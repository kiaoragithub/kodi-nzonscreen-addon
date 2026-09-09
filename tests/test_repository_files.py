import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0.6'


def require(condition, message):
    if not condition:
        raise AssertionError(message)


for filename in ('addon.xml', 'docs/addons.xml', 'resources/settings.xml'):
    ET.parse(ROOT / filename)

top_zip = ROOT / ('NZ-On-Screen-Kodi-%s.zip' % VERSION)
repo_zip = ROOT / ('docs/zips/plugin.video.nzonscreen/plugin.video.nzonscreen-%s.zip' % VERSION)
require(top_zip.read_bytes() == repo_zip.read_bytes(), 'Published installation ZIP copies differ')

with zipfile.ZipFile(top_zip) as archive:
    require(archive.testzip() is None, 'Installation ZIP is corrupt')
    names = archive.namelist()
    require(not any('__pycache__' in name or name.endswith('.pyc') for name in names),
            'Installation ZIP contains generated Python cache files')
    manifest = archive.read('plugin.video.nzonscreen/addon.xml').decode('utf-8')
    require('version="%s"' % VERSION in manifest, 'Installation ZIP version is incorrect')

for checksum_name in (
        'docs/addons.xml.md5',
        'docs/zips/plugin.video.nzonscreen/plugin.video.nzonscreen-%s.zip.md5' % VERSION):
    checksum = ROOT / checksum_name
    target = checksum.with_suffix('')
    require(checksum.read_text().strip() == hashlib.md5(target.read_bytes()).hexdigest(),
            '%s does not match %s' % (checksum, target))

print('Repository package validation passed')
