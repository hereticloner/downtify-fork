# The Downtify Mirror: a silent, always-online Spotify Connect device.
#
# spotifyd runs on the server with no sound hardware: volume starts at
# 0, and ALSA's built-in `null` device swallows the stream. Plays sent
# to this device exist to be counted by Spotify (see
# docs/features/spotify-mirror.md), not to be heard.

FROM debian:bookworm-slim

ARG SPOTIFYD_VERSION=v0.4.2

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl libasound2 libdbus-1-3 \
    && rm -rf /var/lib/apt/lists/*

# A pinned official release binary: full build (alsa backend included),
# matching the container's architecture.
RUN set -e; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
        amd64) target=x86_64 ;; \
        arm64) target=aarch64 ;; \
        *) echo "unsupported architecture: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL \
        "https://github.com/Spotifyd/spotifyd/releases/download/${SPOTIFYD_VERSION}/spotifyd-linux-${target}-full.tar.gz" \
        -o /tmp/spotifyd.tar.gz; \
    tar -xzf /tmp/spotifyd.tar.gz -C /usr/local/bin spotifyd; \
    chmod 0755 /usr/local/bin/spotifyd; \
    rm /tmp/spotifyd.tar.gz

# /etc/spotifyd.conf is one of spotifyd's default locations - mount the
# real one there. It holds the Spotify credentials: keep it on the
# server, out of git (see spotifyd.conf.example).
VOLUME ["/cache"]

CMD ["spotifyd", "--no-daemon"]