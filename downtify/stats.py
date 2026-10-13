"""Library + activity statistics for the Stats page.

Reads only existing stores: the activity log (downloads, playback),
likes, the playlist batch store, the library listing, and - when the
Spotify history import is on - the plays mirrored out of Spotify. No new
tables.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Optional

#: How many mirrored Spotify plays one response carries. The store keeps
#: a page of fifty; the page shows the newest handful of it.
SPOTIFY_RECENT_LIMIT = 10


def _activity_kinds(log: Any, kind: str) -> list[dict[str, Any]]:
    """Every entry of one kind, via the log's own pagination."""

    out: list[dict[str, Any]] = []
    before = 0
    while True:
        page = log.entries(kinds=[kind], limit=100, before=before)
        out.extend(page['entries'])
        nxt = int(page.get('next') or 0)
        if not nxt or not page['entries']:
            break
        before = nxt
    return out


def _parse_at(value: str) -> str:
    # entries carry ISO strings; the first 10 chars are the date.
    return str(value or '')[:10]


def _spotify_recent(rows: Any) -> list[dict[str, Any]]:
    """The newest mirrored plays, trimmed to what the page shows.

    Rows arrive newest first from the history store; anything that is
    not a row is skipped rather than rendered as a blank line.
    """

    out: list[dict[str, Any]] = []
    for row in list(rows or [])[:SPOTIFY_RECENT_LIMIT]:
        if not isinstance(row, dict):
            continue
        out.append({
            'played_at': str(row.get('played_at') or ''),
            'artist_name': str(row.get('artist_name') or ''),
            'track_name': str(row.get('track_name') or ''),
            'album_name': str(row.get('album_name') or ''),
        })
    return out


def _spotify_play_count(value: Any, shown: int) -> int:
    """How many plays the history store holds in total."""

    try:
        count = int(value)
    except (TypeError, ValueError):
        count = 0
    # Never below what this same response lists.
    return max(0, count, shown)


def build_stats(
    *,
    activity: Any,
    track_count: int,
    likes: int = 0,
    playlist_count: int = 0,
    spotify_recent: Optional[list[dict[str, Any]]] = None,
    spotify_play_count: Optional[int] = None,
) -> dict[str, Any]:
    """The numbers the Stats page renders.

    *spotify_recent* is the page of plays mirrored out of Spotify,
    newest first (see ``downtify.spotify_history``); *spotify_play_count*
    is how many the store holds altogether. Without them the ``spotify``
    block is simply empty - the import is opt-in, so a server that never
    turned it on has nothing to report.
    """

    downloads = _activity_kinds(activity, 'download')
    playbacks = _activity_kinds(activity, 'playback')

    from datetime import datetime, timezone  # noqa: PLC0415

    now = datetime.now(timezone.utc)

    last_30 = 0
    for entry in downloads:
        try:
            at = datetime.fromisoformat(str(entry.get('at') or ''))
            days = (now - at).total_seconds() / 86400
            if days <= 30:
                last_30 += 1
        except (TypeError, ValueError):
            continue

    top_tracks = Counter(
        str(e.get('summary') or '') for e in playbacks if e.get('summary')
    )
    per_day = Counter(_parse_at(e.get('at')) for e in downloads if e.get('at'))
    recent = _spotify_recent(spotify_recent)

    return {
        'library': {
            'tracks': track_count,
            'playlists': playlist_count,
            'likes': likes,
        },
        'downloads': {
            'total': len(downloads),
            'last_30_days': last_30,
            'per_day': [
                {'date': day, 'count': count}
                for day, count in sorted(per_day.items())
            ][-30:],
        },
        'playback': {
            'total': len(playbacks),
            'top_tracks': [
                {'summary': summary, 'count': count}
                for summary, count in top_tracks.most_common(10)
            ],
        },
        'spotify': {
            'recent': recent,
            'play_count': _spotify_play_count(spotify_play_count, len(recent)),
        },
    }
