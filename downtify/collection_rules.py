"""The rule engine behind smart collections.

A smart collection stores a list of *rules* next to its static playlist
names. Each rule is a condition on a library **playlist**; a playlist is a
member of the smart collection when every rule holds (rules combine with
AND). Conditions that name a field (genre, artist, album, format) look at
the playlist's tracks and pass when at least one track matches; ``added``
looks at when the playlist itself was downloaded and ``plays`` at how many
times its tracks have been played in total.

The engine is pure - it works on plain dicts the API layer already has,
needs no disk or database, and is what makes a collection live: the saved
static members and the rule-derived ones are unioned on every read.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any, Optional

from .library_catalog import fold_text

RULE_TYPES = ('added', 'plays', 'genre', 'artist', 'album', 'format')

_ARTIST_SPLIT = re.compile(r'\s*[;,/]\s*|\s+&\s+')


class RuleError(ValueError):
    """A rule set the engine can't express. ``status_code`` mirrors the
    other collection errors so the API layer can answer directly."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _as_date(value: Any, field: str) -> Optional[date]:
    text = str(value or '').strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise RuleError(f'{field} is not a date: {text!r}') from exc


def _as_int(value: Any, field: str) -> Optional[int]:
    if value is None or not str(value).strip():
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise RuleError(f'{field} is not a number: {value!r}') from exc


def normalize_rules(raw: Any) -> list[dict[str, Any]]:
    """Validate a stored rule list and return it in a canonical shape.

    Raises :class:`RuleError` (status 400) on anything the engine can't
    evaluate, so a bad payload is rejected at the API boundary instead of
    silently matching nothing later.
    """

    if raw is None:
        return []
    if not isinstance(raw, list):
        raise RuleError('rules must be a list')
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise RuleError('each rule must be an object')
        rtype = str(item.get('type') or '').strip()
        if rtype not in RULE_TYPES:
            raise RuleError(f'unknown rule type {rtype!r}')
        if rtype == 'added':
            start = _as_date(item.get('from'), 'from')
            end = _as_date(item.get('to'), 'to')
            if start is None and end is None:
                raise RuleError('an added rule needs a from or to date')
            if start is not None and end is not None and start > end:
                raise RuleError('the from date is after the to date')
            out.append({
                'type': 'added',
                'from': start.isoformat() if start else '',
                'to': end.isoformat() if end else '',
            })
            continue
        if rtype == 'plays':
            low = _as_int(item.get('min'), 'min')
            high = _as_int(item.get('max'), 'max')
            if low is None and high is None:
                raise RuleError('a plays rule needs a min or max')
            if low is not None and high is not None and low > high:
                raise RuleError('min is above max')
            out.append({'type': 'plays', 'min': low, 'max': high})
            continue
        value = str(item.get('value') or '').strip()
        if not value:
            raise RuleError(f'a {rtype} rule needs a value')
        out.append({'type': rtype, 'value': value})
    return out


def _text_hits(actual: str, want: str, *, split_artists: bool) -> bool:
    folded = fold_text(want)
    if not folded:
        return False
    if not split_artists:
        return fold_text(actual) == folded
    candidates = [actual, *_ARTIST_SPLIT.split(actual)]
    return any(
        fold_text(part) == folded for part in candidates if part.strip()
    )


def _format_hits(track: dict[str, Any], want: str) -> bool:
    folded = fold_text(want)
    if not folded:
        return False
    codec = fold_text(str(track.get('codec') or ''))
    if codec == folded:
        return True
    name = str(track.get('file') or '')
    suffix = name.rsplit('.', 1)[-1] if '.' in name else ''
    return fold_text(suffix) == folded


def _playlist_plays(
    member: dict[str, Any], play_counts: dict[str, int]
) -> int:
    return sum(
        int(play_counts.get(str(f), 0)) for f in member.get('files') or []
    )


def _added_in_range(member: dict[str, Any], rule: dict[str, Any]) -> bool:
    try:
        when = datetime.fromtimestamp(
            int(member.get('added') or 0), tz=timezone.utc
        ).date()
    except (OverflowError, OSError, ValueError):
        return False
    start = _as_date(rule.get('from'), 'from')
    end = _as_date(rule.get('to'), 'to')
    if start is not None and when < start:
        return False
    if end is not None and when > end:
        return False
    return True


def _rule_holds(
    rule: dict[str, Any],
    member: dict[str, Any],
    tracks: dict[str, dict[str, Any]],
    play_counts: dict[str, int],
) -> bool:
    rtype = rule.get('type')
    if rtype == 'added':
        return _added_in_range(member, rule)
    if rtype == 'plays':
        total = _playlist_plays(member, play_counts)
        low = rule.get('min')
        high = rule.get('max')
        if low is not None and total < int(low):
            return False
        if high is not None and total > int(high):
            return False
        return True
    # Field rules pass when any of the playlist's tracks matches.
    field_tracks = [
        tracks[str(f)] for f in member.get('files') or [] if f in tracks
    ]
    if rtype == 'format':
        return any(
            _format_hits(track, str(rule.get('value') or ''))
            for track in field_tracks
        )
    field = str(rtype)
    return any(
        _text_hits(
            str(track.get(field) or ''),
            str(rule.get('value') or ''),
            split_artists=rtype == 'artist',
        )
        for track in field_tracks
    )


def playlist_matches(
    rules: list[dict[str, Any]],
    member: dict[str, Any],
    tracks: dict[str, dict[str, Any]],
    play_counts: dict[str, int],
) -> bool:
    """Whether *member* satisfies every rule (AND). No rules match all."""

    return all(
        _rule_holds(rule, member, tracks, play_counts) for rule in rules
    )


def resolve_collection(
    data: dict[str, Any],
    *,
    playlists: list[dict[str, Any]],
    tracks: dict[str, dict[str, Any]],
    play_counts: dict[str, int],
) -> dict[str, Any]:
    """Merge the collection's static members with its rule-derived ones.

    A collection with no rules is returned untouched, so a plain
    collection's document (and the API response built from it) is
    byte-for-byte what it always was.
    """

    rules = data.get('rules') or []
    static = [str(p) for p in data.get('playlists') or []]
    if not rules:
        return dict(data)
    computed = [
        str(member.get('name') or '')
        for member in playlists
        if member.get('name')
        and playlist_matches(rules, member, tracks, play_counts)
    ]
    union = list(static)
    for name in computed:
        if name not in union:
            union.append(name)
    result = dict(data)
    result['playlists'] = union
    result['rules'] = list(rules)
    result['computed'] = [name for name in computed if name not in static]
    return result
