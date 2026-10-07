---
icon: lucide/list-checks
---

# Queue

The **Queue** page (`/queue`) shows every download Downtify is working on or has finished, split across tabs — **In progress**, **Waiting**, **Done**, **Failed** and **All** — with retry, remove and clear actions and, on the side, the playlist batches currently downloading and a CSV import box. This page also holds the global **pause**.

## Pausing and resuming the queue

While anything is waiting, a **Pause all** button sits in the page header (on a phone it collapses to just its icon). Click it to pause, and it becomes **Resume all**:

- **Pausing stops new downloads from starting.** Rows that are already downloading keep going and finish normally; rows still waiting stay put and start again only once you resume.
- **Resume unblocks the queue.** Waiting rows go back to starting as concurrency slots free up. It does not re-queue anything that already finished or failed.
- The pause is **global**, not per batch or per tab: every download that goes through the download queue — a single track, a playlist/album batch, a CSV import — waits while it is on. Playlist Monitor sweeps download directly (not through the queue) and are not paused by it.
- It is **in-memory**: the state lives in the running server, not on disk, so restarting the container clears it and downloads resume. The button only appears when something is queued, and the page reads the current state when it loads.

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/queue/status` | `{ "paused": false }` — current pause state |
| `POST /api/queue/pause` | Pause; in-flight downloads finish, queued ones wait |
| `POST /api/queue/resume` | Resume the queue |

See the [Queue API reference](../api-reference.md#queue).