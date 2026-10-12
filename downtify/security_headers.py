"""Baseline security headers on every response.

The app is served from this origin (and through ``tailscale serve``), so the
headers here are the ones that cannot change how the SPA renders: no
``default-src`` CSP yet, which would need the bundle, inline style
attributes and ``blob:`` media checked in a browser first.

Every header is added only when the response does not already carry it, so
a route can override any of them.
"""

from __future__ import annotations

from typing import Any

HEADERS: tuple[tuple[str, str], ...] = (
    # A mis-sniffed media or JSON response must not be treated as script.
    ('X-Content-Type-Options', 'nosniff'),
    # Nothing embeds this app; ``frame-ancestors`` is the modern half of it.
    ('X-Frame-Options', 'DENY'),
    ('Content-Security-Policy', "frame-ancestors 'none'"),
    # Signed stream URLs must not leak into a third party's referrer.
    ('Referrer-Policy', 'strict-origin-when-cross-origin'),
)


class SecurityHeadersMiddleware:
    """Add :data:`HEADERS` to every HTTP response."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: dict) -> None:
            if message['type'] == 'http.response.start':
                headers: list[tuple[bytes, bytes]] = message.setdefault(
                    'headers', []
                )
                present = {name.lower() for name, _ in headers}
                for header, value in HEADERS:
                    name = header.lower().encode()
                    if name not in present:
                        headers.append((name, value.encode()))
            await send(message)

        await self.app(scope, receive, send_with_headers)
