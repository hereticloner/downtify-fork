---
icon: lucide/git-merge
---

# Upstream port — wave 1

Seven changes from [upstream Downtify](https://github.com/henriquesebastiao/downtify) were ported into this fork as one wave. Each one is listed below with what changed, what you get out of it, and the upstream commit it came from. In the fork they are the `feat: Upstream W1-N — …` commit series, each with the tests that go with it.

| Item | Change | Upstream commit |
|------|--------|-----------------|
| W1-1 | The Queue tab stays where you left it while a batch downloads | `e2dac1c` |
| W1-2 | A title with ` - ` matches an upload that credits a guest artist | `770ac5f` |
| W1-3 | SQLite connections close when their `with` block ends | `8ebcbe0` |
| W1-4 | Library upgrades skip folders that refuse writes | `affa41d` |
| W1-5 | A checked sign-in is kept in memory for 30 seconds | `2a497c4` |
| W1-6 | `GET /cover?size=` serves a scaled cover | `346b7d8` |
| W1-7 | A parity gate for the eight languages the app ships | none — fork-only |

## W1-1 — The Queue tab stays put during a batch

**Upstream commit:** `e2dac1c` — "Keep the Queue tab put while a batch downloads" (fixes upstream issue #455).

**What changed.** The Queue page watched the number of running downloads and switched itself to the **In progress** tab whenever that number went up. During a batch that happens over and over: one item finishes, the next one starts, the count goes up again — so reading the **Waiting** or **Failed** list kept pulling you back to **In progress**. The jump now happens only when downloads start from idle (nothing running → something running), which is what it was there for.

**What you get.** The tab you picked stays on screen for the whole batch, so the waiting and failed lists can be read while the download runs. Nothing else moves: the first download of a batch still takes you to **In progress** when you are on another tab.

**Where it lives.** The new pure helper `shouldJumpToActive()` in `frontend/src/lib/queueTab.js`, used by `frontend/src/views/QueueView.vue`, with `frontend/src/__tests__/queueTab.test.js`. See [Queue](queue.md).

## W1-2 — A title with ` - ` matches a `(feat. …)` upload

**Upstream commit:** `770ac5f` — "Match titles with a dash against candidates with a feat. suffix" (fixes upstream issue #433).

**What changed.** Before a search result is accepted, the matcher rewrites a trailing ` - Suffix` into ` (Suffix)` on both names, so Spotify's dash style and YouTube Music's bracketed one count as the same. That rewrite only touches the *last* ` - ` segment, so when the title itself contains ` - ` the two sides came out differently — or not at all, because the candidate's `(feat. …)` credit blocks the rewrite on its side — and neither the exact nor the prefix comparison could match. The plain, unrewritten names are now compared as well, under the same prefix and version-qualifier rules.

**What you get.** A track whose title contains a dash is no longer passed over just because the YouTube upload credits a guest artist: `Tu - Na Sever, Ya - Na Yug` matches `Tu - Na Sever, Ya - Na Yug (feat. Ирина Билык)`. The version rules still hold — a plain title is still not accepted for a live, instrumental or other-version upload, and `A - B` still does not match `A - B (Live)`.

**Where it lives.** `_names_match()` in `downtify/providers.py`, with `tests/test_providers.py`. The matching rules are described in [How it works](../how-it-works.md#2-audio-match-youtube-music-then-youtube).

## W1-3 — SQLite connections close when their `with` block ends

**Upstream commit:** `8ebcbe0` — "fix: close SQLite connections when their with-block ends".

**What changed.** `with conn:` on a plain connection only commits or rolls back. On Python 3.11 and later the connection then lingers — with the database, `-wal` and `-shm` file descriptors open — until the cyclic garbage collector gets to it. Short lookups in a loop piled those up: upstream measured `GET /api/playlists/batches` checking around 5,000 tracks on a large library, and two concurrent Library loads were enough to exhaust the default 1,024-descriptor limit, after which uvicorn's `accept()` failed with `OSError: [Errno 24]` and requests answered 500. `downtify/sqlite_utils.py` now provides `ClosingConnection`, a `sqlite3.Connection` subclass whose `__exit__` closes the connection; `connect_sqlite()` builds those, and `PlaylistMonitorDB` — the one place that used `sqlite3.connect` directly — goes through the same helper.

**What you get.** The Library page stops running the server out of file descriptors on large libraries. The connections are still closed at the same points as before; they are just closed *now* instead of whenever the garbage collector happens to run.

**Where it lives.** `downtify/sqlite_utils.py` (`ClosingConnection`, `connect_sqlite()`) and `downtify/monitor.py` (`PlaylistMonitorDB._connect()`), with `tests/test_sqlite_utils.py`.

## W1-4 — Library upgrades skip folders that refuse writes

**Upstream commit:** `affa41d` — "fix: skip library upgrades on read-only filesystems" (fixes upstream issue #443).

**What changed.** An upgrade rewrites tags in place, so on a filesystem that refuses writes — a read-only mount, or a folder the container may not write to — the track is now skipped with an explanation *before* any metadata, artwork or lyrics lookup. `downtify/library_upgrade.py` detects that in two cheap ways: the mount's own read-only flag (`os.statvfs`) and the write permission on the folder the working copy is written into. A folder that turns read-only while a track is being worked on is caught too, by the `EROFS` error the copy step reports. The folder is warned about once per process instead of once per track.

**What you get.** A read-only music folder no longer fails the whole upgrade run. Its tracks stay playable and stay in their playlists, and their files and mount permissions are left alone. A skipped track is not remembered as successfully checked, so it is considered again once its folder becomes writable. Unexpected permission, disk-space and I/O errors still show up as failures. This is different from [existing-folder enrichment](external-library.md), which keeps artwork and lyrics in Downtify's own data folder without rewriting the protected audio files.

**Where it lives.** `downtify/library_upgrade.py` (`_read_only_filesystem()`, `_warn_read_only_once()`, `UpgradeOutcome.checked`), with `tests/test_library_upgrade.py`. See [Upgrade library](library-upgrade.md#read-only-music-folders).

## W1-5 — A checked sign-in is kept in memory for 30 seconds

**Upstream commit:** `2a497c4` — "perf: cache checked sign-ins for 30 s, dropped on any revocation".

**What changed.** The auth middleware checked the session cookie or the device token against SQLite on every request, on the event loop. A checked answer is now kept in memory for up to 30 seconds, and never past the session's own expiry. Every way of ending access clears that cache at once: signing out, signing a user out everywhere, revoking a device or everything, and any account change (name, role, password, deletion) through a new change listener on the user store. A lookup that started before a clear does not store its answer, so a revoked session can never be cached back in. With accounts turned off (`DOWNTIFY_DISABLE_AUTH`) nothing is cached at all, because there everybody is the same admin and the account's state has to be read fresh.

**What you get.** Signed-in pages answer from memory instead of a database round trip on every request. Revoking access still takes effect at once — the cache is dropped the moment you sign out, unpair an app or change an account.

**Where it lives.** `downtify/auth.py` (`_SignInCache`, `SIGN_IN_CACHE_SECONDS`) and `downtify/users.py` (`UserStore.add_change_listener()`), with `tests/test_auth_cache.py`. See [Users & Sign-in](users.md#managing-users).

## W1-6 — `GET /cover?size=` serves a scaled cover

**Upstream commit:** `346b7d8` — "feat: serve scaled library covers with GET /cover?size=".

**What changed.** The web interface drew every Library grid tile and list row from the full embedded picture (around 640 px, roughly 1.6 MB once decoded) although it shows it at 40–250 px. `/cover` now takes an optional `size` — `150`, `300` or `600` px on the longest side; any other number rounds up to the next of those, and anything larger is the full picture — and serves the scaled copy that `CoverThumbs` already made for the mobile API, cached under `/data/cover_thumbs` and sent with an `ETag`. Without `size` the response is unchanged, and a cover that only the cover cache knows about (read-only extra folders) still comes back full size. `CoverThumbs` now runs at most four ffmpeg scalings at a time, since a first scroll through a large library asks for thousands of thumbnails.

**What you get.** An optional query parameter on the cover endpoint, so a client can ask for a small cover instead of the full picture. The path, the parameters and the default response are unchanged, so existing clients keep working as before.

**Where it lives.** `main.py` (`GET /cover`, `_cover_size()`) and `downtify/cover_thumbs.py` (`MAX_PARALLEL_SCALES`), with `tests/test_cover_route.py`. See the [API reference](../api-reference.md#get-cover).

```bash
# the same cover, scaled to 300 px on the longest side
curl -o cover.jpg "http://localhost:8000/cover?file=Artist/Track.mp3&size=300"
```

## W1-7 — A parity gate for the eight languages the app ships

**Upstream commit:** none — this one is fork-only. Upstream checks key parity inside `frontend/src/__tests__/i18n.test.js`, over the locales that are registered in the runtime registry; there is no dedicated parity file upstream.

**What changed.** The fork adds `frontend/src/__tests__/i18nParity.test.js`, which finds the locale files on disk instead of reading the registry. A new locale file therefore cannot escape the gate by forgetting to register it in `frontend/src/i18n/index.js`. The gate checks that the files on disk are exactly the eight the app ships (`bg`, `el`, `en`, `es`, `fr`, `hu`, `pt-BR`, `tr`), that `en.js` is there as the reference, that every other locale has exactly the same key paths as it — plural forms contribute one path per form — and that no locale has an empty value, a value that is not a string, or a message group without entries. The existing `i18n.test.js` keeps covering the runtime behaviour of `t()`: interpolation and plural selection. Upstream's own tree also carries a German locale (`88f53eb`); this fork does not, so the gate pins the fork's own eight.

**What you get.** A missing or half-translated key in any of the eight languages fails the test suite instead of turning into raw English in the interface. Adding a language means one locale file, one entry in `frontend/src/i18n/index.js` and one more code in the gate's list — see [Internationalization](internationalization.md#adding-a-new-language).

**Where it lives.** `frontend/src/__tests__/i18nParity.test.js` and `frontend/src/__tests__/i18n.test.js`.
