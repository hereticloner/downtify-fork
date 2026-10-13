"""Tests for the HTML-to-text helper (downtify/_html_utils.py)."""

from __future__ import annotations

from downtify._html_utils import strip_html


def test_strip_html_drops_tags_and_keeps_paragraph_breaks():
    assert strip_html('<p>Hello <b>world</b></p><p>Second</p>') == (
        'Hello world\n\nSecond'
    )


def test_strip_html_unescapes_entities_without_any_tags():
    assert strip_html('Rock &amp; Roll') == 'Rock & Roll'


def test_strip_html_of_empty_text_is_empty():
    assert not strip_html('')


def test_strip_html_survives_malformed_markup():
    # An unclosed tag shouldn't raise; a plain fallback is fine.
    assert 'broken' in strip_html('<p>broken<b>markup')


def test_strip_html_keeps_list_items_on_their_own_lines():
    assert strip_html('<ul><li>One</li><li>Two</li></ul>') == 'One\n\nTwo'
