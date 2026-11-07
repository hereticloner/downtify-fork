"""Download-policy exceptions.

The full policy (download exclusions + attempt budgets, upstream
PR #511) arrives in W6 task 06. The music trash (PR #512) only needs
:class:`DownloadPolicyBlocked` to signal "this song must not be
(down)loaded", e.g. a trashed track stays out until an admin restores
it. Kept deliberately tiny until the policy port lands.
"""

from __future__ import annotations


class DownloadPolicyBlocked(Exception):
    """A download is blocked by policy (trash, exclusion, budget).

    ``reason`` is the machine-readable code, e.g.
    ``'library_trash_excluded'``.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
