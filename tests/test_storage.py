"""Tests for the storage report and duplicate cleanup (downtify.storage).

The filesystem is faked: a fake context returns canned entries, so the
assertions are about grouping, the keep/duplicate choice and the delete
contract — not about real files.
"""

from __future__ import annotations

from downtify import storage
from downtify.auth import classify


class FakeCtx:
    """A library context with a download dir and no real files."""

    def __init__(self, entries=None, download_dir='/downloads') -> None:
        self.download_dir = download_dir
        self._entries = entries or []

    def entries(self):
        return self._entries


def _entry(file, artist='A', title='T', album='Al', size=100, bitrate=320, added=0):  # noqa: PLR0913, PLR0917
    return {
        'file': file,
        'artist': artist,
        'title': title,
        'album': album,
        'size': size,
        'bitrate': bitrate,
        'added': added,
    }


# ── disk usage ───────────────────────────────────────────────────────


def test_disk_usage_shape(monkeypatch):
    class Usage:
        total = 1000
        used = 250
        free = 750

    monkeypatch.setattr(storage.shutil, 'disk_usage', lambda p: Usage())
    usage = storage.disk_usage(storage.Path('/x'))
    assert usage == {
        'total': 1000,
        'used': 250,
        'free': 750,
        'percent': 25.0,
    }


def test_disk_usage_zero_on_error(monkeypatch):
    def boom(p):
        raise OSError('no disk')

    monkeypatch.setattr(storage.shutil, 'disk_usage', boom)
    assert storage.disk_usage(storage.Path('/x')) == {
        'total': 0,
        'used': 0,
        'free': 0,
        'percent': 0,
    }


# ── library size ─────────────────────────────────────────────────────


def test_library_size_sums_entries(monkeypatch):
    entries = [
        _entry('a.mp3', size=100),
        _entry('b.mp3', size=200),
        _entry('c.mp3', size=0),
    ]
    monkeypatch.setattr(storage, 'list_library_entries', lambda ctx: entries)
    size = storage.library_size(FakeCtx())
    assert size == {'bytes': 300, 'tracks': 3}


# ── duplicates ───────────────────────────────────────────────────────


def test_find_duplicates_groups_same_song(monkeypatch):
    entries = [
        _entry('a.mp3', size=100, added=1),
        _entry('b.mp3', size=200, added=2),
        _entry('c.mp3', size=50, added=3),
    ]
    monkeypatch.setattr(storage, 'list_library_entries', lambda ctx: entries)
    groups = storage.find_duplicates(FakeCtx())
    assert len(groups) == 1
    group = groups[0]
    assert group['artist'] == 'A'
    assert group['title'] == 'T'
    # Largest file is kept.
    assert group['keep'] == {'file': 'b.mp3', 'size': 200}
    assert group['duplicates'] == [
        {'file': 'a.mp3', 'size': 100},
        {'file': 'c.mp3', 'size': 50},
    ]
    assert group['wasted_bytes'] == 150


def test_find_duplicates_skips_single_copies(monkeypatch):
    entries = [
        _entry('a.mp3', artist='A', title='T'),
        _entry('b.mp3', artist='B', title='U'),
    ]
    monkeypatch.setattr(storage, 'list_library_entries', lambda ctx: entries)
    assert storage.find_duplicates(FakeCtx()) == []


def test_find_duplicates_skips_unnamed(monkeypatch):
    entries = [
        _entry('a.mp3', artist='', title='T'),
        _entry('b.mp3', artist='A', title=''),
    ]
    monkeypatch.setattr(storage, 'list_library_entries', lambda ctx: entries)
    assert storage.find_duplicates(FakeCtx()) == []


def test_find_duplicates_sorts_by_wasted_bytes(monkeypatch):
    entries = [
        _entry('a.mp3', artist='A', title='T', size=10),
        _entry('b.mp3', artist='A', title='T', size=10),
        _entry('c.mp3', artist='B', title='U', size=500),
        _entry('d.mp3', artist='B', title='U', size=500),
    ]
    monkeypatch.setattr(storage, 'list_library_entries', lambda ctx: entries)
    groups = storage.find_duplicates(FakeCtx())
    assert [g['artist'] for g in groups] == ['B', 'A']


# ── delete ───────────────────────────────────────────────────────────


def test_delete_files_removes_and_drops_cache(monkeypatch, tmp_path):
    removed: list[str] = []
    dropped: list[bool] = []

    class Ctx:
        download_dir = str(tmp_path)

    def fake_resolve(name, ctx):
        path = tmp_path / name
        path.write_bytes(b'x')
        return path

    monkeypatch.setattr(storage, 'resolve_library_file', fake_resolve)
    monkeypatch.setattr(
        storage.Path,
        'unlink',
        lambda self: removed.append(self.name),
    )
    monkeypatch.setattr(
        storage,
        'drop_library_listing_files',
        lambda ctx: dropped.append(True),
    )
    result = storage.delete_files(Ctx(), ['a.mp3', 'b.mp3'])
    assert result == {'removed': 2}
    assert removed == ['a.mp3', 'b.mp3']
    assert dropped == [True]


def test_delete_files_skips_missing(monkeypatch, tmp_path):
    class Ctx:
        download_dir = str(tmp_path)

    monkeypatch.setattr(
        storage,
        'resolve_library_file',
        lambda name, ctx: None,
    )
    result = storage.delete_files(Ctx(), ['a.mp3'])
    assert result == {'removed': 0}


# ── settings plumbing (no new settings block, but routes classified) ─


def test_storage_routes_classified():
    assert classify('GET', '/api/storage/report') is not None
    assert classify('GET', '/api/storage/duplicates') is not None
    assert classify('POST', '/api/storage/duplicates/delete') is not None
