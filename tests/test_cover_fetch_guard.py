"""URLs that arrive in a request payload must not reach the host itself, the
Docker network or a cloud metadata service (``downtify.url_guard``).
Offline: no hostname here needs DNS."""

from __future__ import annotations

from downtify.url_guard import is_public_http_url


def test_loopback_and_metadata_addresses_are_refused():
    assert not is_public_http_url('http://127.0.0.1/')
    assert not is_public_http_url('http://169.254.169.254/latest/meta-data/')
    assert not is_public_http_url('http://172.17.0.1:18901/state')
    assert not is_public_http_url('http://localhost:8000/')
    assert not is_public_http_url('http://[::1]/')


def test_non_http_and_hostless_urls_are_refused():
    assert not is_public_http_url('file:///etc/passwd')
    assert not is_public_http_url('')
    assert not is_public_http_url('https:///nohost.jpg')
    assert not is_public_http_url('https://example.com:notaport/x.jpg')


def test_public_address_is_allowed():
    assert is_public_http_url('https://93.184.216.34/cover.jpg')
