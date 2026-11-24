from __future__ import annotations

import pytest
from fastapi import HTTPException

from downtify import api


def test_artist_watch_accepts_an_exact_name_match(monkeypatch):
    monkeypatch.setattr(
        api.providers,
        'search_artists',
        lambda name, limit=10: [
            {'name': 'Other Artist', 'artist_id': 'UC-other'},
            {'name': 'Cher', 'artist_id': 'UC-cher'},
        ],
    )

    assert api._youtube_artist_for_name('Cher') == ('UC-cher', 'Cher')


def test_artist_watch_refuses_an_ambiguous_name_match(monkeypatch):
    monkeypatch.setattr(
        api.providers,
        'search_artists',
        lambda name, limit=10: [
            {'name': 'Cher Similar', 'artist_id': 'UC-similar'},
        ],
    )

    with pytest.raises(HTTPException) as exc:
        api._youtube_artist_for_name('Cher')

    assert exc.value.status_code == 409
