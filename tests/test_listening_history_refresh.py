"""Tests for the one-shot listening-history catch-up run at startup.

Both provider ``run_once`` calls are faked, so nothing here touches the
network. The assertions are about invocation, token redaction and error
isolation.
"""

from __future__ import annotations

import asyncio
import json

from downtify import listening_history


class _Listening:
    def __init__(self) -> None:
        self.calls = 0

    def reconcile_lastfm_sources(self) -> int:
        self.calls += 1
        return 3


def _spotify(**overrides):
    summary = {
        'enabled': True,
        'fetched': 1,
        'saved': 1,
        'error': '',
        'tokens': {},
    }
    summary.update(overrides)
    return summary


def _lastfm(**overrides):
    summary = {
        'enabled': True,
        'fetched': 2,
        'saved': 2,
        'linked': 2,
        'pages': 1,
        'error': '',
    }
    summary.update(overrides)
    return summary


def test_catch_up_runs_both_providers_and_reconciles(monkeypatch):
    seen = {'spotify': [], 'lastfm': []}

    def fake_spotify(settings, db_path, **kwargs):
        seen['spotify'].append((settings, db_path, kwargs))
        return _spotify()

    def fake_lastfm(settings, db_path, **kwargs):
        seen['lastfm'].append((settings, db_path, kwargs))
        return _lastfm()

    monkeypatch.setattr(
        listening_history.spotify_history, 'run_once', fake_spotify
    )
    monkeypatch.setattr(
        listening_history.lastfm_history, 'run_once', fake_lastfm
    )
    listening = _Listening()
    settings = {'spotify_mirror': {}}
    result = asyncio.run(
        listening_history.catch_up_listening_history(
            settings, 'activity.db', listening, user_id=7
        )
    )

    assert len(seen['spotify']) == 1
    assert len(seen['lastfm']) == 1
    assert seen['spotify'][0][0] is settings
    assert seen['spotify'][0][1] == 'activity.db'
    assert seen['spotify'][0][2]['user_id'] == 7
    assert seen['lastfm'][0][2]['user_id'] == 7
    assert seen['lastfm'][0][2]['max_pages'] == 1
    assert seen['spotify'][0][2]['listening'] is listening
    assert seen['lastfm'][0][2]['listening'] is listening
    assert 'tokens' not in result['spotify']
    assert result['spotify']['saved'] == 1
    assert result['lastfm']['saved'] == 2
    assert result['reconciled'] == 3
    assert listening.calls == 1


def test_catch_up_persists_spotify_token_renewal_without_returning_it(
    monkeypatch,
):
    tokens = {
        'access_token': 'access-xyz',
        'refresh_token': 'refresh-xyz',
        'token_expires_at': 12345,
    }
    persisted = []

    def fake_spotify(settings, db_path, **kwargs):
        return _spotify(tokens=dict(tokens))

    def fake_lastfm(settings, db_path, **kwargs):
        return _lastfm()

    monkeypatch.setattr(
        listening_history.spotify_history, 'run_once', fake_spotify
    )
    monkeypatch.setattr(
        listening_history.lastfm_history, 'run_once', fake_lastfm
    )
    result = asyncio.run(
        listening_history.catch_up_listening_history(
            {},
            'activity.db',
            _Listening(),
            user_id=1,
            persist_tokens=persisted.append,
        )
    )

    assert persisted == [tokens]
    blob = json.dumps(result)
    assert 'access-xyz' not in blob
    assert 'refresh-xyz' not in blob
    assert 'tokens' not in blob


def test_catch_up_isolates_provider_failure(monkeypatch):
    def fake_spotify(settings, db_path, **kwargs):
        raise RuntimeError('token access-xyz broke')

    def fake_lastfm(settings, db_path, **kwargs):
        return _lastfm()

    monkeypatch.setattr(
        listening_history.spotify_history, 'run_once', fake_spotify
    )
    monkeypatch.setattr(
        listening_history.lastfm_history, 'run_once', fake_lastfm
    )
    result = asyncio.run(
        listening_history.catch_up_listening_history(
            {}, 'activity.db', _Listening(), user_id=1
        )
    )

    assert result['spotify'] == {'error': 'RuntimeError'}
    assert result['lastfm']['saved'] == 2
    assert result['reconciled'] == 3
    assert 'access-xyz' not in json.dumps(result)
