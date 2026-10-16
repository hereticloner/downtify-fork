"""Library + activity statistics for the Stats page.

Reads only existing stores: the activity log (downloads, playback),
likes, the playlist batch store, the library listing, and - when the
Spotify history import is on - the plays mirrored out of Spotify. No new
tables.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from .activity import RETENTION_DAYS

#: How many mirrored Spotify plays one response carries. The store keeps
#: a page of fifty; the page shows the newest handful of it.
SPOTIFY_RECENT_LIMIT = 10

#: How many of your own plays the response carries. The Stats page lists
#: them newest first and filters them by day when a heatmap cell is
#: clicked, so this has to be deeper than one evening of listening -
#: but not the whole retained year, which would dwarf every other field.
PLAYBACK_RECENT_LIMIT = 400

#: How many queues the "most played from" list names.
TOP_CONTEXTS_LIMIT = 10

#: How many weeks the listening heatmap spans. Tied to the activity
#: log's own retention, so the grid never promises days the log has
#: already pruned.
HEATMAP_WEEKS = max(1, RETENTION_DAYS // 7)


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


def _text(value: Any) -> str:
    """A trimmed string, whatever the row actually held."""

    return str(value or '').strip()


def _played_days(activity: Any) -> Counter:
    """``{YYYY-MM-DD: plays}`` for one kind of activity entry."""

    return Counter(
        day for day in (_parse_at(e.get('at')) for e in activity or []) if day
    )


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _detail(entry: dict[str, Any]) -> dict[str, Any]:
    """An entry's ``detail`` object, or ``{}`` if it isn't readable.

    The log writes JSON, but a row can still arrive empty or malformed
    (a restore from an older backup, a hand edit). Stats must show the
    play rather than fail the whole page over its detail.
    """

    raw = entry.get('detail')
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _play_source(entry: dict[str, Any]) -> tuple[str, str]:
    """``(queue title, queue kind)`` a play was served from.

    Players report where the queue came from - a playlist, an album, an
    artist, the library - so the Stats page can say *what you were
    playing* rather than only how much. Both are empty for a play the
    player didn't attribute (an old entry, or a bare library play).
    """

    track = _detail(entry).get('track')
    if not isinstance(track, dict):
        return '', ''
    return _text(track.get('context')), _text(track.get('context_type'))


def _recent_plays(
    entries: list[dict[str, Any]], limit: int = PLAYBACK_RECENT_LIMIT
) -> list[dict[str, Any]]:
    """Your newest plays, newest first, each with the queue it came from.

    *entries* arrives newest first (the log's own order), so the newest
    page of them is simply the head of the list.
    """

    out: list[dict[str, Any]] = []
    for entry in list(entries or [])[:limit]:
        at = str(entry.get('at') or '')
        context, kind = _play_source(entry)
        out.append({
            'at': at,
            'date': _parse_at(at),
            'summary': _text(entry.get('summary')),
            'context': context,
            'context_type': kind,
        })
    return out


def _top_contexts(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The queues your plays came from, most played first."""

    counts = Counter(
        context
        for context, _kind in (_play_source(e) for e in entries or [])
        if context
    )
    return [
        {'context': context, 'count': count}
        for context, count in counts.most_common(TOP_CONTEXTS_LIMIT)
    ]


def build_activity_heatmap(
    activity: list[dict[str, Any]],
    weeks: int = HEATMAP_WEEKS,
    *,
    today: Optional[date] = None,
) -> list[dict[str, Any]]:
    """One ``{date, count}`` per day for the last *weeks* weeks.

    Oldest first, and dense: a day without a play is a zero rather than
    a gap, so the grid the page draws always has ``weeks * 7`` cells
    (see ``frontend/src/lib/heatmap.js``). The window is capped at the
    activity log's retention, since older plays are pruned and would
    read as empty days anyway. *today* is only there to keep tests off
    the clock.
    """

    span = max(1, min(int(weeks or 0), HEATMAP_WEEKS)) * 7
    end = today or _today()
    counts = _played_days(activity)
    out: list[dict[str, Any]] = []
    day = end - timedelta(days=span - 1)
    for _ in range(span):
        stamp = day.isoformat()
        out.append({'date': stamp, 'count': counts.get(stamp, 0)})
        day += timedelta(days=1)
    return out


def build_listening_streak(
    activity: list[dict[str, Any]], *, today: Optional[date] = None
) -> int:
    """Days in a row that had at least one play.

    A day still to come doesn't break the streak: until it is over,
    yesterday's run still counts. Nothing played today *or* yesterday
    means zero - that is a finished streak, not one waiting to start.
    *today* is only there to keep tests off the clock.
    """

    played = _played_days(activity)
    cursor = today or _today()
    if cursor.isoformat() not in played:
        cursor -= timedelta(days=1)
    streak = 0
    while cursor.isoformat() in played:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


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

    The ``playback`` block carries the listening heatmap (one entry per
    day of the retained window), the current streak and the busiest day,
    all read from the same play entries as ``total`` and ``top_tracks``.
    It also carries ``recent`` - your newest plays, each with the queue
    it was served from - and ``top_contexts``, those plays grouped by
    queue, so the page can answer "what did I play, and from where".
    """

    downloads = _activity_kinds(activity, 'download')
    playbacks = _activity_kinds(activity, 'playback')

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

    # The heatmap is dense (a playless day is a zero), so the busiest
    # day is the first entry that isn't: the empties only lead.
    heatmap = build_activity_heatmap(playbacks)
    busiest = next(
        (day for day in reversed(heatmap) if day['count'] > 0), None
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
            'heatmap': heatmap,
            'streak_days': build_listening_streak(playbacks),
            'best_day': (
                {'date': busiest['date'], 'count': busiest['count']}
                if busiest
                else {'date': '', 'count': 0}
            ),
            # What the plays were, and which queue served them: the page
            # lists these and filters them by the day a heatmap cell
            # stands for.
            'recent': _recent_plays(playbacks),
            'top_contexts': _top_contexts(playbacks),
        },
        'spotify': {
            'recent': recent,
            'play_count': _spotify_play_count(spotify_play_count, len(recent)),
        },
    }
