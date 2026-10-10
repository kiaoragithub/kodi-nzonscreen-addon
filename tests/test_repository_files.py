import hashlib
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.1.4'
ADDON_ID = 'plugin.video.nzonscreen'
DIRECT = ROOT / ('NZ-On-Screen-Kodi-%s.zip' % VERSION)
REPO = ROOT / ('docs/zips/%s/%s-%s.zip' % (ADDON_ID, ADDON_ID, VERSION))


class RepositoryPackageTests(unittest.TestCase):
    def test_xml_versions_and_metadata_match(self):
        source = ET.parse(ROOT / 'addon.xml').getroot()
        repository = ET.parse(ROOT / 'docs/addons.xml').getroot().find("addon[@id='%s']" % ADDON_ID)
        self.assertEqual(source.get('version'), VERSION)
        self.assertEqual(repository.get('version'), VERSION)
        for element in list(source.iter()) + list(repository.iter()):
            element.text = (element.text or '').strip() or None
            element.tail = None
        self.assertEqual(ET.tostring(source), ET.tostring(repository))
        metadata = source.find("extension[@point='xbmc.addon.metadata']")
        self.assertEqual(metadata.findtext('source'), 'https://github.com/kiaoragithub/kodi-nzonscreen-addon')
        self.assertTrue(metadata.findtext('disclaimer'))

    def test_source_mirrors_and_api_version(self):
        self.assertEqual((ROOT / 'addon.xml').read_bytes(), (ROOT / ADDON_ID / 'addon.xml').read_bytes())
        parser = (ROOT / 'resources/lib/nzos.py').read_bytes()
        self.assertEqual(parser, (ROOT / ADDON_ID / 'resources/lib/nzos.py').read_bytes())
        self.assertIn(('NZOnScreen-Addon/' + VERSION).encode(), parser)
        self.assertIn(("'appVersion': '%s'" % VERSION).encode(), parser)

    def test_duplicate_zip_equality_and_complete_source_contents(self):
        self.assertEqual(DIRECT.read_bytes(), REPO.read_bytes())
        with zipfile.ZipFile(DIRECT) as archive:
            self.assertIsNone(archive.testzip())
            names = archive.namelist()
            self.assertEqual(len(names), len(set(names)))
            self.assertTrue(all(name.startswith(ADDON_ID + '/') for name in names))
            self.assertFalse(any('__pycache__' in name or name.endswith(('.pyc', '.pyo')) for name in names))
            self.assertFalse(any('/tests/' in name or '/.git/' in name or 'session.cookies' in name for name in names))
            for name in names:
                if not name.endswith('/'):
                    path = ROOT / name[len(ADDON_ID) + 1:]
                    self.assertEqual(archive.read(name), path.read_bytes(), name)
            for name in ('addon.py', 'addon.xml', 'service.py', 'README.md', 'CHANGELOG.md', 'LICENSE.txt',
                         'resources/lib/addon.py', 'resources/lib/nzos.py', 'resources/settings.xml'):
                self.assertIn(ADDON_ID + '/' + name, names)
            self.assertEqual(ET.fromstring(archive.read(ADDON_ID + '/addon.xml')).get('version'), VERSION)

    def test_all_published_md5_checksums_match(self):
        for checksum in (ROOT / 'docs').rglob('*.md5'):
            with self.subTest(file=checksum.relative_to(ROOT).as_posix()):
                self.assertEqual(checksum.read_text().strip(), hashlib.md5(checksum.with_suffix('').read_bytes()).hexdigest())

    def test_repository_installer_copies_and_urls(self):
        copies = [ROOT / 'docs/repository.nzonscreen-1.0.1.zip',
                  ROOT / 'docs/zips/repository.nzonscreen/repository.nzonscreen-1.0.1.zip']
        self.assertEqual(copies[0].read_bytes(), copies[1].read_bytes())
        with zipfile.ZipFile(copies[0]) as archive:
            self.assertIsNone(archive.testzip())
            manifest = ET.fromstring(archive.read('repository.nzonscreen/addon.xml'))
            directory = manifest.find("extension[@point='xbmc.addon.repository']/dir")
            self.assertEqual(directory.findtext('info'), 'https://kiaoragithub.github.io/kodi-nzonscreen-addon/addons.xml')
            self.assertEqual(directory.findtext('checksum'), 'https://kiaoragithub.github.io/kodi-nzonscreen-addon/addons.xml.md5')
            self.assertEqual(directory.findtext('datadir'), 'https://kiaoragithub.github.io/kodi-nzonscreen-addon/zips/')

    def test_artwork_is_png_and_matches_package(self):
        with zipfile.ZipFile(DIRECT) as archive:
            for name in ('icon.png', 'fanart.png'):
                source = (ROOT / 'resources' / name).read_bytes()
                self.assertTrue(source.startswith(b'\x89PNG\r\n\x1a\n'))
                self.assertEqual(archive.read(ADDON_ID + '/resources/' + name), source)
                self.assertEqual((ROOT / 'docs/zips' / ADDON_ID / name).read_bytes(), source)

    def test_documentation_and_directory_index_reference_latest_release(self):
        self.assertIn('NZ-On-Screen-Kodi-%s.zip' % VERSION, (ROOT / 'README.md').read_text())
        self.assertTrue((ROOT / 'CHANGELOG.md').read_text().startswith('# Changelog\n\n## %s —' % VERSION))
        index = (ROOT / 'docs/zips' / ADDON_ID / 'index.html').read_text()
        self.assertIn('%s-%s.zip' % (ADDON_ID, VERSION), index)
        self.assertIn('issues', (ROOT / 'README.md').read_text())

    def test_settings_use_kodi21_schema_and_mask_password(self):
        root = ET.parse(ROOT / 'resources/settings.xml').getroot()
        self.assertEqual(root.get('version'), '1')
        group = root.find('section/category/group')
        self.assertIsNotNone(group)
        save = group.find("setting[@id='save_password']")
        self.assertEqual(save.findtext('default'), 'false')
        self.assertEqual(save.find('control').get('type'), 'toggle')
        password = group.find("setting[@id='account_password']")
        self.assertEqual(password.findtext('control/hidden'), 'true')
        self.assertEqual(password.findtext('dependencies/dependency'), 'true')
        for setting in group.findall('setting'):
            self.assertIsNotNone(setting.find('default'))
            self.assertIsNotNone(setting.find('control'))


if __name__ == '__main__': unittest.main()
