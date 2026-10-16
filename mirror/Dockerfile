# The Downtify Mirror runs Spotify Soloist: Spotify's own headless Spotify
# Connect client, on the same playback engine as the Spotify desktop and
# mobile apps. Unlike go-librespot (an unofficial engine), a play sent to
# Soloist is recorded by Spotify as real listening - Recently played, top
# tracks, the yearly wrap-up (docs/features/spotify-mirror.md).
#
# ubuntu:24.04, not debian bookworm: the Soloist binary needs glibc 2.38.
# It is glibc/x86-64 only, and a headless container has no sound card, so
# it plays into PulseAudio's null sink instead of a real device.
FROM ubuntu:24.04

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      pulseaudio pulseaudio-utils libatomic1 ca-certificates curl \
 && curl -fsSL -o /tmp/soloist.tar.gz \
      https://soloist-builds.spotifycdn.com/soloist_release_x86_64.tar.gz \
 && tar -xzf /tmp/soloist.tar.gz -C /usr/local/bin/ soloist \
 && rm /tmp/soloist.tar.gz \
 && apt-get purge -y curl \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 755 /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
