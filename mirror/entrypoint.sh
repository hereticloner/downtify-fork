#!/bin/sh
# The Downtify Mirror is a silent Spotify Connect device. It runs Spotify
# Soloist, Spotify's own headless client, so plays sent to it go through the
# same playback engine as the Spotify apps and count as real listening.
# Spotify Soloist builds expire after 90 days; rebuild the image before then.
set -e

# A headless container has no sound card. PulseAudio as root only runs in
# system mode; either way Soloist plays into a null sink.
pulseaudio --start --exit-idle-time=-1 2>/dev/null \
  || pulseaudio --system --daemonize=yes --disallow-exit \
       --disallow-module-loading=false 2>/dev/null \
  || true
pactl load-module module-null-sink sink_name=mirror 2>/dev/null || true

DATA_DIR="${SOLOIST_DATA_DIR:-/data}"
NAME="${SOLOIST_DEVICE_NAME:-Downtify Mirror}"

# One-time pairing, from a Spotify app on the same network as the server:
#   docker compose run --rm mirror pair
if [ "${1:-}" = 'pair' ]; then
  exec soloist --pair --device-name "$NAME" --api-key "$SOLOIST_API_KEY" \
    --data-dir "$DATA_DIR"
fi

exec soloist --device-name "$NAME" --api-key "$SOLOIST_API_KEY" \
  --data-dir "$DATA_DIR" --initial-volume 0
