---
icon: lucide/radio
---

# Streaming & Similar Tracks

Downtify can hand out a track's **full audio** without downloading it into your library, and it can find **tracks that sound like one you name**. Both are backend endpoints today — the web UI for them is not part of this build yet, so they are aimed at third-party clients and at the web UI that will sit on top of them.

## Streaming a track that isn't downloaded

A song that is in a playlist or a search result but not in your library can still be played in full. The server resolves it to a YouTube video and serves the audio itself.

Two shapes, both taking the song's YouTube `video_id`:

- `GET /api/stream/file` — the audio **downloaded once** into `/data/stream_cache` and served from this server with seeking support. This is the one to use: it keeps working where the client itself can't reach YouTube (or only slowly), because the only YouTube traffic is server-side. The second play of a track never touches YouTube at all.
- `GET /api/stream` — a **fresh direct URL** to YouTube's audio for the same video. Short-lived and bound to the server's network: fetch it on demand, never cache or persist it. Meant for clients that can reach YouTube themselves.

`POST /api/stream/prefetch` starts caching a video's audio in the background (`{"video_id": "..."}`) without waiting for it — so the next track can be warmed up while the current one is still loading.

::: tip Concurrent requests share one download
Two requests for the same video that arrive together are served from **one** download, not two. A request that is cancelled (the client moved on) only stops the download once nobody else is waiting for it.
:::

### The cache

`/data/stream_cache` holds the fetched audio, named `<video_id>.<ext>`. It is pruned least-recently-used past `DOWNTIFY_STREAM_CACHE_MB` (default 1024 MB), with at most `DOWNTIFY_STREAM_CONCURRENCY` downloads running at once (default 2). Both are environment variables — see [Environment Variables](../getting-started/environment-variables.md).

A streamed track never lands in your library: no file in `/downloads`, no tags, no playlist, nothing in the activity log. It is audio served on the side.

### What is refused

- **Tracks over 10 minutes** are refused with `400`, before any download when the caller states the length, and from the probed length of the served file otherwise. A long upload never accumulates in the cache.
- **Age-gated tracks** need usable YouTube cookies, or the request fails with `503`. Upload a `cookies.txt` in **Settings → YouTube cookies** — see [YouTube Cookies](youtube-cookies.md).
- A malformed `video_id` is a `400`; YouTube being unreachable or refusing is a `503`.

## Finding similar tracks

`GET /api/similar/tracks?artist=&track=` returns tracks that sound like one you name, taken from YouTube Music's own radio mix for the seed — what YouTube plays after it. No API key, no setup.

Either `artist` or `track` alone is enough as a seed: a bare artist seeds from its top hit, a bare title from the top hit for it.

The rows are ordinary song objects — the same shape `/api/songs/search` returns — plus a `match` score. YouTube ranks "Up next" by relevance but gives no score of its own, so `match` decays with the row's position: the first row counts as a perfect match, the last one as barely related. They download straight away through `POST /api/download/url`, and they stream through `GET /api/stream/file` without being downloaded.

`502` when YouTube Music can't be reached, or when the seed matches nothing.

## API

See [`GET /api/stream/file`](../api-reference.md#get-apistreamfile), [`GET /api/stream`](../api-reference.md#get-apistream), [`POST /api/stream/prefetch`](../api-reference.md#post-apistreamprefetch) and [`GET /api/similar/tracks`](../api-reference.md#get-apisimilartracks) in the API Reference.
