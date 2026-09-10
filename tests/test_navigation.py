import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock


class SearchNavigationTests(unittest.TestCase):
    def setUp(self):
        self.original_argv = sys.argv[:]
        self.original_modules = {name: sys.modules.get(name) for name in
                                 ('xbmc', 'xbmcaddon', 'xbmcgui', 'xbmcplugin', 'xbmcvfs')}

        xbmc = types.ModuleType('xbmc')
        xbmc.executebuiltin = MagicMock()
        xbmc.getCondVisibility = MagicMock(return_value=True)
        xbmc.LOGERROR = 4
        xbmc.PLAYLIST_VIDEO = 1
        self.playlist = MagicMock()
        self.player = MagicMock()
        xbmc.PlayList = MagicMock(return_value=self.playlist)
        xbmc.Player = MagicMock(return_value=self.player)

        xbmcaddon = types.ModuleType('xbmcaddon')
        addon_settings = MagicMock()
        addon_settings.getAddonInfo.return_value = '/tmp/plugin.video.nzonscreen/'
        addon_settings.getSetting.return_value = 'false'
        xbmcaddon.Addon = MagicMock(return_value=addon_settings)
        self.addon_settings = addon_settings

        xbmcgui = types.ModuleType('xbmcgui')
        xbmcgui.INPUT_ALPHANUM = 0
        xbmcgui.NOTIFICATION_INFO = 1
        dialog = MagicMock()
        dialog.input.return_value = 'Howard Morrison'
        self.dialog = dialog
        xbmcgui.Dialog = MagicMock(return_value=dialog)
        xbmcgui.ListItem = MagicMock()
        xbmcgui.Window = MagicMock()

        xbmcplugin = types.ModuleType('xbmcplugin')
        xbmcplugin.addDirectoryItem = MagicMock()
        xbmcplugin.endOfDirectory = MagicMock()
        xbmcplugin.setContent = MagicMock()
        xbmcplugin.setPluginCategory = MagicMock()
        xbmcplugin.setResolvedUrl = MagicMock()

        xbmcvfs = types.ModuleType('xbmcvfs')
        xbmcvfs.translatePath = lambda path: path

        sys.modules.update({'xbmc': xbmc, 'xbmcaddon': xbmcaddon,
                            'xbmcgui': xbmcgui, 'xbmcplugin': xbmcplugin,
                            'xbmcvfs': xbmcvfs})
        sys.argv = ['plugin://plugin.video.nzonscreen', '7', '']
        sys.modules.pop('resources.lib.addon', None)
        self.addon = importlib.import_module('resources.lib.addon')
        self.xbmc = xbmc

    def tearDown(self):
        sys.argv = self.original_argv
        sys.modules.pop('resources.lib.addon', None)
        for name, module in self.original_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def test_search_renders_results_without_container_redirect(self):
        self.addon.show_search = MagicMock()
        self.addon.search_dialog()

        self.addon.show_search.assert_called_once_with('Howard Morrison', 1)
        self.xbmc.executebuiltin.assert_not_called()

    def test_catalogue_folders_use_paginated_search_api(self):
        self.addon.root()

        urls = [call.args[1] for call in sys.modules['xbmcplugin'].addDirectoryItem.call_args_list]
        self.assertIn(
            'plugin://plugin.video.nzonscreen?category=Series&sort=-last_published_at&action=results',
            urls,
        )
        self.assertIn(
            'plugin://plugin.video.nzonscreen?category=Music+video&sort=-last_published_at&action=results',
            urls,
        )
        self.assertIn(
            'plugin://plugin.video.nzonscreen?category=Profile&sort=title&action=results',
            urls,
        )

    def test_current_search_media_type_enables_watchlist_action(self):
        self.addon.search_result_to_item({
            'id': 39644,
            'title': 'Scared Old Men',
            'html_url': 'https://www.nzonscreen.com/all-music-videos/scared-old-men-2025/',
            'media_type_category': 'Music video',
        })

        list_item = sys.modules['xbmcgui'].ListItem.return_value
        context = list_item.addContextMenuItems.call_args.args[0]
        self.assertEqual(context[0][0], 'Add to NZ On Screen watchlist')
        self.assertIn('item_type=Music+video', context[0][1])

    def test_search_pagination_preserves_query_and_filters(self):
        self.addon.nzos.search = MagicMock(return_value={
            'results': [],
            'pagination': {'page_number': 1, 'page_size': 20, 'total_count': 41},
        })

        self.addon.show_search('Howard', 1, 'Television', '49', '1980', '-last_published_at')

        url = sys.modules['xbmcplugin'].addDirectoryItem.call_args.args[1]
        self.assertIn('query=Howard', url)
        self.assertIn('page=2', url)
        self.assertIn('category=Television', url)
        self.assertIn('genre=49', url)
        self.assertIn('decade=1980', url)
        self.assertIn('sort=-last_published_at', url)

    def test_login_can_save_password_when_user_explicitly_agrees(self):
        self.dialog.input.side_effect = ['viewer@example.com', 'secret']
        self.dialog.yesno.return_value = True
        self.addon.nzos.login = MagicMock()

        self.addon.login_dialog()

        self.addon.nzos.login.assert_called_once_with('viewer@example.com', 'secret')
        self.addon_settings.setSetting.assert_any_call('save_password', 'true')
        self.addon_settings.setSetting.assert_any_call('account_email', 'viewer@example.com')
        self.addon_settings.setSetting.assert_any_call('account_password', 'secret')

    def test_login_clears_password_when_user_does_not_save(self):
        self.dialog.input.side_effect = ['viewer@example.com', 'secret']
        self.dialog.yesno.return_value = False
        self.addon.nzos.login = MagicMock()

        self.addon.login_dialog()

        self.addon_settings.setSetting.assert_any_call('save_password', 'false')
        self.addon_settings.setSetting.assert_any_call('account_email', '')
        self.addon_settings.setSetting.assert_any_call('account_password', '')

    def test_play_all_queues_every_clip_in_order(self):
        videos = [
            {'video_id': '101', 'label': 'Part one'},
            {'video_id': '102', 'label': 'Part two'},
            {'video_id': '199', 'label': 'Credits'},
        ]

        self.addon.play_all(videos)

        self.playlist.clear.assert_called_once_with()
        queued = [call.args[0] for call in self.playlist.add.call_args_list]
        self.assertEqual(queued, [
            'plugin://plugin.video.nzonscreen?video_id=101&clip_label=Part+one&action=play',
            'plugin://plugin.video.nzonscreen?video_id=102&clip_label=Part+two&action=play',
            'plugin://plugin.video.nzonscreen?video_id=199&clip_label=Credits&action=play',
        ])
        self.player.play.assert_called_once_with(self.playlist)

    def test_multi_clip_page_offers_play_all_first(self):
        videos = [
            {'video_id': '101', 'label': 'Part one'},
            {'video_id': '102', 'label': 'Part two'},
        ]
        self.addon.nzos.page_links = MagicMock(return_value={
            'title': 'Programme', 'videos': videos, 'links': []})
        self.dialog.select.return_value = 0
        self.addon.play_page('/videos/programme/')

        self.dialog.select.assert_called_once_with(
            'Programme', ['Play all parts', 'Part one', 'Part two'])
        self.xbmc.executebuiltin.assert_called_once_with(
            'RunPlugin(plugin://plugin.video.nzonscreen?'
            'path=%2Fvideos%2Fprogramme%2F&action=playall)')

    def test_playback_uses_stable_representation_to_avoid_audio_resync(self):
        self.addon.nzos.playback = MagicMock(return_value={
            'manifest': 'https://media.example/video.mpd',
            'license': 'https://license.example/widevine',
            'title': 'Programme', 'plot': '', 'poster': '',
            'duration': 60, 'subtitles': [],
        })
        self.addon.nzos.watching_progress = MagicMock(return_value={})

        self.addon.play('101')

        list_item = sys.modules['xbmcgui'].ListItem.return_value
        list_item.setProperty.assert_any_call(
            'inputstream.adaptive.stream_selection_type', 'fixed-res')


if __name__ == '__main__':
    unittest.main()
