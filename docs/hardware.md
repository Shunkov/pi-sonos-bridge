# Hardware

## You need

| Part | Notes |
|---|---|
| Raspberry Pi 4 or 5 (3B+ works too) | 2 GB RAM is plenty. Pi OS Bookworm 64-bit. |
| Power supply + microSD (16 GB+) | The official 27 W USB-C supply on a Pi 5 avoids under-voltage audio glitches. |
| **A line-in interface** | ⚠️ **No Raspberry Pi has a line-in jack.** The 3.5 mm jack is output-only (or absent on Pi 5). Pick one option below. |
| Ethernet (recommended) or good Wi-Fi | Streaming to Sonos is far more reliable wired. |

## Line-in options

1. **USB audio interface** (easiest, recommended) — any class-compliant USB
   device with a stereo input, e.g. a Behringer UCA222/UCA202 (~£25), or any
   USB "capture" dongle that exposes a real stereo line-in (check it is not
   mic-mono only). Shows up as an `alsa_input.usb-...` source.
2. **HiFiBerry DAC+ ADC / DAC2 Pro + ADC**, or **IQaudio Codec Zero** HATs —
   sit on the GPIO header, proper RCA line-in, best audio quality.
3. A USB turntable with its own ADC also works — it *is* a USB audio source.

Set `LINEIN_SOURCE_MATCH` in `/etc/pi-sonos-bridge.env` if your device does
not match the default `alsa_input.usb` pattern. Run
`pactl list short sources` with the device plugged in to see its name.

## Bluetooth

The Pi's built-in Bluetooth (4/5) works as an A2DP receiver via PipeWire +
BlueZ, SBC and AAC codecs. Range is the usual ~10 m; a USB Bluetooth dongle
with an external antenna helps in bigger rooms. No extra hardware needed
for the common case.

## Levels

Line-in should be a true line-level signal (~1–2 Vrms). A turntable needs a
phono preamp (or a deck with line output) — plugging a phono-level signal
straight in will sound very quiet and thin.
