"""Pure helpers for playing and measuring a resolved collection."""

from __future__ import annotations

from typing import Any


def _members(data: dict[str, Any], playlists: list[dict[str, Any]]):
    by_name = {
        str(playlist.get('name') or ''): playlist
        for playlist in playlists
        if playlist.get('name')
    }
    seen: set[str] = set()
    for name in data.get('playlists') or []:
        member = by_name.get(str(name))
        if not member:
            continue
        for filename in member.get('files') or []:
            file = str(filename)
            if file and file not in seen:
                seen.add(file)
                yield file


def collection_tracks(
    data: dict[str, Any],
    playlists: list[dict[str, Any]],
    tracks: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolved tracks in playlist order, deduplicated by file."""

    return [
        dict(tracks[filename])
        for filename in _members(data, playlists)
        if isinstance(tracks.get(filename), dict)
    ]


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def collection_analysis(
    data: dict[str, Any],
    playlists: list[dict[str, Any]],
    tracks: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    files = list(_members(data, playlists))
    found = [
        tracks[file] for file in files if isinstance(tracks.get(file), dict)
    ]
    missing = len(files) - len(found)
    total = len(files)
    return {
        'tracks': len(found),
        'duration_seconds': sum(
            _number(track.get('duration')) for track in found
        ),
        'bytes': int(sum(_number(track.get('size')) for track in found)),
        'missing_tracks': missing,
        'missing_ratio': missing / total if total else 0.0,
    }
