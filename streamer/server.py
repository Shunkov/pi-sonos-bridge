"""Control server: tiny JSON API + one-page web UI. Stdlib only.

Endpoints:
  GET  /                  web UI
  GET  /healthz           liveness probe
  GET  /api/status        stream + input status (incl. paired BT devices)
  POST /api/source        {"source": "mix" | "linein" | "bluetooth" | "mute"}
  POST /api/stream/start
  POST /api/stream/stop
  POST /api/stream/restart
"""
from __future__ import annotations

import json
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import Config
from .manager import StreamManager, VALID_SOURCES

UI_HTML = """<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pi Sonos Bridge</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:640px;margin:2rem auto;padding:0 1rem;background:#111;color:#eee}
 button{padding:.6rem 1rem;margin:.25rem;border:0;border-radius:.5rem;background:#2b6cb0;color:#fff;cursor:pointer}
 button.off{background:#444} code{background:#222;padding:.2rem .4rem;border-radius:.3rem}
 .card{background:#1a1a1a;border-radius:.75rem;padding:1rem;margin:1rem 0}
</style>
<h1>🎵 Pi Sonos Bridge</h1>
<div class="card">
  <p>Stream status: <b id="status">…</b></p>
  <p>Play this URL on Sonos: <code id="url">…</code></p>
  <p>
    <button data-source="mix">Mix both</button>
    <button data-source="linein">Line-in only</button>
    <button data-source="bluetooth">Bluetooth only</button>
    <button data-source="mute" class="off">Mute</button>
  </p>
  <p>
    <button id="restart">Restart stream</button>
    <button id="stop" class="off">Stop stream</button>
  </p>
  <p id="bt"></p>
</div>
<script>
async function refresh(){
  const s = await (await fetch('/api/status')).json();
  document.getElementById('status').textContent =
    (s.stream.running ? '▶ streaming' : '⏸ stopped') + ' · source: ' + s.stream.source +
    ' · mode: ' + s.stream.audio_mode + ' · ' + s.stream.bitrate_kbps + ' kbps';
  document.getElementById('url').textContent = s.stream.stream_url;
  const bt = s.bluetooth;
  document.getElementById('bt').textContent = bt.available
    ? 'Bluetooth: ' + (bt.devices.length ? bt.devices.map(d=>d.name||d.mac).join(', ') : 'no devices paired yet — pair from your phone, the Pi is discoverable')
    : 'Bluetooth status unavailable on this machine';
}
document.querySelectorAll('[data-source]').forEach(b=>b.onclick=async()=>{
  await fetch('/api/source',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({source:b.dataset.source})}); refresh();});
document.getElementById('restart').onclick=async()=>{await fetch('/api/stream/restart',{method:'POST'});refresh();};
document.getElementById('stop').onclick=async()=>{await fetch('/api/stream/stop',{method:'POST'});refresh();};
refresh(); setInterval(refresh, 5000);
</script>
"""


def bluetooth_status() -> dict:
    """Paired devices via bluetoothctl; unavailable off-Pi, which is fine."""
    try:
        out = subprocess.run(
            ["bluetoothctl", "devices", "Paired"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode != 0:
            return {"available": False, "devices": []}
        devices = []
        for line in out.stdout.splitlines():
            parts = line.split(None, 2)  # Device <MAC> <name>
            if len(parts) >= 2 and parts[0] == "Device":
                devices.append({"mac": parts[1], "name": parts[2] if len(parts) > 2 else ""})
        return {"available": True, "devices": devices}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {"available": False, "devices": []}


def make_handler(cfg: Config, manager: StreamManager):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep journald clean
            pass

        def _json(self, code: int, payload: dict) -> None:
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/healthz":
                self._json(200, {"ok": True})
            elif self.path == "/api/status":
                self._json(200, {"stream": manager.status(), "bluetooth": bluetooth_status()})
            elif self.path == "/":
                body = UI_HTML.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                return self._json(400, {"error": "invalid JSON"})

            if self.path == "/api/source":
                source = str(payload.get("source", "")).lower()
                if source not in VALID_SOURCES:
                    return self._json(400, {"error": f"source must be one of {VALID_SOURCES}"})
                return self._json(200, manager.set_source(source))
            if self.path == "/api/stream/start":
                manager.start()
                return self._json(200, manager.status())
            if self.path == "/api/stream/stop":
                manager.stop()
                return self._json(200, manager.status())
            if self.path == "/api/stream/restart":
                manager.restart()
                return self._json(200, manager.status())
            return self._json(404, {"error": "not found"})

    return Handler


def serve(cfg: Config, manager: StreamManager) -> None:
    server = ThreadingHTTPServer((cfg.control_host, cfg.control_port), make_handler(cfg, manager))
    print(f"Control UI on http://{cfg.control_host}:{cfg.control_port} — Sonos URL: {cfg.stream_url_hint}")
    server.serve_forever()
