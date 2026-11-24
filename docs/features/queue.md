---
icon: lucide/list-checks
---

# Queue

The **Queue** page (`/queue`) shows every download Downtify is working on or has finished, split across tabs — **In progress**, **Waiting**, **Done**, **Failed** and **All** — with retry, remove and clear actions and, on the side, the playlist batches currently downloading and a CSV import box. Admins also get waiting-row selection, Normal/High priority and per-selection pause/resume/remove actions.

## Unfinished playlists

When a tracked Spotify playlist is still missing tracks — some failed, or were added to the playlist later — an **Unfinished playlists** panel shows it in the side column, with how many are missing and a **Download missing** button that queues exactly those. The playlist name links to its page for the full breakdown.

## Pausing, priority and quiet hours

The page header holds the global **Pause downloads** switch. Running downloads finish, waiting jobs keep their place, and the switch survives restarts. Playlist Monitor and Replace Audio jobs wait at the same gate.

Admins can select waiting rows to pause, resume or remove only those jobs, and set each waiting row to **Normal** or **High** priority. Quiet hours in **Settings → Server → Queue control** apply the same gate automatically during a local-time window without cancelling running work.

See [Download Queue](download-queue.md) for the full behavior, restart guarantees and quiet-hour rules.

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/queue/state` | Global pause state |
| `POST /api/queue/pause` | Pause new downloads; running ones finish |
| `POST /api/queue/resume` | Resume the global queue |
| `POST /api/queue/priority` | Set Normal/High priority on waiting jobs |
| `POST /api/queue/bulk` | Remove, pause or resume selected waiting jobs |

See the [Queue API reference](../api-reference.md#queue).