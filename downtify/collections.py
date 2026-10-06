"""Collections: named groups of library playlists.

Minimal storage: one JSON file per collection under
``Playlists/.collections/``. No sqlite, no migration; the folder rides
every existing backup/sync of the downloads volume. Deletion of a
collection never touches the playlists or audio it groups.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import m3u
from .manual_playlists import ManualPlaylistError

COLLECTIONS_DIR = '.collections'
FORMAT_VERSION = 1


def _dir(download_dir: Path) -> Path:
    return Path(download_dir) / 'Playlists' / COLLECTIONS_DIR


def _safe_name(raw: str) -> str:
    return m3u.sanitize_playlist_name(raw)


def _path(download_dir: Path, name: str) -> Path:
    return _dir(download_dir) / f'{_safe_name(name)}.json'


def _read(download_dir: Path, path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise CollectionError(f'Broken collection file {path.name}') from exc
    return {
        'version': int(data.get('version') or FORMAT_VERSION),
        'name': str(data.get('name') or path.stem),
        'playlists': [str(p) for p in data.get('playlists') or []],
    }


def _write(download_dir: Path, data: dict[str, Any]) -> None:
    path = _path(download_dir, data['name'])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8'
    )


def _err(message: str, *, status_code: int = 400) -> CollectionError:
    return CollectionError(message, status_code=status_code)


class CollectionError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def create_collection(download_dir: Path, name: str) -> dict[str, Any]:
    safe = _safe_name(str(name or '').strip())
    if not safe:
        raise _err('Enter a collection name')
    path = _path(download_dir, safe)
    if path.exists():
        raise _err(
            f'A collection named {safe!r} already exists', status_code=409
        )
    data = {'version': FORMAT_VERSION, 'name': safe, 'playlists': []}
    _write(download_dir, data)
    return data


def list_collections(download_dir: Path) -> list[dict[str, Any]]:
    base = _dir(download_dir)
    if not base.is_dir():
        return []
    out = []
    for path in sorted(base.glob('*.json')):
        try:
            out.append(_read(download_dir, path))
        except CollectionError:
            continue
    out.sort(key=lambda c: c['name'].casefold())
    return out


def _require(download_dir: Path, name: str) -> dict[str, Any]:
    path = _path(download_dir, name)
    if not path.exists():
        raise _err(f'Collection {name!r} was not found', status_code=404)
    return _read(download_dir, path)


def add_to_collection(
    download_dir: Path, name: str, playlists: list[str]
) -> dict[str, Any]:
    data = _require(download_dir, name)
    existing = set(data['playlists'])
    known = {path.stem for path in m3u.iter_m3u_files(Path(download_dir))}
    for raw in playlists or []:
        pl = _safe_name(str(raw or '').strip())
        if not pl:
            continue
        if pl not in known:
            raise _err(
                f'{pl!r} is not a playlist in the library', status_code=404
            )
        if pl not in existing:
            data['playlists'].append(pl)
            existing.add(pl)
    _write(download_dir, data)
    return data


def remove_from_collection(
    download_dir: Path, name: str, playlists: list[str]
) -> dict[str, Any]:
    data = _require(download_dir, name)
    drop = {_safe_name(str(p or '').strip()) for p in playlists or []}
    data['playlists'] = [p for p in data['playlists'] if p not in drop]
    _write(download_dir, data)
    return data


def rename_collection(
    download_dir: Path, name: str, new_name: str
) -> dict[str, Any]:
    data = _require(download_dir, name)
    safe = _safe_name(str(new_name or '').strip())
    if not safe:
        raise _err('Enter a collection name')
    old_path = _path(download_dir, name)
    new_path = _path(download_dir, safe)
    if new_path.exists() and new_path.resolve() != old_path.resolve():
        raise _err(
            f'A collection named {safe!r} already exists', status_code=409
        )
    try:
        old_path.unlink(missing_ok=True)
    except OSError as exc:
        raise _err(f'Could not remove {old_path.name}') from exc
    data['name'] = safe
    _write(download_dir, data)
    return data


def delete_collection(download_dir: Path, name: str) -> dict[str, Any]:
    data = _require(download_dir, name)
    path = _path(download_dir, name)
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        raise _err(f'Could not remove {path.name}') from exc
    return {'ok': True, 'collection': data['name']}


# Re-export for API-layer parity with manual_playlists' error type.
PlaylistEditError = ManualPlaylistError
