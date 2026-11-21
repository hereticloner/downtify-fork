#!/bin/sh

LOG_LEVEL="${DOWNTIFY_LOG_LEVEL:-info}"
APP_UID="${UID:-1000}"
APP_GID="${GID:-1000}"

# Docker creates bind-mounted directories as root, so a fresh install would
# leave the app unable to write. Hand the two volume roots to the app user
# once (the recursive pass only runs while they still belong to someone
# else), then drop privileges: nothing in the app needs root.
if [ "$(id -u)" = "0" ]; then
    for dir in /downloads /data; do
        if [ "$(stat -c %u "$dir" 2>/dev/null)" != "$APP_UID" ]; then
            chown -R "$APP_UID:$APP_GID" "$dir" 2>/dev/null || true
        fi
    done
    exec su-exec "$APP_UID:$APP_GID" python main.py web \
        --host 0.0.0.0 \
        --log-level "${LOG_LEVEL}"
fi

# Already running unprivileged (e.g. `docker run --user`): nothing to drop.
exec python main.py web \
    --host 0.0.0.0 \
    --log-level "${LOG_LEVEL}"
