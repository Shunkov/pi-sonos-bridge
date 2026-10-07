#!/usr/bin/env bash
# Installs pi-sonos-bridge on Raspberry Pi OS (Bookworm, 64-bit recommended).
# Run as a normal user with sudo:  ./scripts/install.sh
# Idempotent — re-running updates the code and restarts the services.
set -euo pipefail

APP_DIR="/opt/pi-sonos-bridge"
ENV_FILE="/etc/pi-sonos-bridge.env"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="${SUDO_USER:-$USER}"

echo "==> Installing packages (Icecast, ffmpeg, PipeWire audio, BlueZ)"
sudo apt-get update
sudo apt-get install -y \
  icecast2 ffmpeg python3 \
  pipewire pipewire-audio pipewire-pulse wireplumber libspa-0.2-bluetooth \
  bluez bluez-tools alsa-utils

echo "==> Configuring Icecast"
if [ ! -f /etc/icecast2/icecast-passwords.txt ]; then
  SOURCE_PW="$(head -c 18 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 24)"
  ADMIN_PW="$(head -c 18 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 24)"
  echo "$SOURCE_PW" | sudo tee /etc/icecast2/icecast-passwords.txt >/dev/null
  echo "$ADMIN_PW" | sudo tee -a /etc/icecast2/icecast-passwords.txt >/dev/null
else
  SOURCE_PW="$(sudo sed -n 1p /etc/icecast2/icecast-passwords.txt)"
fi
sudo install -m 644 "$SRC_DIR/config/icecast.xml" /etc/icecast2/icecast.xml
sudo sed -i "s/__SOURCE_PASSWORD__/$SOURCE_PW/g" /etc/icecast2/icecast.xml
sudo sed -i 's/^ENABLE=false/ENABLE=true/' /etc/default/icecast2 2>/dev/null || true

echo "==> Writing environment file $ENV_FILE"
PI_IP="$(hostname -I | awk '{print $1}')"
sudo tee "$ENV_FILE" >/dev/null <<EOF
ICECAST_SOURCE_PASSWORD=$SOURCE_PW
ICECAST_PUBLIC_HOST=$(hostname).local
AUDIO_MODE=pipewire
PULSE_SOURCE=sonos_stream.monitor
# Uncomment and adjust if your line-in source isn't a USB interface:
# LINEIN_SOURCE_MATCH=alsa_input.platform
EOF
sudo chmod 600 "$ENV_FILE"

echo "==> Configuring Bluetooth as an A2DP audio receiver"
sudo tee /etc/bluetooth/main.conf >/dev/null <<'EOF'
[General]
Name = Pi Sonos Bridge
Class = 0x200414
DiscoverableTimeout = 0
AlwaysPairable = true
[Policy]
AutoEnable = true
EOF
# 'Just works' pairing agent (no PIN, no display on a headless Pi).
sudo tee /etc/systemd/system/pi-sonos-bt-agent.service >/dev/null <<EOF
[Unit]
Description=Bluetooth pairing agent (Just Works)
After=bluetooth.service
Requires=bluetooth.service
[Service]
ExecStart=/usr/bin/bt-agent -c NoInputNoOutput
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF

echo "==> Installing application to $APP_DIR"
sudo mkdir -p "$APP_DIR"
sudo cp -r "$SRC_DIR/streamer" "$SRC_DIR/scripts" "$SRC_DIR/tools" "$APP_DIR/"
sudo chmod +x "$APP_DIR"/scripts/*.sh

echo "==> Installing user services (audio routing + streamer + BT watcher)"
mkdir -p ~/.config/systemd/user
for unit in pi-sonos-routing pi-sonos-streamer pi-sonos-bt-loopback; do
  install -m 644 "$SRC_DIR/systemd/$unit.service" ~/.config/systemd/user/
done
# User services need the session to survive logout on a headless Pi.
sudo loginctl enable-linger "$RUN_USER" || true

systemctl --user daemon-reload
sudo systemctl daemon-reload
sudo systemctl enable --now icecast2 bluetooth pi-sonos-bt-agent
systemctl --user enable --now pi-sonos-routing pi-sonos-streamer pi-sonos-bt-loopback

cat <<EOF

✅ Done.

  1. Pair your phone: Bluetooth settings → "Pi Sonos Bridge" (discoverable now;
     if not, run: bluetoothctl discoverable on)
  2. Plug your turntable / CD player / TV into the USB or HAT line-in.
  3. On Sonos, add this custom stream (see docs/sonos-setup.md):
        http://$PI_IP:8000/stream.mp3
     …or from any computer on your network:
        python3 $APP_DIR/tools/sonos_discover.py
        python3 $APP_DIR/tools/sonos_play.py <speaker-ip> http://$PI_IP:8000/stream.mp3
  4. Control inputs in your browser:  http://$PI_IP:8080

  Expect ~2–5 seconds of delay — that's Icecast/MP3/Sonos buffering, and it's
  why this suits music, not TV lip-sync.
EOF
