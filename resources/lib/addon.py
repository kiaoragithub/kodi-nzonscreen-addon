import sys
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from . import nzos

HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]
ADDON = xbmcaddon.Addon()

ROOT = [
    ('Featured & latest', '/'),
    ('Television in NZ', '/television-in-nz/'),
    ('Film in NZ', '/film-in-nz/'),
    ('Series', '/all-series/'),
    ('Music videos', '/all-music-videos/'),
    ('Collections', '/collection/'),
    ('Interviews', '/interviews/screentalk/'),
    ('Profiles', '/profile/'),
    ('NZOS+', '/nzos/'),
]


def plugin_url(action, **kwargs):
    kwargs['action'] = action
    return BASE_URL + '?' + urllib.parse.urlencode(kwargs)


def item(label, url, folder=True, playable=False, art=None, info=None, context=None):
    li = xbmcgui.ListItem(label=label)
    if art:
        li.setArt({'thumb': art, 'poster': art, 'icon': art})
    if info:
        tag = li.getVideoInfoTag()
        if info.get('plot'): tag.setPlot(info['plot'])
        if info.get('title'): tag.setTitle(info['title'])
        if info.get('duration'): tag.setDuration(info['duration'])
    if playable:
        li.setProperty('IsPlayable', 'true')
    if context:
        li.addContextMenuItems(context)
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=folder)


def root():
    item('Search', plugin_url('search'), True)
    item('Browse by category, genre or decade', plugin_url('filters'), True)
    for label, path in ROOT:
        item(label, plugin_url('page', path=path), True)
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def classify(path):
    bits = [x for x in urllib.parse.urlsplit(path).path.split('/') if x]
    if not bits: return 'page'
    if bits[0] == 'videos': return 'playpage'
    if bits[0] == 'all-music-videos': return 'playpage'
    if bits[0] == 'all-series' and len(bits) >= 3: return 'playpage'
    return 'page'


def show_page(path):
    data = nzos.page_links(path)
    for index, video in enumerate(data['videos']):
        label = video['label'] if len(data['videos']) > 1 else ('Play ' + (data['title'] or 'video'))
        item(label, plugin_url('play', video_id=video['video_id'], clip_label=video['label']), False, True)
    for link in data['links']:
        action = classify(link['url'])
        if action == 'playpage':
            item(link['label'], plugin_url('playpage', path=link['url']), False, True, link['image'])
        else:
            item(link['label'], plugin_url('page', path=link['url']), True, art=link['image'])
    xbmcplugin.setPluginCategory(HANDLE, data['title'])
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)


def play_page(path):
    data = nzos.page_links(path)
    if not data['videos']:
        raise nzos.NZOSError('No playable video was found on this page.')
    if len(data['videos']) == 1:
        play(data['videos'][0]['video_id'], data['videos'][0]['label'])
        return
    labels = ['Play all parts'] + [x['label'] for x in data['videos']]
    selected = xbmcgui.Dialog().select(data['title'] or 'Choose video', labels)
    if selected == 0:
        # This page was opened as a playable item, so Kodi is currently waiting
        # for setResolvedUrl(). Starting Player.play() in that resolver can crash
        # Kodi on some platforms. End the resolver and start the playlist from a
        # separate, non-resolver plugin invocation instead.
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        xbmc.executebuiltin('RunPlugin(%s)' % plugin_url('playall', path=path))
    elif selected > 0:
        video = data['videos'][selected - 1]
        play(video['video_id'], video['label'])


def play_all(videos):
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    for video in videos:
        url = plugin_url('play', video_id=video['video_id'], clip_label=video['label'])
        li = xbmcgui.ListItem(label=video['label'])
        li.setProperty('IsPlayable', 'true')
        playlist.add(url, li)
    xbmc.Player().play(playlist)


def search_dialog():
    query = xbmcgui.Dialog().input('Search NZ On Screen', type=xbmcgui.INPUT_ALPHANUM)
    if query:
        # Render into the current directory invocation. Container.Update with
        # replace returns to the add-on root on some Kodi platforms.
        show_search(query, 1)
    else:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)


def search_result_to_item(result):
    label = result.get('title') or result.get('name') or result.get('display_name') or 'Untitled'
    path = result.get('html_url') or result.get('url') or result.get('path') or ''
    image = result.get('image') or result.get('thumbnail') or result.get('hero_image') or ''
    if isinstance(image, dict):
        image = (image.get('large') or image.get('thumbnail') or {})
        if isinstance(image, dict): image = image.get('url') or image.get('src') or ''
    if image: image = urllib.parse.urljoin(nzos.BASE + '/', image)
    if not path: return
    action = classify(path)
    item(label, plugin_url(action, path=path), action == 'page', action == 'playpage', image)


def show_search(query='', page=1, category='', genre='', decade='', sort=''):
    data = nzos.search(query, page, [genre] if genre else None, [decade] if decade else None, category, sort)
    for result in data.get('results', []):
        search_result_to_item(result)
    pagination = data.get('pagination') or {}
    total = int(pagination.get('total_count') or 0)
    page_size = int(pagination.get('page_size') or 20)
    total_pages = data.get('total_pages') or data.get('pages') or ((total + page_size - 1) // page_size)
    has_next = data.get('next') or data.get('has_next') or (total_pages and page < total_pages)
    if has_next:
        item('Next page', plugin_url('results', query=query, page=page + 1, category=category,
                                     genre=genre, decade=decade, sort=sort), True)
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def show_filters():
    data = nzos.filters()
    item('All titles', plugin_url('results'), True)
    for x in data.get('categories', []):
        item('Category: ' + x.get('display_name', str(x.get('id'))),
             plugin_url('results', category=x.get('id', '')), True)
    for x in data.get('genres', []):
        item('Genre: ' + x.get('display_name', str(x.get('id'))),
             plugin_url('results', genre=x.get('id', '')), True)
    current = 10 * (2026 // 10)
    for decade in range(current, 1909, -10):
        item('Decade: %ss' % decade, plugin_url('results', decade=decade), True)
    xbmcplugin.endOfDirectory(HANDLE)


def play(video_id, clip_label=''):
    if not xbmc.getCondVisibility('System.HasAddon(inputstream.adaptive)'):
        if not xbmcgui.Dialog().yesno('InputStream Adaptive required',
                                      'NZ On Screen uses Widevine DASH. Install InputStream Adaptive now?'):
            return
        xbmc.executebuiltin('InstallAddon(inputstream.adaptive)', wait=True)
    media = nzos.playback(video_id)
    li = xbmcgui.ListItem(path=media['manifest'])
    li.setContentLookup(False)
    li.setMimeType('application/dash+xml')
    li.setProperty('inputstream', 'inputstream.adaptive')
    li.setProperty('inputstream.adaptive.manifest_type', 'mpd')
    # NZOS DASH manifests offer several video representations but a single
    # audio representation. Keeping the chosen video representation fixed
    # avoids a startup quality switch that can make Kodi briefly resync/mute
    # the audio on some Android/HDMI devices.
    li.setProperty('inputstream.adaptive.stream_selection_type', 'fixed-res')
    li.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
    li.setProperty('inputstream.adaptive.license_key', media['license'])
    li.setArt({'poster': media['poster'], 'thumb': media['poster']})
    tag = li.getVideoInfoTag()
    title = media['title']
    if clip_label and clip_label.casefold() != title.casefold():
        title = title + ' — ' + clip_label
    tag.setTitle(title)
    tag.setPlot(media['plot'])
    tag.setDuration(media['duration'])
    if media['subtitles']:
        li.setSubtitles(media['subtitles'])
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def run():
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:] if len(sys.argv) > 2 else ''))
    action = params.get('action', 'root')
    try:
        if action == 'root': root()
        elif action == 'page': show_page(params.get('path', '/'))
        elif action == 'playpage': play_page(params['path'])
        elif action == 'playall': play_all(nzos.page_links(params['path'])['videos'])
        elif action == 'play': play(params['video_id'], params.get('clip_label', ''))
        elif action == 'search': search_dialog()
        elif action == 'filters': show_filters()
        elif action == 'results':
            show_search(params.get('query', ''), int(params.get('page', 1)), params.get('category', ''),
                        params.get('genre', ''), params.get('decade', ''), params.get('sort', ''))
    except Exception as exc:
        xbmc.log('NZ On Screen error: %s' % exc, xbmc.LOGERROR)
        xbmcgui.Dialog().notification('NZ On Screen', str(exc), xbmcgui.NOTIFICATION_ERROR, 7000)
        if action != 'play': xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        else: xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
