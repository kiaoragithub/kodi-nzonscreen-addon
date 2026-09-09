import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock


class SearchNavigationTests(unittest.TestCase):
    def setUp(self):
        self.original_argv = sys.argv[:]
        self.original_modules = {name: sys.modules.get(name) for name in
                                 ('xbmc', 'xbmcaddon', 'xbmcgui', 'xbmcplugin')}

        xbmc = types.ModuleType('xbmc')
        xbmc.executebuiltin = MagicMock()
        xbmc.LOGERROR = 4
        xbmc.PLAYLIST_VIDEO = 1
        self.playlist = MagicMock()
        self.player = MagicMock()
        xbmc.PlayList = MagicMock(return_value=self.playlist)
        xbmc.Player = MagicMock(return_value=self.player)

        xbmcaddon = types.ModuleType('xbmcaddon')
        xbmcaddon.Addon = MagicMock(return_value=object())

        xbmcgui = types.ModuleType('xbmcgui')
        xbmcgui.INPUT_ALPHANUM = 0
        dialog = MagicMock()
        dialog.input.return_value = 'Howard Morrison'
        self.dialog = dialog
        xbmcgui.Dialog = MagicMock(return_value=dialog)
        xbmcgui.ListItem = MagicMock()

        xbmcplugin = types.ModuleType('xbmcplugin')
        xbmcplugin.endOfDirectory = MagicMock()

        sys.modules.update({'xbmc': xbmc, 'xbmcaddon': xbmcaddon,
                            'xbmcgui': xbmcgui, 'xbmcplugin': xbmcplugin})
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

    def test_search_uses_persistent_results_container(self):
        self.addon.search_dialog()

        self.xbmc.executebuiltin.assert_called_once_with(
            'Container.Update(plugin://plugin.video.nzonscreen?'
            'query=Howard+Morrison&action=results,replace)')

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
        self.addon.play_all = MagicMock()

        self.addon.play_page('/videos/programme/')

        self.dialog.select.assert_called_once_with(
            'Programme', ['Play all parts', 'Part one', 'Part two'])
        self.addon.play_all.assert_called_once_with(videos)


if __name__ == '__main__':
    unittest.main()
