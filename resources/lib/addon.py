import os
import sys
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

from . import nzos

HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]
ADDON = xbmcaddon.Addon()
SESSION_FILE = os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo('profile')), 'session.cookies')

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
    item('My NZ On Screen account', plugin_url('account'), True)
    item('Browse by category, genre or decade', plugin_url('filters'), True)
    for label, path in ROOT:
        item(label, plugin_url('page', path=path), True)
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def account_menu():
    try:
        user = nzos.current_user()
    except Exception:
        item('Sign in', plugin_url('login'), False)
        item('Create account on nzonscreen.com',
             plugin_url('website', url='https://www.nzonscreen.com/signup/'), False)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    name = user.get('display_name') or user.get('name') or user.get('email') or 'Signed in'
    item('Signed in as ' + str(name), '', False)
    item('My watchlist', plugin_url('watchlist'), True)
    item('NZOS+ rentals and catalogue', plugin_url('page', path='/nzos/'), True)
    item('Transaction history on nzonscreen.com',
         plugin_url('website', url='https://www.nzonscreen.com/account/'), False)
    item('Sign out', plugin_url('logout'), False)
    xbmcplugin.endOfDirectory(HANDLE)


def login_dialog():
    save_password = ADDON.getSetting('save_password') == 'true'
    saved_email = ADDON.getSetting('account_email') if save_password else ''
    saved_password = ADDON.getSetting('account_password') if save_password else ''
    email = xbmcgui.Dialog().input('NZ On Screen email', defaultt=saved_email,
                                   type=xbmcgui.INPUT_ALPHANUM)
    if not email:
        return
    hide = getattr(xbmcgui, 'ALPHANUM_HIDE_INPUT', 0)
    password = xbmcgui.Dialog().input('NZ On Screen password', defaultt=saved_password,
                                      type=xbmcgui.INPUT_ALPHANUM, option=hide)
    if not password:
        return
    nzos.login(email.strip(), password)
    keep = xbmcgui.Dialog().yesno(
        'Save NZ On Screen password?',
        'Saving makes future sign-ins easier, but stores the password locally on this Kodi device.')
    ADDON.setSetting('save_password', 'true' if keep else 'false')
    ADDON.setSetting('account_email', email.strip() if keep else '')
    ADDON.setSetting('account_password', password if keep else '')
    xbmcgui.Dialog().notification('NZ On Screen', 'Signed in', xbmcgui.NOTIFICATION_INFO, 4000)
    xbmc.executebuiltin('Container.Refresh')


def logout_account():
    nzos.logout()
    xbmcgui.Dialog().notification('NZ On Screen', 'Signed out', xbmcgui.NOTIFICATION_INFO, 4000)
    xbmc.executebuiltin('Container.Refresh')


def _account_result(entry):
    if not isinstance(entry, dict):
        return None
    nested = entry.get('item') or entry.get('content') or entry.get('page') or entry
    if not isinstance(nested, dict):
        nested = entry
    result = dict(nested)
    result.setdefault('title', entry.get('title') or entry.get('displayName') or entry.get('name'))
    result.setdefault('html_url', entry.get('html_url') or entry.get('url') or entry.get('path'))
    result.setdefault('image', entry.get('image') or entry.get('thumbnail'))
    return result


def show_watchlist():
    data = nzos.my_list()
    entries = data.get('items') if isinstance(data, dict) else data
    for entry in entries or []:
        result = _account_result(entry)
        if result:
            result['_watchlist_id'] = entry.get('itemId') or result.get('itemId')
            search_result_to_item(result)
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def change_my_list(item_id, item_type='', remove=False):
    if remove:
        nzos.remove_from_my_list(item_id)
        message = 'Removed from watchlist'
    else:
        nzos.add_to_my_list(item_id, item_type)
        message = 'Added to watchlist'
    xbmcgui.Dialog().notification('NZ On Screen', message, xbmcgui.NOTIFICATION_INFO, 3500)
    xbmc.executebuiltin('Container.Refresh')


def website_notice(url):
    xbmcgui.Dialog().ok('Continue on NZ On Screen',
                        'For security, complete this account or payment action in a browser:\n' + url)


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
    context = None
    item_id = result.get('id') or result.get('itemId')
    item_type = result.get('content_type') or result.get('itemType') or result.get('type')
    watchlist_id = result.get('_watchlist_id')
    if watchlist_id:
        context = [('Remove from NZ On Screen watchlist',
                    'RunPlugin(%s)' % plugin_url('removewatchlist', item_id=watchlist_id))]
    elif item_id and item_type:
        context = [('Add to NZ On Screen watchlist',
                    'RunPlugin(%s)' % plugin_url('addwatchlist', item_id=item_id,
                                                  item_type=item_type))]
    item(label, plugin_url(action, path=path), action == 'page', action == 'playpage', image,
         context=context)


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
    try:
        progress = nzos.watching_progress(video_id)
        position = int(progress.get('position') or 0)
        if position > 0 and position < media['duration'] - 10:
            tag.setResumePoint(position, media['duration'])
            li.setProperty('StartOffset', str(position))
    except Exception:
        pass
    window = xbmcgui.Window(10000)
    window.setProperty('NZOS.VideoId', str(video_id))
    window.setProperty('NZOS.SessionId', media.get('session_id', ''))
    if media['subtitles']:
        li.setSubtitles(media['subtitles'])
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def run():
    nzos.configure_session(SESSION_FILE)
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:] if len(sys.argv) > 2 else ''))
    action = params.get('action', 'root')
    try:
        if action == 'root': root()
        elif action == 'account': account_menu()
        elif action == 'login': login_dialog()
        elif action == 'logout': logout_account()
        elif action == 'watchlist': show_watchlist()
        elif action == 'addwatchlist': change_my_list(params['item_id'], params.get('item_type', ''))
        elif action == 'removewatchlist': change_my_list(params['item_id'], remove=True)
        elif action == 'website': website_notice(params['url'])
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
