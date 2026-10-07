#!/usr/bin/env python3
"""Tell a Sonos speaker to play this bridge's stream — stdlib only.

Talks raw UPnP/SOAP to the speaker (port 1400), the same mechanism the
Sonos app uses for a custom radio stream. No Sonos account needed.

Usage:
    python3 tools/sonos_play.py 192.168.1.50 http://192.168.1.20:8000/stream.mp3
    python3 tools/sonos_play.py 192.168.1.50 http://192.168.1.20:8000/stream.mp3 --stop
"""
from __future__ import annotations

import argparse
import urllib.request
from xml.sax.saxutils import escape

CONTROL_URL = "http://{ip}:1400/MediaRenderer/AVTransport/Control"
SERVICE = "urn:schemas-upnp-org:service:AVTransport:1"


def didl_for(stream_url: str, title: str = "Pi Sonos Bridge") -> str:
    return (
        '<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" '
        'xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/" '
        'xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">'
        '<item id="-1" parentID="-1" restricted="true">'
        f"<dc:title>{escape(title)}</dc:title>"
        "<upnp:class>object.item.audioItem.audioBroadcast</upnp:class>"
        f'<res protocolInfo="http-get:*:audio/mpeg:*">{escape(stream_url)}</res>'
        "</item></DIDL-Lite>"
    )


def soap_body(action: str, args: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
        's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
        f"<s:Body><u:{action} xmlns:u=\"{SERVICE}\">{args}</u:{action}></s:Body>"
        "</s:Envelope>"
    ).encode()


def send(ip: str, action: str, args: str) -> str:
    req = urllib.request.Request(
        CONTROL_URL.format(ip=ip),
        data=soap_body(action, args),
        headers={
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPACTION": f'"{SERVICE}#{action}"',
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode(errors="replace")


def play(ip: str, stream_url: str) -> None:
    # Sonos expects the radio URI wrapped like this for MP3 streams.
    uri = stream_url if stream_url.startswith("x-rincon") else stream_url
    send(
        ip,
        "SetAVTransportURI",
        "<InstanceID>0</InstanceID>"
        f"<CurrentURI>{escape(uri)}</CurrentURI>"
        f"<CurrentURIMetaData>{escape(didl_for(stream_url))}</CurrentURIMetaData>",
    )
    send(ip, "Play", "<InstanceID>0</InstanceID><Speed>1</Speed>")


def stop(ip: str) -> None:
    send(ip, "Stop", "<InstanceID>0</InstanceID>")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("speaker_ip")
    parser.add_argument("stream_url", nargs="?", help="e.g. http://192.168.1.20:8000/stream.mp3")
    parser.add_argument("--stop", action="store_true")
    parsed = parser.parse_args()
    if parsed.stop:
        stop(parsed.speaker_ip)
        print("Stopped.")
    else:
        if not parsed.stream_url:
            parser.error("stream_url is required unless --stop is given")
        play(parsed.speaker_ip, parsed.stream_url)
        print(f"Playing {parsed.stream_url} on {parsed.speaker_ip}")
