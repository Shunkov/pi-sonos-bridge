#!/usr/bin/env bash
# Bluetooth A2DP sources appear/disappear as phones connect/disconnect.
# This watcher loops every connected Bluetooth source into the sonos_stream
# sink. Polling every 3s is plenty: Sonos playback is buffered anyway.
set -uo pipefail

SINK_NAME="${SINK_NAME:-sonos_stream}"
STATE_DIR="${XDG_RUNTIME_DIR:-/tmp}/pi-sonos-bridge"
mkdir -p "$STATE_DIR"

while true; do
  # Current Bluetooth sources look like: bluez_source.AA_BB_CC_DD_EE_FF.a2dp_source
  CURRENT="$(pactl list short sources 2>/dev/null | awk '{print $2}' | grep -E '^bluez_source\.' | grep -v monitor || true)"
  for src in $CURRENT; do
    marker="$STATE_DIR/bt-$(echo "$src" | tr '.:/' '___')"
    if [ ! -f "$marker" ]; then
      if pactl load-module module-loopback \
          source="$src" sink="$SINK_NAME" latency_msec=100 \
          source_output_properties=media.name="pi-sonos-bluetooth" >/dev/null 2>&1; then
        touch "$marker"
        echo "bluetooth $src -> $SINK_NAME"
      fi
    fi
  done
  # Clean markers for devices that have gone away (their loopback module
  # unloads itself when the source disappears).
  for marker in "$STATE_DIR"/bt-*; do
    [ -e "$marker" ] || continue
    src_name="$(basename "$marker" | sed 's/^bt-//' | tr '_' '.')"
    echo "$CURRENT" | grep -q "$(basename "$marker" | sed 's/^bt-//;s/_/./g')" || rm -f "$marker"
  done
  sleep 3
done
