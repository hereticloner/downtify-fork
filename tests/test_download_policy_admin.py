from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from downtify import admin_access


@pytest.mark.parametrize(
    ('kind', 'role'),
    [('signed', 'admin'), ('ticket', 'admin'), ('session', 'user')],
)
def test_admin_door_rejects_non_admin(monkeypatch, kind, role):
    principal = SimpleNamespace(
        kind=kind, is_admin=(role == 'admin'), user_id=1
    )
    monkeypatch.setattr(
        admin_access.api, 'principal_of', lambda _request: principal
    )
    with pytest.raises(HTTPException) as error:
        admin_access.admin_user(Mock())
    assert error.value.status_code == 403


@pytest.mark.parametrize('kind', ['session', 'device', 'open'])
def test_valid_admins_can_mutate(monkeypatch, kind):
    principal = SimpleNamespace(kind=kind, is_admin=True, user_id=1)
    monkeypatch.setattr(
        admin_access.api, 'principal_of', lambda _request: principal
    )
    assert admin_access.admin_user(Mock()) == 1
