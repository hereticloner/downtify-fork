"""Library + activity statistics for the Stats page.

Reads only existing stores: the activity log (downloads, playback),
likes, the playlist batch store, and the library listing. No new tables.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


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


def build_stats(
    *,
    activity: Any,
    track_count: int,
    likes: int = 0,
    playlist_count: int = 0,
) -> dict[str, Any]:
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
    per_day = Counter(
        _parse_at(e.get('at')) for e in downloads if e.get('at')
    )

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
    }
