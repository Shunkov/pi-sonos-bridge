"""Configuration for pi-sonos-bridge. Stdlib only.

Values come from environment variables (set by systemd / .env / Docker),
with sensible defaults for a Raspberry Pi running PipeWire.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


@dataclass(frozen=True)
class Config:
    # Icecast (the server Sonos actually connects to)
    icecast_host: str = "127.0.0.1"
    icecast_port: int = 8000
    icecast_mount: str = "/stream.mp3"
    icecast_source_password: str = "changeme"
    icecast_public_host: str = ""  # e.g. raspberrypi.local — used in UI hints

    # Audio encoding
    bitrate_kbps: int = 192
    sample_rate: int = 44100
    channels: int = 2

    # Audio capture
    #   pipewire  -> capture the monitor of the virtual "sonos_stream" sink
    #                (line-in and Bluetooth are both looped into that sink by
    #                scripts/audio-routing.sh + scripts/bt-loopback-watcher.sh)
    #   direct    -> capture a single ALSA device (line-in only, simplest setup)
    #   test_tone -> no hardware: stream a 440 Hz tone so the Sonos side can
    #                be verified end-to-end before any audio hardware exists
    audio_mode: str = "pipewire"
    pulse_source: str = "sonos_stream.monitor"
    alsa_device: str = "hw:2,0"

    # Control server
    control_host: str = "0.0.0.0"
    control_port: int = 8080

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            icecast_host=_env("ICECAST_HOST", "127.0.0.1"),
            icecast_port=int(_env("ICECAST_PORT", "8000")),
            icecast_mount="/" + _env("ICECAST_MOUNT", "stream.mp3").lstrip("/"),
            icecast_source_password=_env("ICECAST_SOURCE_PASSWORD", "changeme"),
            icecast_public_host=_env("ICECAST_PUBLIC_HOST", ""),
            bitrate_kbps=int(_env("AUDIO_BITRATE_KBPS", "192")),
            sample_rate=int(_env("AUDIO_SAMPLE_RATE", "44100")),
            channels=int(_env("AUDIO_CHANNELS", "2")),
            audio_mode=_env("AUDIO_MODE", "pipewire").strip().lower(),
            pulse_source=_env("PULSE_SOURCE", "sonos_stream.monitor"),
            alsa_device=_env("ALSA_DEVICE", "hw:2,0"),
            control_host=_env("CONTROL_HOST", "0.0.0.0"),
            control_port=int(_env("CONTROL_PORT", "8080")),
        )

    @property
    def icecast_source_url(self) -> str:
        return (
            f"icecast://source:{self.icecast_source_password}"
            f"@{self.icecast_host}:{self.icecast_port}{self.icecast_mount}"
        )

    @property
    def stream_url_hint(self) -> str:
        host = self.icecast_public_host or "<raspberry-pi-ip>"
        return f"http://{host}:{self.icecast_port}{self.icecast_mount}"
