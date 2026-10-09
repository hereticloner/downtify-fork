---
icon: lucide/hard-drive
---

# Server Settings

**Settings → Server** holds how the server itself runs. Only admins see it (see [Users & Sign-in](users.md#admins-and-users)).

## The Downtify Mirror device

For [Spotify Mirror](spotify-mirror.md) the server can ship its own silent Spotify Connect client: the `mirror` service (go-librespot), named **Downtify Mirror**, always online, playing at volume 0 through ALSA's `null` device — plays sent to it are only there to be counted by Spotify.

Setting it up on a compose server:

1. `docker compose up -d mirror` — the first start logs a short pairing code:
   ```
   docker compose logs mirror | grep -A2 "code"
   ```
2. On any phone or computer, open [spotify.com/pair](https://spotify.com/pair) and enter that code with the account the mirror should run under (the same Premium account the Spotify Mirror is connected with).
3. `docker compose logs -f mirror` shows the login complete; the credentials are stored in `mirror/state.json`, so restarts don't need pairing again.

The device then shows up in **Settings → Spotify Mirror → Load devices**; plays started in Downtify begin there — silently — and land in your Spotify history.

> Password logins for Connect clients were removed by Spotify, so the device pairs once with a code (or interactive OAuth) instead; the credentials survive in `state.json`.

## Changing the port

## Changing the port

Downtify listens on port **8000**. An admin can choose another one in **Settings → Server → Port** (1024–65535):

- **Save** keeps it for the next time the server starts.
- **Save and restart** restarts the server on it right away. Downloads in progress stop, and pages and apps reconnect. A page opened on the server's own address (e.g. `http://nas:8000`) waits for the server and opens the new address by itself; you stay signed in.

When the port comes from the `DOWNTIFY_PORT` (or `PORT`) environment variable or from `--port` on the command line — those always win — the field shows the port in use but can't be edited, and the page says which one sets it. Remove it (and restart) to choose the port in Settings.

::: warning Docker's bridge network maps a fixed port
In the default Docker setup (`ports: - '8000:8000'`), the container's port has to match the mapping. After changing it in Settings, change the mapping to the new port (`'9000:9000'`) and recreate the container — or run with `network_mode: host`. Otherwise Downtify can't be reached. To get back in, set `DOWNTIFY_PORT` to the old port: it wins over Settings.
:::

Behind a [reverse proxy](mobile-apps.md#behind-a-reverse-proxy), point the proxy at the new port too. [Paired apps](mobile-apps.md) use the address they were given: after a port change, enter the new one in the app.
