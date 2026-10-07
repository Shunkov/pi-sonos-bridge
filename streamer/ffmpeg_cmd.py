"""Builds the ffmpeg command that encodes captured audio to Icecast as MP3.

MP3 over Icecast is used because every Sonos speaker (S1 and S2) can play
an MP3 HTTP stream as a custom radio station, with no Sonos account
features, cloud service or deprecated APIs involved.
"""
from __future__ import annotations

from .config import Config

VALID_MODES = ("pipewire", "direct", "test_tone")


def build_ffmpeg_command(cfg: Config) -> list[str]:
    if cfg.audio_mode not in VALID_MODES:
        raise ValueError(
            f"Unknown AUDIO_MODE {cfg.audio_mode!r}; expected one of {VALID_MODES}"
        )

    cmd: list[str] = ["ffmpeg", "-hide_banner", "-loglevel", "warning", "-nostdin"]

    if cfg.audio_mode == "pipewire":
        cmd += ["-f", "pulse", "-i", cfg.pulse_source]
    elif cfg.audio_mode == "direct":
        cmd += ["-f", "alsa", "-i", cfg.alsa_device]
    else:  # test_tone
        # lavfi is not paced by hardware like ALSA/Pulse capture, so -re is
        # required or ffmpeg encodes as fast as the CPU allows and floods
        # Icecast with hours of tone in seconds.
        cmd += [
            "-re",
            "-f", "lavfi",
            "-i", f"sine=frequency=440:sample_rate={cfg.sample_rate}",
        ]

    cmd += [
        "-ac", str(cfg.channels),
        "-ar", str(cfg.sample_rate),
        "-codec:a", "libmp3lame",
        "-b:a", f"{cfg.bitrate_kbps}k",
        "-content_type", "audio/mpeg",
        "-ice_name", "Pi Sonos Bridge",
        "-ice_description", "Line-in and Bluetooth from Raspberry Pi",
        "-f", "mp3",
        cfg.icecast_source_url,
    ]
    return cmd
