# Architecture

```
 phone / laptop ──Bluetooth A2DP──► BlueZ ──► PipeWire source (bluez_source.*)
                                                        │ loopback (watcher)
                                                        ▼
 turntable / CD / TV ──line──► USB/HAT ADC ──► PipeWire source (alsa_input.*)
                                                        │ loopback (routing)
                                                        ▼
                                              ┌───────────────────┐
                                              │ sonos_stream sink │  (PipeWire null sink)
                                              └─────────┬─────────┘
                                                        │ .monitor
                                                        ▼
                                              ffmpeg ──MP3 192k──► Icecast2 :8000/stream.mp3
                                                        │
                                                        ▼
                                              Sonos speaker(s)  (custom radio stream)
```

## Why this shape

- **One always-on stream.** ffmpeg captures the *monitor of a virtual sink*,
  never a physical device. Input switching = mute/unmute loopbacks in
  PipeWire, so the Icecast mount (and Sonos's connection to it) never drops
  when you switch from Bluetooth to line-in.
- **Bluetooth sources are dynamic.** A phone's A2DP source only exists while
  it's connected, so a small watcher loop adds its loopback on connect;
  PipeWire removes it on disconnect.
- **MP3/Icecast to Sonos.** It's the one format/transport every Sonos
  generation plays natively as a custom radio station — no cloud, no Sonos
  account features, no reverse-engineered APIs in the playback path.
  `tools/sonos_play.py` is plain UPnP/SOAP to the speaker's local API.
- **Zero Python dependencies.** The streamer is stdlib-only
  (`http.server`, `subprocess`), so it runs on a stock Pi OS install and
  survives OS upgrades that would break a venv.

## Components

| Piece | What it does |
|---|---|
| `streamer/` | Control API/UI (:8080) and ffmpeg process manager with auto-restart/backoff |
| `config/icecast.xml` | Icecast config; install script injects a generated source password |
| `scripts/audio-routing.sh` | Creates `sonos_stream` sink + line-in loopback (idempotent, boot-safe) |
| `scripts/bt-loopback-watcher.sh` | Loops newly connected Bluetooth sources into the sink |
| `scripts/install.sh` | Full Pi setup: packages, Bluetooth A2DP receiver config, systemd units |
| `systemd/` | User units for streamer/routing/watcher (linger enabled for headless boot) |
| `tools/sonos_play.py` | Start/stop the stream on a speaker via UPnP/SOAP |
| `tools/sonos_discover.py` | SSDP discovery of speaker IPs |

## Known limits

- End-to-end latency ~2–5 s (inherent to MP3 + Icecast + Sonos buffering).
- One mixed stream — line-in and Bluetooth mix together if both play;
  pick a single source in the web UI if that isn't what you want.
- Bluetooth codec is whatever phone + PipeWire negotiate (SBC/AAC);
  aptX/LDAC receive is not supported by BlueZ/PipeWire on Pi OS.
