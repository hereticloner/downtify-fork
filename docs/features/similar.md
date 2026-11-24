---
icon: lucide/sparkles
---

# Similar

**Similar** finds tracks that sound like one you name, from YouTube Music's own radio mix — what YouTube plays after your track. No API key, no setup.

## How it works

`GET /api/similar/tracks?artist=&track=` returns tracks from the radio mix of the seed you name. Either **artist** or **track** alone is enough: a bare artist seeds from its top hit, a bare title from the top hit for it. `limit` is `20` by default and `50` at most.

The rows are ordinary song objects — the same shape `/api/songs/search` returns — plus a `match` score. YouTube ranks "Up next" by relevance but gives no score of its own, so `match` decays with the row's position: the first row counts as a perfect match, the last one as barely related.

Rows carry their video id and link, so they download straight away through `POST /api/download/url`, and they stream through `GET /api/stream/file` without being downloaded. `502` when YouTube Music can't be used (unknown track, network).

## Endless list

The frontend model chains the mix page by page: each request is seeded from the last row, rows already shown are dropped, and a page that adds nothing new ends the list. What has loaded stays playable if a later page fails.

## Downloading the loaded results

**Download new** queues every currently loaded result that is not already in the library. It does not wait for or select future pages, so a long endless list cannot turn one click into an unbounded download. Tracks already downloaded are skipped.

## API

See [`GET /api/similar/tracks`](../api-reference.md#get-apisimilartracks) in the API Reference.
