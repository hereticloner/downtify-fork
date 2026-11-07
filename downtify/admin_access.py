"""Who may reach administrator-only features.

One door for both the browser and paired apps: an administrator is an
administrator whatever key opened it; a signed URL or a WebSocket
ticket is neither.
"""

from __future__ import annotations

from fastapi import Request

from . import api

#: Who may: a signed-in browser, a paired app, or anyone while sign-in
#: is off (``DOWNTIFY_DISABLE_AUTH``: the request acts as the first
#: admin). Never a signed URL or a WebSocket ticket.
_KINDS = {'session', 'device', 'open'}


def admin_user(request: Request) -> int:
    principal = api.principal_of(request)
    if (
        principal is None
        or principal.kind not in _KINDS
        or not principal.is_admin
        or not principal.user_id
    ):
        raise api.ApiError(
            403, 'auth.admin_required', 'Administrator access required'
        )
    return principal.user_id
