"""Owns the ffmpeg encoder process: start / stop / restart / health.

If ffmpeg exits unexpectedly it is restarted with exponential backoff
(1s, 2s, 4s ... capped at 30s). A deliberate stop never triggers a restart.
"""
from __future__ import annotations

import subprocess
import threading
import time

from .config import Config
from .ffmpeg_cmd import build_ffmpeg_command

# Input selection is done in PipeWire (muting/unmuting loopback modules),
# not by restarting ffmpeg — so switching source never drops the Sonos stream.
VALID_SOURCES = ("mix", "linein", "bluetooth", "mute")


class StreamManager:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._stop_requested = False
        self._started_at: float | None = None
        self._restarts = 0
        self._last_error: str | None = None
        self.source = "mix"

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                return
            self._stop_requested = False
            self._spawn_locked()
            threading.Thread(target=self._watchdog, daemon=True).start()

    def _spawn_locked(self) -> None:
        cmd = build_ffmpeg_command(self.cfg)
        try:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
            )
            self._started_at = time.time()
            self._last_error = None
        except FileNotFoundError:
            self._proc = None
            self._last_error = "ffmpeg not found — install it (see scripts/install.sh)"
            raise

    def stop(self) -> None:
        with self._lock:
            self._stop_requested = True
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
            self._proc = None
            self._started_at = None

    def restart(self) -> None:
        self.stop()
        self.start()

    def _watchdog(self) -> None:
        backoff = 1.0
        while True:
            time.sleep(1)
            with self._lock:
                if self._stop_requested or self._proc is None:
                    return
                if self._proc.poll() is None:
                    backoff = 1.0
                    continue
                # ffmpeg died on its own — capture why, then restart.
                stderr = ""
                try:
                    stderr = (self._proc.stderr.read() or "")[-500:] if self._proc.stderr else ""
                except Exception:
                    pass
                self._last_error = stderr.strip() or f"ffmpeg exited rc={self._proc.returncode}"
                self._restarts += 1
            time.sleep(backoff)
            backoff = min(backoff * 2, 30.0)
            with self._lock:
                if self._stop_requested:
                    return
                try:
                    self._spawn_locked()
                except FileNotFoundError:
                    return

    # -- input selection ---------------------------------------------------
    def set_source(self, source: str) -> dict:
        """Mute/unmute PipeWire loopbacks so only the chosen input is heard.

        Best-effort: on a machine without pactl (dev laptop) the selection
        is recorded and reported, but no audio routing exists to change.
        """
        if source not in VALID_SOURCES:
            raise ValueError(f"Unknown source {source!r}; expected one of {VALID_SOURCES}")
        self.source = source
        routing_applied = _apply_routing(source)
        return {"source": source, "routing_applied": routing_applied}

    # -- status ------------------------------------------------------------
    def status(self) -> dict:
        running = bool(self._proc and self._proc.poll() is None)
        return {
            "running": running,
            "audio_mode": self.cfg.audio_mode,
            "source": self.source,
            "uptime_seconds": int(time.time() - self._started_at) if running and self._started_at else 0,
            "restarts": self._restarts,
            "last_error": self._last_error,
            "stream_url": self.cfg.stream_url_hint,
            "bitrate_kbps": self.cfg.bitrate_kbps,
        }


def _apply_routing(source: str) -> bool:
    """Use pactl to mute the loopback streams that should not be heard.

    Loopback modules created by our scripts carry the media.name markers
    'pi-sonos-linein' / 'pi-sonos-bluetooth', which is how we find them.
    Returns True if at least one pactl call succeeded.
    """
    try:
        out = subprocess.run(
            ["pactl", "list", "short", "sink-inputs"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode != 0:
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

    # pactl's short listing has no names, so inspect the verbose list and
    # pair each sink-input id with its media.name.
    try:
        verbose = subprocess.run(
            ["pactl", "list", "sink-inputs"],
            capture_output=True, text=True, timeout=5,
        ).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

    applied = False
    current_id: str | None = None
    for line in verbose.splitlines():
        line = line.strip()
        if line.startswith("Sink Input #"):
            current_id = line.split("#", 1)[1].strip()
        elif "media.name" in line and current_id:
            name = line.split("=", 1)[1].strip().strip('"') if "=" in line else ""
            kind = None
            if "pi-sonos-linein" in name:
                kind = "linein"
            elif "pi-sonos-bluetooth" in name:
                kind = "bluetooth"
            if kind is None:
                continue
            mute = source == "mute" or (source != "mix" and source != kind)
            res = subprocess.run(
                ["pactl", "set-sink-input-mute", current_id, "1" if mute else "0"],
                capture_output=True, timeout=5,
            )
            applied = applied or res.returncode == 0
    return applied
