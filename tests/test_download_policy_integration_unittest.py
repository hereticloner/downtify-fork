import sqlite3
import unittest
from unittest.mock import Mock

import pytest

from downtify.download_policy import DownloadPolicy, DownloadPolicyBlocked
from downtify.downloader import Downloader


class DownloadIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.policy = DownloadPolicy(lambda: self.conn)
        self.song = {
            'song_id': 'track-123',
            'name': 'Song',
            'artist': 'Artist',
            'album_name': 'Album',
            'duration': 120,
        }
        self.downloader = Downloader.__new__(Downloader)
        # The fork's download() checks the trash first; there is no trash
        # store configured here, so getattr default applies.
        self.downloader.download_policy = self.policy
        self.downloader.download_policy_limit = lambda: 60
        self.downloader._download_inner = Mock(return_value='song.flac')

    def tearDown(self):
        self.conn.close()

    def test_manual_block_prevents_source_fetch_and_is_reversible(self):
        ident = self.policy.suppress(self.song, user_id=1)['id']
        with pytest.raises(DownloadPolicyBlocked):
            self.downloader.download(self.song)
        self.downloader._download_inner.assert_not_called()
        self.policy.resume(ident)
        assert self.downloader.download(self.song) == 'song.flac'

    def test_suppression_during_attempt_stops_publication_before_return(self):
        def download(song, progress, subdir, check):
            self.policy.suppress(song, user_id=1)
            check(force=True)
            self.fail('must not proceed after suppression')

        self.downloader._download_inner.side_effect = download
        with pytest.raises(DownloadPolicyBlocked):
            self.downloader.download(self.song)
        assert self.policy.blocked(self.song)


if __name__ == '__main__':
    unittest.main()
