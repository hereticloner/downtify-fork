"""Machine-readable error codes for the HTTP API.

User-facing failures are raised as :class:`ApiError`, which carries a
stable, lower-case, dot-separated ``code`` next to the human-readable
``detail`` (kept in English for API clients and logs). ``main.py``'s
exception handler serialises it as ``{"detail": ..., "code": ...}``, and
the web UI translates ``code`` (``frontend/src/lib/errors.js``) instead of
showing the English text.

The translations live in ``frontend/src/i18n/locales/*.js`` under
``errors.*``. A plain ``HTTPException`` still gets a code from
:data:`STATUS_CODES` by its status, so every error the UI can hit is
translatable even when the raise site predates this module.
"""

from __future__ import annotations

from fastapi import HTTPException

# Fallback code per HTTP status, for errors raised without an explicit one.
STATUS_CODES: dict[int, str] = {
    400: 'request.invalid',
    401: 'auth.signin_required',
    403: 'auth.forbidden',
    404: 'resource.not_found',
    409: 'request.conflict',
    413: 'request.too_large',
    422: 'request.invalid',
    429: 'auth.rate_limited',
    500: 'server.error',
    502: 'download.failed',
    503: 'server.starting',
}


class ApiError(HTTPException):
    """An HTTP error that also carries a machine-readable ``code``."""

    def __init__(
        self,
        status_code: int,
        code: str,
        detail: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            status_code=status_code, detail=detail, headers=headers
        )
        self.code = code


def code_for(exc: HTTPException) -> str:
    """The code to serialise for *exc*: its own, else one from the status."""

    code = getattr(exc, 'code', None)
    if isinstance(code, str) and code:
        return code
    return STATUS_CODES.get(exc.status_code, 'server.error')
