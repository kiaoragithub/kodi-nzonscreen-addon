"""Reproducibly rebuild the current release without modifying archived packages."""
import hashlib
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build():
    manifest_path = ROOT / 'addon.xml'
    manifest = ET.parse(manifest_path).getroot()
    version = manifest.attrib['version']
    addon_id = manifest.attrib['id']
    repo_manifest_path = ROOT / 'docs/addons.xml'
    repo_tree = ET.parse(repo_manifest_path)
    old_addon = repo_tree.getroot().find("addon[@id='%s']" % addon_id)
    repo_tree.getroot().remove(old_addon)
    repo_tree.getroot().insert(0, manifest)
    ET.indent(repo_tree, space='  ')
    repo_tree.write(repo_manifest_path, encoding='UTF-8', xml_declaration=True)
    with repo_manifest_path.open('ab') as stream:
        stream.write(b'\n')
    (ROOT / addon_id / 'addon.xml').write_bytes(manifest_path.read_bytes())
    (ROOT / addon_id / 'resources/lib/nzos.py').write_bytes((ROOT / 'resources/lib/nzos.py').read_bytes())
    paths = [ROOT / name for name in ('LICENSE.txt', 'README.md', 'CHANGELOG.md', 'addon.py', 'addon.xml', 'service.py')]
    paths += [p for p in (ROOT / 'resources').rglob('*') if p.is_file() and
              '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')]
    target = ROOT / ('NZ-On-Screen-Kodi-%s.zip' % version)
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(paths):
            info = zipfile.ZipInfo(addon_id + '/' + path.relative_to(ROOT).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    repo_zip = ROOT / ('docs/zips/%s/%s-%s.zip' % (addon_id, addon_id, version))
    shutil.copyfile(target, repo_zip)
    for path in (repo_manifest_path, repo_zip):
        Path(str(path) + '.md5').write_text(hashlib.md5(path.read_bytes()).hexdigest() + '\n')
    # The original directory index linked only 1.0.1 even after later releases.
    zips = sorted(repo_zip.parent.glob('*.zip'), key=lambda p: [int(n) for n in p.stem.rsplit('-', 1)[1].split('.')], reverse=True)
    links = '\n'.join('<a href="%s">%s</a><br>' % (p.name, p.name) for p in zips)
    (repo_zip.parent / 'index.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>NZ On Screen releases</title></head>\n<body>' + links + '</body></html>\n')
    print('Built NZ On Screen %s (%s bytes)' % (version, target.stat().st_size))


if __name__ == '__main__':
    build()
