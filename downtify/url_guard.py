"""Fetch guards for URLs that arrive in a request payload.

A client (or a compromised session) can point these at the host itself, the
Docker network or a cloud metadata service, so anything fetched from such a
URL must resolve to public addresses only.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit


def is_public_http_url(url: str) -> bool:
    """True when *url* is http(s) and every address it resolves to is global.

    shortcut: httpx re-resolves DNS after this check, so a rebinding host can
    still win the race; pin the transport if that ever matters.
    """
    try:
        parsed = urlsplit(url)
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    except ValueError:
        return False
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
        return False
    try:
        infos = socket.getaddrinfo(parsed.hostname, port)
    except OSError:
        return False
    for info in infos:
        try:
            if not ipaddress.ip_address(info[4][0]).is_global:
                return False
        except ValueError:
            return False
    return True
