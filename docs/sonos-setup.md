# Getting the stream playing on Sonos

The bridge publishes one URL: `http://<pi-ip>:8000/stream.mp3`.
Any Sonos speaker that can reach the Pi on your LAN can play it.
Two ways to start it:

## Option A — one command (recommended)

From any computer on the same network:

```bash
python3 tools/sonos_discover.py            # find your speakers' IPs
python3 tools/sonos_play.py 192.168.1.50 http://192.168.1.20:8000/stream.mp3
```

This speaks UPnP/SOAP directly to the speaker — the same thing the Sonos
app does internally. Once playing, the stream also appears in the Sonos
app's recently played, so next time it's one tap there.
Stop with `python3 tools/sonos_play.py 192.168.1.50 --stop` (URL not needed).

To play on a stereo pair / group, target the group coordinator's IP
(the speaker the Sonos app shows as the group's first member).

## Option B — add it as a custom radio station in the Sonos app

1. Open the Sonos app → **Radio** (or Browse → TuneIn on S1).
2. **My Radio Stations** (TuneIn) → **Add New Radio Station**.
3. Paste the streaming URL `http://<pi-ip>:8000/stream.mp3` and name it
   "Pi Bridge".
4. Play it on any room. Favourite it for quick access.

Exact menu labels vary slightly between Sonos app versions; the URL and
the idea (a custom MP3 radio stream) are constant across S1 and S2.

## Notes

- **Delay:** expect roughly 2–5 s between the source and the speakers
  (Bluetooth + MP3 encode + Icecast buffer + Sonos buffer). Fine for
  music and radio; not usable for TV lip-sync.
- **Grouping:** group rooms in the Sonos app as usual — grouped speakers
  stay in sync with each other.
- **Keep the Pi's IP stable** (DHCP reservation in your router), or use
  `raspberrypi.local` if your network resolves mDNS names for Sonos
  (router dependent — a fixed IP is the reliable choice).
- The stream runs even with nothing connected — Sonos will happily play
  silence. Switch inputs at `http://<pi-ip>:8080`.
