#!/usr/bin/env bash
# Creates the virtual sink both inputs feed, and loops line-in into it.
#
#   line-in source ──loopback──┐
#                              ├─► sonos_stream (null sink) ─► .monitor ─► ffmpeg
#   Bluetooth A2DP source ─────┘        (BT loopbacks are added dynamically
#                                        by bt-loopback-watcher.sh)
#
# Idempotent: safe to run on every boot. Needs PipeWire/Pulse (pactl).
set -euo pipefail

SINK_NAME="${SINK_NAME:-sonos_stream}"
# Substring/regex identifying the line-in source among `pactl list short sources`.
# USB audio interfaces usually appear as alsa_input.usb-... ; override in env.
LINEIN_SOURCE_MATCH="${LINEIN_SOURCE_MATCH:-alsa_input.usb}"
LINEIN_LATENCY_MS="${LINEIN_LATENCY_MS:-50}"

# Wait for the audio server socket (user session may still be starting).
for _ in $(seq 1 30); do
  pactl info >/dev/null 2>&1 && break
  sleep 1
done
pactl info >/dev/null

# 1. Virtual sink
if ! pactl list short sinks | grep -qw "$SINK_NAME"; then
  pactl load-module module-null-sink \
    sink_name="$SINK_NAME" \
    sink_properties=device.description="SonosStream" >/dev/null
  echo "created sink $SINK_NAME"
fi
# A null sink has no hardware output — set its volume sane for the monitor tap.
pactl set-sink-volume "$SINK_NAME" 100% || true
pactl set-sink-mute "$SINK_NAME" 0 || true

# 2. Line-in loopback (marker name lets the control API mute it by source)
if pactl list short modules | grep -q "pi-sonos-linein"; then
  echo "line-in loopback already present"
  exit 0
fi

LINEIN_SOURCE="$(pactl list short sources | grep -E "$LINEIN_SOURCE_MATCH" | grep -v monitor | awk '{print $2}' | head -n1 || true)"
if [ -z "${LINEIN_SOURCE:-}" ]; then
  echo "WARNING: no line-in source matching '$LINEIN_SOURCE_MATCH' found." >&2
  echo "Available sources:" >&2
  pactl list short sources >&2 || true
  echo "Set LINEIN_SOURCE_MATCH to match your USB/HAT interface and re-run." >&2
  exit 0  # Bluetooth can still work without line-in hardware attached
fi

pactl load-module module-loopback \
  source="$LINEIN_SOURCE" \
  sink="$SINK_NAME" \
  latency_msec="$LINEIN_LATENCY_MS" \
  source_output_properties=media.name="pi-sonos-linein" >/dev/null
echo "line-in $LINEIN_SOURCE -> $SINK_NAME"
