---
icon: lucide/layers
---

# Collections

Collections are named groups of the playlists already in your library — a level above the playlist. Where a playlist holds songs, a collection holds playlists, so a library that has grown to dozens of downloaded playlists can be sorted into a handful of groups like *Road trip*, *Dinner party* or *2024 albums*.

A collection only groups: it never copies or moves a song, never rewrites a playlist and never touches the audio. Deleting a collection removes the group and nothing else.

## Opening the page

The page lives at `/library/collections`, in the Library area of the app (the **Library** item in the sidebar stays highlighted while you are there).

## Creating a collection

1. Type a name into the box at the top of the page.
2. Press **Enter** or click **Create**.

The name is sanitized the same way a playlist name is (it becomes the name of the file behind it), so characters that a filename can't hold are folded out. A name that is already in use is rejected with an error instead of overwriting the existing collection.

## Adding playlists

Every collection has an **Add a playlist by name** box. Type a name and press **Enter** to add one — or start typing and pick from the autocomplete list, which is the sorted set of playlist names Downtify already shows in the Library, so a name can't be mistyped.

The box is checked against the library: a name that isn't a playlist Downtify knows about gives an error and nothing is added. The same playlist can be in several collections; adding it to one doesn't remove it from another.

## Opening a playlist

Each playlist in a collection is shown as a chip, and every chip is a link: click it to open that playlist's page (the built-in player's playlist view, with its tracks).

## Deleting a collection

Click the trash button on a collection and confirm. Only the collection is deleted — its playlists, their M3U files and their audio all stay exactly where they were.

::: info Removing one playlist vs. deleting the collection
To drop a single playlist from a collection without deleting the group, use the [API](#api) (`POST /api/collections/{name}/items` with a `remove` list). The page itself offers adding playlists and deleting a whole collection.
:::

## Where collections are stored

Each collection is one JSON file under the downloads folder:

```
<downloads>/Playlists/.collections/<name>.json
```

```json
{
  "version": 1,
  "name": "Road trip",
  "playlists": ["Chill", "Drive"]
}
```

There is no database and no migration: the file is read when the page opens and rewritten on every change. Because it lives inside the downloads volume, it is included in whatever backup or sync covers that volume. Downtify only reads the playlist **names** — the playlists themselves, their M3U files and media servers such as [Navidrome](slskd-navidrome.md) are not affected by collections at all.

## API

| Endpoint | What it does |
|----------|--------------|
| `GET /api/collections` | List every collection with its playlist names |
| `POST /api/collections` | Create a collection; body `{name}`. `409` if the name already exists |
| `POST /api/collections/{name}` | Rename a collection; body `{name}` |
| `POST /api/collections/{name}/items` | Add and/or remove playlists; body `{add: [...], remove: [...]}`. A name that isn't a library playlist gives `404` |
| `DELETE /api/collections/{name}` | Delete the collection (never its playlists) |

See the [API reference](../api-reference.md#collections) for request and response shapes.