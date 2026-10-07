# Troubleshooting

**Sonos says the station can't be played / connection lost**
- Can a laptop on the same network open `http://<pi-ip>:8000/stream.mp3`
  and hear audio (or the test tone)? If not, fix that first — Sonos adds
  nothing magical.
- Guest Wi-Fi / VLANs: speakers and Pi must be on the same subnet, or your
  router must route between them. Client isolation kills this.
- Check Icecast is up: `systemctl status icecast2`, and the mount exists at
  `http://<pi-ip>:8000/status.xsl`.

**Stream is silent**
- `http://<pi-ip>:8080` shows the stream running? Restart it there.
- Line-in: is the right source being looped? `pactl list short sources`
  (find your device), then check `LINEIN_SOURCE_MATCH` in
  `/etc/pi-sonos-bridge.env` and `systemctl --user restart pi-sonos-routing`.
- Check levels with `alsamixer` — USB interfaces often default capture to 0.
- Bluetooth: is the phone actually routing audio to "Pi Sonos Bridge"
  (phones keep media on the phone speaker if a call profile grabbed it —
  disconnect/reconnect Bluetooth).

**Phone can't see / pair with the Pi**
- `bluetoothctl show` (powered on?) and `bluetoothctl discoverable on`.
- `systemctl status pi-sonos-bt-agent` — the Just Works agent must run for
  headless pairing.
- Forget the Pi on the phone and re-pair if a previous pairing went stale.

**Audio stutters**
- Use Ethernet for the Pi, or move it closer to the access point.
- Under-voltage: use the official PSU; `vcgencmd get_throttled` should say `0x0`.
- Drop the bitrate (`AUDIO_BITRATE_KBPS=128` in the env file, restart the
  streamer service) on very weak networks.

**Delay is too long**
- ~2–5 s is normal for this design. Reduce Icecast `burst-size` a little,
  but Sonos needs some buffer; there's no zero-latency mode. For TV, use a
  Sonos product with a hardware line-in/HDMI instead.

**Services don't start at boot**
- `loginctl show-user $USER | grep Linger` must say `Linger=yes`
  (install.sh enables it). Without it, user services wait for a login.
