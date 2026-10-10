"""Offline, reduced public page data observed on 2026-10-10; no tokens/cookies."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from resources.lib import nzos


CASES = json.loads((Path(__file__).parent / 'fixtures/live_page_shapes.json').read_text())


def hydration(data, split=False):
    query = {'queryKey': [{'url': '/api/v3/pages/find/'}], 'state': {'data': data}}
    payload = '7:' + json.dumps({'queries': [query]}, ensure_ascii=False) + '\n'
    chunks = [payload[:len(payload)//2], payload[len(payload)//2:]] if split else [payload]
    return ''.join('<script>self.__next_f.push(%s)</script>' % json.dumps([1, chunk]) for chunk in chunks)


class LiveStructureTests(unittest.TestCase):
    def test_all_observed_page_shapes_keep_exact_video_ids_and_labels(self):
        for case in CASES:
            with self.subTest(path=case['path']):
                actual = nzos.extract_videos(hydration(case['data'], True), case['path'])
                self.assertEqual([(x['video_id'], x['label']) for x in actual],
                                 [(x['video_id'], x['label']) for x in case['expected_videos']])
                self.assertEqual(len(actual), len({x['video_id'] for x in actual}))

    def test_season_folder_recovers_only_its_seven_episodes(self):
        pages = {case['path']: hydration(case['data']) for case in CASES}
        path = '/all-series/k-road-chronicles/season-4/'
        with patch.object(nzos, 'get_page', side_effect=lambda p: (pages[p], p)), \
                patch.object(nzos, 'get_html', side_effect=pages.__getitem__):
            result = nzos.page_links(path)
        self.assertEqual(len(result['links']), 7)
        self.assertEqual(result['videos'], [])
        self.assertTrue(all(link['url'].startswith(path) for link in result['links']))
        self.assertIn('Episode 01', result['links'][0]['label'])
        self.assertIn('Episode 07', result['links'][-1]['label'])

    def test_series_provides_season_folders_without_embedded_episode_playback(self):
        case = next(x for x in CASES if x['path'] == '/all-series/k-road-chronicles/')
        with patch.object(nzos, 'get_page', return_value=(hydration(case['data']), case['path'])):
            result = nzos.page_links(case['path'])
        self.assertEqual(result['videos'], [])
        self.assertEqual([x['label'] for x in result['links'][:4]],
                         ['Season 01', 'Season 02', 'Season 03', 'Season 04'])

    def test_redirected_parent_is_used_for_validation(self):
        case = next(x for x in CASES if x['path'] == '/videos/patu-1983/')
        with patch.object(nzos, 'get_page', return_value=(hydration(case['data']), case['path'])):
            result = nzos.page_links('/title/patu-1983')
        self.assertEqual(result['videos'][0]['video_id'], '6392424229112')

    def test_rental_and_trailer_are_distinct(self):
        case = next(x for x in CASES if x['path'] == '/videos/marama-2025/')
        videos = nzos.extract_videos(hydration(case['data']), case['path'])
        self.assertTrue(videos[0]['is_rental'])
        self.assertNotIn('is_rental', videos[1])
        self.assertEqual(videos[1]['video_id'], '6393473255112')

    def test_duplicate_and_foreign_parent_reject_without_fallback(self):
        source = '{"name":"Wrong","navigation":{"navigation_type":"video","video_id":123},' \
                 '"parent_page":{"html_url":"https://www.nzonscreen.com/videos/other/"},' \
                 '"videoId":"123","accountId":"456"}'
        self.assertEqual(nzos.extract_videos(source, '/videos/expected/'), [])
        video = {'name': 'Correct', 'navigation': {'navigation_type': 'video', 'video_id': 123},
                 'parent_page': {'html_url': 'https://www.nzonscreen.com/videos/expected/'}}
        self.assertEqual(len(nzos._structured_videos({'content': [video, video]}, '/videos/expected/')), 1)

    def test_parent_must_be_on_nzos_and_match_page(self):
        for parent in ('https://evil.example/videos/expected/', '/videos/other/'):
            with self.subTest(parent=parent):
                obj = {'name': 'Incorrect', 'navigation': {'navigation_type': 'video', 'video_id': 123},
                       'parent_page': {'html_url': parent}}
                self.assertEqual(nzos._structured_videos(obj, '/videos/expected/'), [])

    def test_natural_episode_prefix_and_ordinal_orders(self):
        for labels in (['Episode 10', 'Episode 2', 'Episode 1', 'Credits'],
                       ['10: Finale', '02: Middle', '01: Start', 'Credits'],
                       ['The third of six parts', 'The second of 6 parts', 'The first of six parts', 'Credits']):
            with self.subTest(labels=labels):
                videos = [{'video_id': str(i), 'label': label} for i, label in enumerate(labels)]
                self.assertEqual([x['video_id'] for x in nzos._order_videos(videos)], ['2', '1', '0', '3'])

    def test_link_parser_void_elements_and_footer_are_not_folders(self):
        source = '<main><div><img src="poster.jpg"><br><a href="/videos/a/">A</a></div>' \
                 '<a href="/videos/b/">B<img src="b.jpg"/></a><footer>' \
                 '<a href="/search/">Search</a></footer></main><a href="/contact/">Contact</a>'
        parser = nzos.LinkParser(); parser.feed(source)
        self.assertEqual([x['url'] for x in parser.links], ['/videos/a/', '/videos/b/'])

    def test_fragments_and_non_web_schemes_are_rejected(self):
        for url in ('#', '#main', 'javascript:alert(1)', 'file:///videos/a',
                    'https://www.nzonscreen.com.evil.example/videos/a/', 'https://evil.example/'):
            with self.subTest(url=url): self.assertEqual(nzos.clean_url(url), '')
        self.assertEqual(nzos.clean_url('https://www.nzonscreen.com/videos/a/'), '/videos/a/')

    def test_pages_do_not_expose_empty_modal_folders_or_fake_images(self):
        source = '<title>Example | NZ On Screen</title><main>' \
                 '<a href="/m/more-info/videos/example/">More info</a>' \
                 '<a href="/videos/other/">Other</a><a href="#main">Jump</a></main>'
        with patch.object(nzos, 'get_page', return_value=(source, '/videos/example/')):
            result = nzos.page_links('/videos/example/')
        self.assertEqual(len(result['links']), 1)
        self.assertEqual(result['links'][0]['image'], '')


if __name__ == '__main__': unittest.main()
