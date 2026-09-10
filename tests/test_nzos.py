import unittest

from resources.lib.nzos import extract_videos


class ExtractVideosTests(unittest.TestCase):
    def test_current_navigation_format_without_account_id(self):
        source = r'''{"name":"Part one.","navigation":{"navigation_type":"video","html_url":"/m/player/one","video_id":6394657312112}}'''

        self.assertEqual(
            extract_videos(source),
            [{'video_id': '6394657312112', 'label': 'Part one.'}],
        )

    def test_multiple_clips_keep_their_own_labels(self):
        source = r'''{"name":"Part one.","navigation":{"navigation_type":"video","video_id":111},"parent_page":{"name":"Programme"}},{"name":"Part two.","navigation":{"navigation_type":"video","video_id":222}}'''

        self.assertEqual(
            extract_videos(source),
            [
                {'video_id': '111', 'label': 'Part one.'},
                {'video_id': '222', 'label': 'Part two.'},
            ],
        )

    def test_single_hero_video_uses_page_navigation(self):
        source = r'''{"hero_video":{"name":"A full length feature film.","navigation":{"navigation_type":"page","video_id":6394663447112},"video_id":"6394663447112","account_id":"6416036801001"}}'''

        self.assertEqual(
            extract_videos(source),
            [{'video_id': '6394663447112', 'label': 'A full length feature film.'}],
        )

    def test_foreign_parent_page_video_is_rejected(self):
        source = r'''{"name":"Correct clip","video_type":"","navigation":{"navigation_type":"video","video_id":111},"parent_page":{"html_url":"https://www.nzonscreen.com/videos/correct/"}},{"name":"Recommended clip","video_type":"","navigation":{"navigation_type":"video","video_id":222},"parent_page":{"html_url":"https://www.nzonscreen.com/videos/other/"}}'''

        self.assertEqual(
            extract_videos(source, '/videos/correct/'),
            [{'video_id': '111', 'label': 'Correct clip'}],
        )

    def test_child_page_navigation_video_is_not_played_from_series_folder(self):
        source = r'''{"title":"Episode one","media_type_category":"Television","navigation":{"navigation_type":"page","html_url":"https://www.nzonscreen.com/all-series/example/episode-one/","video_id":444}}'''

        self.assertEqual(extract_videos(source, '/all-series/example/'), [])

    def test_same_page_navigation_video_is_kept(self):
        source = r'''{"name":"Full episode","video_type":"full","navigation":{"navigation_type":"page","html_url":"https://www.nzonscreen.com/videos/example/","video_id":555}}'''

        self.assertEqual(
            extract_videos(source, '/videos/example/'),
            [{'video_id': '555', 'label': 'Full episode'}],
        )

    def test_quoted_clip_name_is_decoded(self):
        source = r'''{"name":"The trailer for \\\"The Convert\\\"","video_type":"trailer","navigation":{"navigation_type":"page","video_id":333}}'''

        self.assertEqual(
            extract_videos(source),
            [{'video_id': '333', 'label': 'The trailer for "The Convert"'}],
        )

    def test_parts_are_naturally_ordered_and_credits_are_last(self):
        source = r'''{"name":"Part three","video_type":"","navigation":{"navigation_type":"video","video_id":3}},{"name":"Credits","video_type":"","navigation":{"navigation_type":"video","video_id":9}},{"name":"Part one","video_type":"","navigation":{"navigation_type":"video","video_id":1}},{"name":"Part two","video_type":"","navigation":{"navigation_type":"video","video_id":2}}'''

        self.assertEqual(
            [video['video_id'] for video in extract_videos(source)],
            ['1', '2', '3', '9'],
        )


if __name__ == '__main__':
    unittest.main()
