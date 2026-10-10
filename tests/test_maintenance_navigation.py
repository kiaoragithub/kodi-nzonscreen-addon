import importlib
import sys
import unittest
import urllib.parse
from unittest.mock import MagicMock, patch
import test_navigation as navigation_tests


class MaintenanceNavigationTests(unittest.TestCase):
    setUp = navigation_tests.SearchNavigationTests.setUp
    tearDown = navigation_tests.SearchNavigationTests.tearDown

    def urls(self):
        return [c.args[1] for c in sys.modules['xbmcplugin'].addDirectoryItem.call_args_list]

    def test_season_is_folder_and_deep_episode_is_playable(self):
        self.assertEqual(self.addon.classify('/all-series/k-road-chronicles/season-4/'), 'page')
        self.assertEqual(self.addon.classify('/all-series/k-road-chronicles/season-4/episode/'), 'playpage')
        self.assertEqual(self.addon.classify('/interviews/funny-as/', 'InterviewLandingPage'), 'page')
        self.assertEqual(self.addon.classify('/interviews/individual/', 'InterviewPage'), 'playpage')

    def test_nested_search_enters_keyboard_and_filter_urls_preserve_values(self):
        self.assertEqual(self.addon.link_route('/search/'), ('search', {}))
        action, params = self.addon.link_route('/search/?s=M%C4%81ori+%26+music&genres=39&genres=49&decades=1980&media_category=Film')
        self.assertEqual(action, 'results')
        self.assertEqual(params['query'], 'Māori & music')
        self.assertEqual(params['genre'], '39,49')
        self.assertEqual(params['category'], 'Film')
        self.assertEqual(params['decade'], '1980')

    def test_show_page_search_link_is_search_action(self):
        self.addon.nzos.page_links = MagicMock(return_value={'title': 'Nested', 'videos': [],
                                      'links': [{'url': '/search/', 'label': 'Search', 'image': ''}]})
        self.addon.show_page('/collection/example/')
        self.assertIn('plugin://plugin.video.nzonscreen?action=search', self.urls())

    def test_empty_search_does_not_reopen_keyboard(self):
        self.dialog.input.return_value = ''
        self.addon.search_dialog()
        sys.modules['xbmcplugin'].endOfDirectory.assert_called_once_with(7, succeeded=False)

    def test_multiple_filters_and_last_page(self):
        self.addon.nzos.search = MagicMock(return_value={'results': [], 'pagination': {'total_count': 40, 'page_size': 20}})
        self.addon.show_search('Māori', 2, 'Film,Television', '39,49', '1980,1990')
        self.addon.nzos.search.assert_called_once_with('Māori', 2, ['39', '49'], ['1980', '1990'], ['Film', 'Television'], '')
        self.assertEqual(self.urls(), [])

    def test_empty_results_do_not_divide_by_zero(self):
        self.addon.nzos.search = MagicMock(return_value={'results': [], 'pagination': {'total_count': 0, 'page_size': 0}})
        self.addon.show_search('no results')
        self.assertEqual(self.urls(), [])

    def test_folder_multipart_also_offers_play_all(self):
        videos = [{'video_id': '1', 'label': 'Part one'}, {'video_id': '2', 'label': 'Part two'}]
        self.addon.nzos.page_links = MagicMock(return_value={'title': 'Programme', 'videos': videos, 'links': []})
        self.addon.show_page('/videos/programme/')
        self.assertIn('action=playall', self.urls()[0])
        self.assertTrue(all('page_title=Programme' in url for url in self.urls()[1:]))

    def test_cancel_clips_completes_resolver(self):
        self.addon.nzos.page_links = MagicMock(return_value={'title': 'Programme', 'links': [],
                                     'videos': [{'video_id': '1', 'label': 'A'}, {'video_id': '2', 'label': 'B'}]})
        self.dialog.select.return_value = -1
        self.addon.play_page('/videos/programme/')
        self.assertFalse(sys.modules['xbmcplugin'].setResolvedUrl.call_args.args[1])
        self.xbmc.executebuiltin.assert_not_called()

    def test_single_and_selected_clip_receive_page_title(self):
        self.addon.play = MagicMock()
        self.addon.nzos.page_links = MagicMock(return_value={'title': 'Human title', 'links': [],
                                                            'videos': [{'video_id': '1', 'label': 'Trailer'}]})
        self.addon.play_page('/videos/title/')
        self.addon.play.assert_called_once_with('1', 'Trailer', 'Human title')
        self.addon.play.reset_mock()
        self.addon.nzos.page_links.return_value['videos'].append({'video_id': '2', 'label': 'Excerpt'})
        self.dialog.select.return_value = 2
        self.addon.play_page('/videos/title/')
        self.addon.play.assert_called_once_with('2', 'Excerpt', 'Human title')

    def test_page_title_replaces_technical_provider_filename(self):
        self.addon.nzos.playback = MagicMock(return_value={'manifest': 'https://example.test/a.mpd', 'license': 'https://example.test/wv',
                   'title': 'Technical_1080_H264_Filename', 'plot': '', 'poster': '', 'duration': 120, 'subtitles': []})
        self.addon.nzos.watching_progress = MagicMock(return_value={})
        self.addon.play('1', 'Trailer', 'Black Sheeps')
        tag = sys.modules['xbmcgui'].ListItem.return_value.getVideoInfoTag.return_value
        tag.setTitle.assert_called_once_with('Black Sheeps — Trailer')

    def test_declining_inputstream_install_completes_resolver(self):
        self.xbmc.getCondVisibility.return_value = False
        self.dialog.yesno.return_value = False
        self.addon.nzos.playback = MagicMock()
        self.addon.play('1')
        self.addon.nzos.playback.assert_not_called()
        self.assertFalse(sys.modules['xbmcplugin'].setResolvedUrl.call_args.args[1])

    def test_resume_and_caption_properties_are_set(self):
        self.addon.nzos.playback = MagicMock(return_value={'manifest': 'https://example.test/a.mpd', 'license': 'https://example.test/wv',
                  'title': 'Title', 'plot': '', 'poster': '', 'duration': 120, 'subtitles': ['https://example.test/en.vtt'], 'session_id': 'session'})
        self.addon.nzos.watching_progress = MagicMock(return_value={'position': 40})
        self.addon.play('1')
        li = sys.modules['xbmcgui'].ListItem.return_value
        li.setProperty.assert_any_call('StartOffset', '40')
        li.setProperty.assert_any_call('inputstream.adaptive.license_type', 'com.widevine.alpha')
        li.setProperty.assert_any_call('inputstream.adaptive.license_key', 'https://example.test/wv')
        li.setSubtitles.assert_called_once_with(['https://example.test/en.vtt'])
        sys.modules['xbmcgui'].Window.return_value.setProperty.assert_any_call('NZOS.Manifest', 'https://example.test/a.mpd')

    def test_interview_group_uses_paginated_api(self):
        self.addon.nzos.page_links = MagicMock(return_value={'title': 'Funny As', 'videos': [], 'links': [],
                                                              'page_type': 'InterviewLandingPage', 'page_id': 22738})
        self.addon.nzos.interview_search = MagicMock(return_value={'results': [], 'pagination': {'page_size': 20, 'total_count': 100}})
        self.addon.show_page('/interviews/funny-as/')
        self.addon.nzos.interview_search.assert_called_once_with('22738', 1)
        self.assertIn('kind=interview', self.urls()[0])
        self.assertIn('page=2', self.urls()[0])

    def test_account_link_is_current_and_logout_clears_saved_credentials(self):
        self.addon.nzos.current_user = MagicMock(return_value={'name': 'Test account'})
        self.addon.account_menu()
        self.assertTrue(any('settings' in url for url in self.urls()))
        self.assertFalse(any('%2Faccount%2F' in url for url in self.urls()))
        self.addon.nzos.logout = MagicMock()
        self.addon.logout_account()
        self.addon_settings.setSetting.assert_any_call('account_password', '')
        self.addon_settings.setSetting.assert_any_call('save_password', 'false')

    def test_account_network_failure_does_not_claim_signed_out(self):
        self.addon.nzos.current_user = MagicMock(side_effect=self.addon.nzos.NZOSError('Network error'))
        with self.assertRaises(self.addon.nzos.NZOSError): self.addon.account_menu()
        self.assertEqual(self.urls(), [])

    def test_saved_password_no_clears_previous_saved_secret_on_next_invocation(self):
        self.addon.nzos.configure_session = MagicMock()
        self.addon.root = MagicMock()
        self.addon.run()
        self.addon_settings.setSetting.assert_any_call('account_password', '')
        self.addon_settings.setSetting.assert_any_call('account_email', '')

    def test_new_filter_folders_use_live_values(self):
        self.addon.nzos.collection_filters = MagicMock(return_value={'themes': [{'id': 5, 'display_name': 'History'}]})
        self.addon.show_special_filters('collection')
        self.assertIn('kind=collection&value=5', self.urls()[0])
        sys.modules['xbmcplugin'].addDirectoryItem.reset_mock()
        self.addon.nzos.profile_filters = MagicMock(return_value={'categories': [{'value': '4', 'label': 'Director'}]})
        self.addon.show_special_filters('profile')
        self.assertIn('kind=profile&value=4', self.urls()[0])


class ProgressServiceTests(unittest.TestCase):
    setUp = navigation_tests.SearchNavigationTests.setUp
    tearDown = navigation_tests.SearchNavigationTests.tearDown

    def tracker(self):
        sys.modules['xbmc'].LOGWARNING = 3
        sys.modules['xbmc'].log = MagicMock()
        sys.modules.pop('service', None)
        service = importlib.import_module('service')
        self.addCleanup(lambda: sys.modules.pop('service', None))
        self.properties = {'NZOS.VideoId': '1', 'NZOS.SessionId': 's1', 'NZOS.Manifest': 'https://example.test/1.mpd'}
        window = MagicMock()
        window.getProperty.side_effect = lambda key: self.properties.get(key, '')
        window.clearProperty.side_effect = lambda key: self.properties.pop(key, None)
        player = MagicMock()
        player.isPlayingVideo.return_value = True
        player.getPlayingFile.return_value = self.properties['NZOS.Manifest']
        player.getTime.return_value = 37
        self.addon.nzos.update_watching_progress = MagicMock()
        return service.ProgressTracker(window), player

    def test_stopped_playback_flushes_cached_position(self):
        tracker, player = self.tracker()
        tracker.tick(player, 100)
        player.isPlayingVideo.return_value = False
        player.getTime.side_effect = RuntimeError('Playback has stopped')
        tracker.tick(player, 101)
        self.addon.nzos.update_watching_progress.assert_called_with('1', 37, 's1')
        self.assertNotIn('NZOS.VideoId', self.properties)

    def test_other_addon_never_receives_nzos_progress(self):
        tracker, player = self.tracker()
        player.getPlayingFile.return_value = 'https://other.example/video.mp4'
        tracker.tick(player, 100)
        self.addon.nzos.update_watching_progress.assert_not_called()

    def test_playlist_transition_keeps_new_session(self):
        tracker, player = self.tracker(); tracker.tick(player, 100)
        self.properties.update({'NZOS.VideoId': '2', 'NZOS.SessionId': 's2', 'NZOS.Manifest': 'https://example.test/2.mpd'})
        player.getPlayingFile.return_value = self.properties['NZOS.Manifest']; player.getTime.return_value = 5
        tracker.tick(player, 120)
        self.addon.nzos.update_watching_progress.assert_any_call('1', 37, 's1')
        self.addon.nzos.update_watching_progress.assert_any_call('2', 5, 's2')
        self.assertEqual(self.properties['NZOS.VideoId'], '2')

    def test_progress_rate_is_fifteen_seconds(self):
        tracker, player = self.tracker()
        tracker.tick(player, 100); tracker.tick(player, 110)
        self.assertEqual(self.addon.nzos.update_watching_progress.call_count, 1)
        tracker.tick(player, 115)
        self.assertEqual(self.addon.nzos.update_watching_progress.call_count, 2)


if __name__ == '__main__': unittest.main()
