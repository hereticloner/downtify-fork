---
icon: lucide/share-2
---

# Navidrome

Mirror the playlists you download into [Navidrome](https://www.navidrome.org/), so they show up in any Subsonic client. It is off by default and configured in **Settings**.

## Setup

1. Make sure Navidrome's music folder includes Downtify's downloads folder. Navidrome can only add tracks to a playlist once it has scanned them.
2. In **Settings → Navidrome**, enable Navidrome and enter its URL, username and password.
3. Optionally, add an **admin** username and password. Downtify then asks Navidrome to scan the library before matching new tracks, instead of waiting for Navidrome's own scheduled scan.

## Testing the connection

Press **Test connection** under the fields to check them before you save — it uses what is typed in the form, saved or not, and changes nothing. It reports:

| Result | What it means |
|--------|---------------|
| **Connected to navidrome 0.53.3.** | The address is right and the username and password were accepted |
| **This account can start library scans.** | The account used for scans is an admin. That is the admin username you filled in, or the normal one when you left it empty |
| **This account can't start library scans.** | Navidrome only lets admins start a scan, and it doesn't say so when Downtify tries — new songs simply show up late. Fill in an admin username and password |
| **The admin account isn't an admin.** | The admin login you entered works but belongs to a normal user |
| **Navidrome rejected the admin username or password.** | The scan account's login is wrong; the main login is reported separately |
| **Navidrome rejected the username or password.** | The server answered, but not to this login |
| **Can't reach … / didn't answer in time.** | Wrong address or port, the server is down, or it isn't reachable from the Downtify container |
| **Doesn't look like Navidrome.** | Something answered, but not the Subsonic API — often a wrong port, or a base URL that is missing from the address |
| **The HTTPS certificate isn't trusted.** | Use `http://` on your own network, or a certificate from a trusted authority; Downtify doesn't skip certificate checks |

The scan rights are only looked up — testing never starts a scan. Editing any field clears the last result, and the button stays disabled until the address, username and password are filled in.

::: info Nothing is sent back to the page
The answer carries only what was found — a version, a path, a status — never your password or the request Downtify made.
:::

## Playlist sync

With **Create playlists in Navidrome** on, Downtify creates (or updates) a Navidrome playlist with the same name after:

- a Spotify playlist download finishes,
- a [Playlist Monitor](playlist-monitor.md) sweep adds tracks,
- tracks are deleted from the Library, or [library paths are fixed](library-catalog.md#fix-library-paths).

Tracks are matched to Navidrome songs by path first, then by tags. **Make Navidrome playlists public** controls the playlist's visibility in Navidrome.

::: warning Files whose tags don't match the playlist are deleted
When a playlist is refreshed (after deletes, **Fix library paths**, or **Download missing** on an already complete playlist), a library file registered for a Spotify track is **deleted from disk** if its embedded title/artist clearly don't match that track — Downtify treats it as a wrong download. Keep this in mind if you edit tags by hand.
:::

## Playlist cover art

Nothing to set up: with [Save playlist cover art](playlist-cover-art.md) on, Navidrome picks up the `.jpg` Downtify writes next to the playlist's M3U as a **sidecar image** — its own way of resolving playlist artwork — as long as its music folder covers that file. Downtify makes no API call for it.

## Playlist downloads

The **Library** page lists the Spotify playlists you've downloaded through Downtify under **Playlist downloads**. Expand it to see, for each playlist, how many tracks are in your library against the current Spotify track list. From there you can:

- **Download missing** — queue only the tracks not in your library yet.
- **Play** the tracks already downloaded.
- Expand a playlist to see and download individual missing tracks.
- **Delete** the playlist — see below.

### Deleting a playlist

Deleting a playlist (from this panel, or with **Delete playlist** next to the Library's playlist filter) removes from disk every track registered to it — **including tracks other playlists also contain** — plus its M3U file and the [cover art](playlist-cover-art.md) saved beside it, and stops tracking it. Other playlists that shared those tracks get their M3U and Navidrome playlist rewritten in the background.
