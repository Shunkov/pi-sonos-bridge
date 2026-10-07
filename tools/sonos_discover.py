#!/usr/bin/env python3
"""Find Sonos speakers on the LAN via SSDP — stdlib only.

Usage: python3 tools/sonos_discover.py
Prints speaker IPs you can pass to tools/sonos_play.py.
"""
from __future__ import annotations

import socket

SSDP_ADDR = ("239.255.255.250", 1900)
REQUEST = (
    "M-SEARCH * HTTP/1.1\r\n"
    "HOST: 239.255.255.250:1900\r\n"
    'MAN: "ssdp:discover"\r\n'
    "MX: 2\r\n"
    "ST: urn:schemas-upnp-org:device:ZonePlayer:1\r\n\r\n"
).encode()


def discover(timeout: float = 5.0) -> list[str]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(timeout)
    sock.sendto(REQUEST, SSDP_ADDR)
    ips: list[str] = []
    try:
        while True:
            _, addr = sock.recvfrom(4096)
            if addr[0] not in ips:
                ips.append(addr[0])
    except socket.timeout:
        pass
    finally:
        sock.close()
    return ips


if __name__ == "__main__":
    found = discover()
    if not found:
        print("No Sonos speakers answered. Check the Pi and speakers share a network/VLAN.")
    for ip in found:
        print(ip)
