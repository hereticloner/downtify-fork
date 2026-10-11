---
icon: lucide/sliders-horizontal
---

# Smart Collections

A smart collection is a [collection](collections.md) with rules. Besides the
playlists you add by hand, it also carries a list of conditions, and its
members are recomputed from those conditions every time it is opened: the
playlists that match are unioned with the ones you added manually.

Nothing is copied or moved. A rule only decides which playlists *appear* in
the collection — the playlists, their M3U files and the audio are untouched,
exactly like a plain collection.

## Adding rules

Open a collection and click the **sliders** button. The rule editor lets you
add one row per condition. Rules combine with **AND**: a playlist joins the
collection only when it matches *every* rule. There is no OR on purpose — to
cover two genres, make two collections.

| Rule type | Field | What it matches |
|-----------|-------|-----------------|
| **Added** | `from` / `to` dates | When the playlist itself was added (its M3U file's date), within the range. Either end can be left blank. |
| **Play count** | `min` / `max` | How many times the playlist's tracks have been played in total, from the activity log. Either end can be left blank. |
| **Genre** | a value | A playlist that has at least one track tagged with this genre. |
| **Artist** | a value | A playlist that has at least one track by this artist (a `;`/`,`/`&`-separated artist list counts too). |
| **Album** | a value | A playlist that has at least one track from this album. |
| **Format** | a value | A playlist that has at least one track in this codec or file type (`flac`, `mp3`, `m4a`, `opus`, …). |

Field rules look at a playlist's **tracks** and pass when **any** track
matches, so a compilation can belong to several genre collections at once.
Text values are matched after case- and accent-folding, and artist names are
matched on the whole name, not as a substring (`Rock` does not match
`The Rockers`).

::: tip Examples
- **New this month** — one `added` rule with the `from` date set to the first
  of the month.
- **Never played** — one `play count` rule with `max` set to `0`.
- **Lossless favourites** — a `format` rule with the value `flac`.
:::

Leaving every row empty (or removing them all) saves an empty rule list, and
the collection becomes a plain, static one again.

## In the library

A collection that has rules is marked with a **Smart** badge on the
[Collections](collections.md) page. The playlist chips you see are the union
of your manual picks and the rule matches, so the same playlist can show up
because you added it *and* because a rule selected it.

## Where the rules are stored

The rules live in the same one JSON file per collection, as an optional
`rules` field — a collection without rules keeps the exact document it always
had:

```json
{
  "version": 1,
  "name": "Lossless",
  "playlists": ["Chill"],
  "rules": [{ "type": "format", "value": "flac" }]
}
```

Because the rules are evaluated from the library on every read, they cost
nothing to keep in sync: add a FLAC playlist and it appears the next time the
collection is opened.

## API

| Endpoint | What it does |
|----------|--------------|
| `GET /api/collections/{name}` | One collection with its members computed: static playlists unioned with the rule matches (`rules` and `computed` are included) |
| `POST /api/collections/{name}/rules` | Replace the rule list; body `{ "rules": [ ... ] }`. An empty list makes the collection static |

See the [API reference](../api-reference.md#collections) for request and
response shapes.
