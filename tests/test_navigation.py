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

        xbmcaddon = types.ModuleType('xbmcaddon')
        xbmcaddon.Addon = MagicMock(return_value=object())

        xbmcgui = types.ModuleType('xbmcgui')
        xbmcgui.INPUT_ALPHANUM = 0
        dialog = MagicMock()
        dialog.input.return_value = 'Howard Morrison'
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


if __name__ == '__main__':
    unittest.main()
