---
icon: lucide/hard-drive
---

# Server Settings

**Settings → Server** holds how the server itself runs. Only admins see it (see [Users & Sign-in](users.md#admins-and-users)).

## The Downtify Mirror device

For [Spotify Mirror](spotify-mirror.md) the server can ship its own silent Spotify Connect client: a `spotifyd` container named **Downtify Mirror**, always online, playing at volume 0 — plays sent to it are only there to be counted by Spotify.

Setting it up on a compose server:

1. Add the `spotifyd` service to `docker-compose.yml` (the image ships the client binary; its config lives in `/data/spotifyd.conf`).
2. In `spotifyd.conf` name the device `Downtify Mirror`, set a silent output (`initial_volume = '0'`) and the Spotify credentials the mirror should run under (the same account the mirror is connected with).
3. `docker compose up -d spotifyd`.

The device shows up in **Settings → Spotify Mirror → Load devices**; every play you start in Downtify then begins there — silently — and lands in your Spotify history.

## Changing the port

Downtify listens on port **8000**. An admin can choose another one in **Settings → Server → Port** (1024–65535):

- **Save** keeps it for the next time the server starts.
- **Save and restart** restarts the server on it right away. Downloads in progress stop, and pages and apps reconnect. A page opened on the server's own address (e.g. `http://nas:8000`) waits for the server and opens the new address by itself; you stay signed in.

When the port comes from the `DOWNTIFY_PORT` (or `PORT`) environment variable or from `--port` on the command line — those always win — the field shows the port in use but can't be edited, and the page says which one sets it. Remove it (and restart) to choose the port in Settings.

::: warning Docker's bridge network maps a fixed port
In the default Docker setup (`ports: - '8000:8000'`), the container's port has to match the mapping. After changing it in Settings, change the mapping to the new port (`'9000:9000'`) and recreate the container — or run with `network_mode: host`. Otherwise Downtify can't be reached. To get back in, set `DOWNTIFY_PORT` to the old port: it wins over Settings.
:::

Behind a [reverse proxy](mobile-apps.md#behind-a-reverse-proxy), point the proxy at the new port too. [Paired apps](mobile-apps.md) use the address they were given: after a port change, enter the new one in the app.
