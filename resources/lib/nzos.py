import html
import http.cookiejar
import json
import os
import re
import ssl
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

BASE = 'https://www.nzonscreen.com'
UA = 'Mozilla/5.0 (Linux; Android TV) Kodi/21 NZOnScreen-Addon/1.1.4'

_cookies = None
_opener = urllib.request.build_opener()


def configure_session(cookie_file):
    """Use a persistent website session without ever storing the password."""
    global _cookies, _opener
    _cookies = http.cookiejar.MozillaCookieJar(cookie_file)
    _reload_session()
    _opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_cookies))


def _reload_session():
    # Kodi's plugin and service are separate Python interpreters. A service
    # started before sign-in must see the new session, and must see sign-out.
    if _cookies is not None:
        _cookies.clear()
        try:
            _cookies.load(ignore_discard=True, ignore_expires=False)
        except (FileNotFoundError, http.cookiejar.LoadError, OSError):
            pass


def _cookie_state():
    return [(c.domain, c.path, c.name, c.value, c.expires) for c in _cookies] if _cookies is not None else []


def _save_session():
    if _cookies is not None:
        directory = os.path.dirname(_cookies.filename)
        if directory:
            os.makedirs(directory, exist_ok=True)
        # Create with mode 0600 before writing secrets; replace atomically so
        # another interpreter cannot read a partially written cookie jar.
        fd, temporary = tempfile.mkstemp(dir=directory or '.', prefix='.nzos-session-')
        os.close(fd)
        try:
            _cookies.save(temporary, ignore_discard=True, ignore_expires=False)
            os.replace(temporary, _cookies.filename)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


class NZOSError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def _http_error(exc):
    # Never echo raw server bodies, which can contain credentials, tokens or
    # personal account data, into Kodi logs and notifications.
    messages = {401: 'Sign in to NZ On Screen to access this title or account feature.',
                403: 'Access denied by NZ On Screen. Rental entitlement, account or regional restrictions may apply.',
                404: 'This title or NZ On Screen feature is unavailable.',
                429: 'NZ On Screen is limiting requests. Please try again later.'}
    message = messages.get(exc.code, 'Please try again later.')
    try:
        detail = json.loads(exc.read(4096).decode('utf-8'))
        entries = detail if isinstance(detail, list) else [detail]
        if any(isinstance(x, dict) and x.get('error_subcode') == 'CLIENT_GEO' for x in entries):
            message = 'This video is not available in your location.'
        elif any(isinstance(x, dict) and x.get('errorMessage') == 'User not entitled to play this asset' for x in entries):
            message = 'This rental requires a valid NZ On Screen account entitlement. Complete rental checkout on nzonscreen.com.'
    except (ValueError, UnicodeError, OSError):
        pass
    return NZOSError('NZ On Screen returned HTTP %s: %s' % (exc.code, message), exc.code)


def request(path, data=None, headers=None, timeout=25, return_url=False):
    url = path if path.startswith('http') else BASE + ('/' if not path.startswith('/') else '') + path
    body = json.dumps(data).encode('utf-8') if data is not None else None
    hdr = {'User-Agent': UA, 'Accept': 'application/json, text/html;q=0.9, */*;q=0.8'}
    if data is not None:
        hdr.update({'Content-Type': 'application/json', 'Origin': BASE, 'Referer': BASE + '/'})
    if headers:
        hdr.update(headers)
    if urllib.parse.urlsplit(url).scheme != 'https':
        raise NZOSError('Refusing an insecure NZ On Screen request.')
    _reload_session()
    cookie_state = _cookie_state()
    try:
        request_obj = urllib.request.Request(url, body, hdr)
        with _opener.open(request_obj, timeout=timeout) as response:
            result = response.read(), response.headers.get('Content-Type', '')
            final_url = response.geturl()
        if _cookie_state() != cookie_state:
            _save_session()
        return result + (final_url,) if return_url else result
    except urllib.error.HTTPError as exc:
        raise _http_error(exc) from None
    except (urllib.error.URLError, OSError) as exc:
        raise NZOSError('Could not connect to NZ On Screen. Check your connection and try again.') from None


def get_json(path, params=None):
    if params:
        path += ('&' if '?' in path else '?') + urllib.parse.urlencode(params, doseq=True)
    raw, _ = request(path)
    return json.loads(raw.decode('utf-8'))


def get_html(path):
    raw, _ = request(path)
    return raw.decode('utf-8', 'replace')


def get_page(path):
    raw, _, final_url = request(path, return_url=True)
    final_path = clean_url(final_url)
    if not final_path:
        raise NZOSError('The page redirected outside NZ On Screen.')
    return raw.decode('utf-8', 'replace'), final_path


def login(email, password):
    csrf = get_json('/api/v3/auth/csrf').get('csrf_token', '')
    raw, _ = request('/api/v3/auth/login', {'email': email, 'password': password},
                     {'X-CSRFToken': csrf} if csrf else None)
    return json.loads(raw.decode('utf-8')) if raw else {}


def logout():
    csrf = get_json('/api/v3/auth/csrf').get('csrf_token', '')
    request('/api/v3/auth/logout', {}, {'X-CSRFToken': csrf} if csrf else None)
    if _cookies is not None:
        _cookies.clear()
        _save_session()


def current_user():
    return get_json('/api/v3/user/me')


def my_list(page_size=100):
    return get_json('/api/v3/user/my-list/', {'pageSize': page_size})


def add_to_my_list(item_id, item_type):
    # Match the live website's MyListToggle normalization.
    item_type = str(item_type).replace(' ', '-').replace('_', '-').lower()
    return _account_write('/api/v3/user/my-list/', 'POST',
                          {'itemId': item_id, 'itemType': item_type})


def remove_from_my_list(item_id):
    return _account_write('/api/v3/user/my-list/' + str(item_id), 'DELETE')


def watching_progress(video_id):
    try:
        return get_json('/api/v3/user/continue-watching/' + str(video_id))
    except NZOSError as exc:
        if 'HTTP 404' in str(exc):
            return {}
        raise


def update_watching_progress(video_id, position, session_id):
    return _account_write('/api/v3/user/continue-watching/' + str(video_id), 'PUT',
                          {'position': int(position), 'sessionId': session_id})


def entitlement(video_id):
    return get_json('/api/v3/user/entitlements/' + str(video_id))


def _account_write(path, method, data=None):
    csrf = get_json('/api/v3/auth/csrf').get('csrf_token', '')
    url = BASE + path
    body = json.dumps(data).encode('utf-8') if data is not None else None
    headers = {'User-Agent': UA, 'Accept': 'application/json',
               'Content-Type': 'application/json', 'Origin': BASE, 'Referer': BASE + '/'}
    if csrf:
        headers['X-CSRFToken'] = csrf
    _reload_session()
    cookie_state = _cookie_state()
    try:
        with _opener.open(urllib.request.Request(url, body, headers, method=method), timeout=25) as response:
            raw = response.read()
        if _cookie_state() != cookie_state:
            _save_session()
        return json.loads(raw.decode('utf-8')) if raw else {}
    except urllib.error.HTTPError as exc:
        raise _http_error(exc) from None
    except (urllib.error.URLError, OSError):
        raise NZOSError('Could not connect to NZ On Screen. Check your connection and try again.') from None


class LinkParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.in_main = False
        self.stack = []
        self.current = None
        self.links = []
        self.title = ''
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'main':
            self.in_main = True
        if tag not in ('area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
                       'link', 'meta', 'param', 'source', 'track', 'wbr'):
            self.stack.append(tag)
        if tag == 'title':
            self.in_title = True
        if self.in_main and 'footer' not in self.stack and tag == 'a' and a.get('href'):
            self.current = {'url': a['href'], 'text': [], 'image': '', 'alt': ''}
        elif self.current and tag == 'img':
            self.current['image'] = a.get('src') or a.get('data-src') or self.current['image']
            self.current['alt'] = a.get('alt', '')

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        if tag == 'a' and self.current:
            text = re.sub(r'\s+', ' ', ' '.join(self.current['text'])).strip()
            self.current['label'] = text or self.current['alt']
            self.links.append(self.current)
            self.current = None
        if tag in self.stack:
            del self.stack[len(self.stack) - 1 - self.stack[::-1].index(tag):]
        if tag == 'main':
            self.in_main = False

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.current:
            self.current['text'].append(data)


def clean_url(url):
    if not url or url.startswith('#'):
        return ''
    url = urllib.parse.urljoin(BASE + '/', html.unescape(url))
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme not in ('https', 'http') or
            parsed.netloc.lower() not in ('www.nzonscreen.com', 'nzonscreen.com')):
        return ''
    return parsed.path + (('?' + parsed.query) if parsed.query else '')


SKIP = ('/login/', '/contact/', '/who-we-are/', '/how-we-work/', '/faqs/',
        '/website-disclaimer/', '/digital-media-trust-', '/nz-on-screen-nzos-ts-cs-',
        '/tv-terms-and-conditions/', '/png/', '/_next/', '/m/player/',
        '/m/more-info/', '/m/background/', '/m/images/', '/m/credits/')


def _walk_objects(value):
    if isinstance(value, dict):
        yield value
        for key, child in value.items():
            if key not in ('meta', 'parent_page'):
                yield from _walk_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_objects(child)


def _flight_objects(source):
    """Read public Next.js hydration data without executing website scripts."""
    decoder = json.JSONDecoder()
    chunks = []
    for match in re.finditer(r'self\.__next_f\.push\(', source):
        try:
            entry, _ = decoder.raw_decode(source, match.end())
            if entry[0] == 1 and isinstance(entry[1], str):
                chunks.append(entry[1])
        except (ValueError, IndexError, TypeError):
            continue
    text = ''.join(chunks)
    # Flight text records can end immediately before the next JSON record.
    for match in re.finditer(r'[0-9a-f]+:(?=[{\[])', text):
        try:
            value, _ = decoder.raw_decode(text, match.end())
        except ValueError:
            continue
        yield from _walk_objects(value)


def page_data(source, page_path=''):
    for obj in _flight_objects(source):
        key = obj.get('queryKey')
        if not isinstance(key, list) or not key or key[0] != {'url': '/api/v3/pages/find/'}:
            continue
        data = (obj.get('state') or {}).get('data')
        if not isinstance(data, dict):
            continue
        actual = clean_url((data.get('meta') or {}).get('html_url', '')).split('?')[0].rstrip('/')
        expected = clean_url(page_path).split('?')[0].rstrip('/')
        if not page_path or actual == expected:
            return data
    return None


def _structured_videos(data, page_path):
    out, seen = [], set()
    current = clean_url(page_path).split('?')[0].rstrip('/')
    for obj in _walk_objects(data):
        nav = obj.get('navigation')
        if not isinstance(nav, dict) or nav.get('navigation_type') not in ('video', 'page'):
            continue
        video_id = str(nav.get('video_id') or '')
        if not video_id.isdigit() or video_id in seen:
            continue
        urls = [obj.get('html_url'), (obj.get('parent_page') or {}).get('html_url'), nav.get('html_url')]
        if page_path and any(url and (not clean_url(url) or
                (not clean_url(url).startswith('/m/player/') and
                 clean_url(url).split('?')[0].rstrip('/') != current)) for url in urls):
            continue
        # Catalogue cards without a parent must never become folder playback.
        if page_path and not obj.get('parent_page') and not obj.get('name'):
            continue
        entry = {'video_id': video_id, 'label': html.unescape(obj.get('name') or 'Play video').strip()}
        rental = obj.get('rental') or {}
        if rental.get('is_rental'):
            entry['is_rental'] = True
        out.append(entry)
        seen.add(video_id)
    return _order_videos(out)


def _order_videos(videos):
    words = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
             'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
             'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5,
             'sixth': 6, 'seventh': 7, 'eighth': 8, 'ninth': 9, 'tenth': 10}
    def number(entry):
        label = entry['label'].lower()
        found = re.search(r'\b(?:part|episode)\s+(\d+|%s)\b' % '|'.join(words), label)
        if not found:
            found = re.search(r'\b(%s)\s+of\s+(?:\d+|%s)\s+parts?\b' %
                              ('|'.join(words), '|'.join(words)), label)
        if not found:
            found = re.match(r'(\d+)\s*:', label)
        token = found.group(1) if found else ''
        return words.get(token, int(token) if token.isdigit() else 0)
    numbers = [number(entry) for entry in videos]
    if sum(n > 0 for n in numbers) >= 2:
        return [entry for _, entry in sorted(enumerate(videos), key=lambda pair:
                (0, numbers[pair[0]]) if numbers[pair[0]] else
                ((2, pair[0]) if 'credit' in pair[1]['label'].lower() else (1, pair[0])))]
    return videos


def page_links(path):
    source, path = get_page(path)
    parser = LinkParser()
    parser.feed(source)
    data = page_data(source, path)
    cards = {}
    if data:
        for obj in _walk_objects(data):
            url = clean_url(obj.get('html_url', ''))
            if url and obj.get('title') and (obj.get('page_type') or obj.get('navigation') or obj.get('media_type_category')):
                cards[url] = obj
    found, seen = [], set()
    for link in parser.links:
        url = clean_url(link['url'])
        if not url or url in seen or url == clean_url(path) or url == '/' or any(url.startswith(x) for x in SKIP):
            continue
        label = re.sub(r'\s+', ' ', link.get('label', '')).strip(' -|')
        if not label or label.lower() in ('more info', 'see more', 'sign in', 'search rapu'):
            continue
        image = urllib.parse.urljoin(BASE + '/', html.unescape(link['image'])) if link.get('image') else ''
        card = cards.get(url, {})
        if label.lower() in ('view the page', 'view the collection') and card.get('title'):
            label = card['title']
        found.append({'label': label[:180], 'url': url, 'image': image,
                      'page_type': card.get('page_type', '')})
        seen.add(url)
    for url, card in cards.items():
        if url not in seen and url != clean_url(path) and not any(url.startswith(x) for x in SKIP):
            found.append({'label': card['title'], 'url': url, 'image': '',
                          'page_type': card.get('page_type', '')})
            seen.add(url)
    page_type = (data or {}).get('content_type', '').split('.')[-1]
    if data and data.get('has_seasons'):
        prefix = clean_url(path).split('?')[0].rstrip('/') + '/'
        seasons = []
        season_prefixes = []
        for season in (data.get('serie_tree') or {}).get('seasons', []):
            episodes = season.get('episodes') or []
            urls = [clean_url(entry.get('html_url', '')) for entry in episodes]
            if not urls or not all(url.startswith(prefix) for url in urls):
                continue
            folder = urls[0].rsplit('/', 2)[0] + '/'
            if folder != prefix and all(url.startswith(folder) for url in urls):
                seasons.append({'label': season.get('season_name') or 'Season', 'url': folder,
                                'image': '', 'page_type': 'SeasonPage'})
                season_prefixes.append(folder)
        if seasons:
            found = seasons + [link for link in found if not any(
                link['url'].startswith(prefix) for prefix in season_prefixes)]
    if page_type == 'SeasonPage':
        parent = ((data.get('meta') or {}).get('parent') or {})
        parent_url = clean_url((parent.get('meta') or parent).get('html_url', ''))
        # Current SeasonPage contains no episode list. Its public parent series
        # has the complete tree; select only children under this season's URL.
        if parent_url and parent_url.rstrip('/') != clean_url(path).rstrip('/'):
            parent_data = page_data(get_html(parent_url), parent_url)
            prefix = clean_url(path).split('?')[0].rstrip('/') + '/'
            found = []
            seen = set()
            for card in _walk_objects(parent_data):
                url = clean_url(card.get('html_url', ''))
                if url.startswith(prefix) and url != prefix and url not in seen and card.get('title'):
                    found.append({'label': card['title'], 'url': url, 'image': '',
                                  'page_type': card.get('page_type', 'VideoPage')})
                    seen.add(url)
    return {'title': parser.title.replace('| NZ On Screen', '').strip(), 'links': found,
            'videos': _structured_videos(data, path) if data is not None else extract_videos(source, path),
            'page_type': page_type, 'page_id': (data or {}).get('id')}


def extract_videos(source, page_path=''):
    data = page_data(source, page_path)
    if data is not None:
        return _structured_videos(data, page_path)
    # Next.js serialises the same fields with escaped quotes in its RSC payload.
    text = source.replace('\\"', '"')
    # account_id used to follow video_id, but NZ On Screen no longer includes it
    # in current page payloads. Match the stable video navigation object instead.
    navigation = re.compile(
        r'"navigation":\{(?P<body>[^{}]*?"navigation_type":"(?P<type>video|page)"'
        r'[^{}]*?"video_id":"?(?P<id>\d+)"?[^{}]*?)\}', re.S)
    out, seen = [], set()
    matches = list(navigation.finditer(text))
    previous = 0
    for index, match in enumerate(matches):
        video_id = match.group('id')
        if video_id in seen:
            previous = match.end()
            continue
        navigation_body = match.group('body')
        target = re.search(r'"html_url":"([^"]+)"', navigation_body)
        # Series cards can navigate to the embedded player while their own
        # html_url points to a different episode. They are not clips on this
        # folder, even though navigation_type is "video".
        if page_path and match.group('type') == 'video':
            card_tail = text[match.end():match.end() + 350]
            card_url = re.match(r'[^{}]*?"html_url":"([^"]+)"', card_tail)
            if card_url:
                card_path = clean_url(card_url.group(1))
                if (card_path and not card_path.startswith('/m/player/') and
                        card_path.rstrip('/') != clean_url(page_path).rstrip('/')):
                    previous = match.end()
                    continue
        if page_path and match.group('type') == 'page' and target:
            target_path = clean_url(target.group(1))
            current_path = clean_url(page_path)
            # Series and other catalogue pages embed child cards whose
            # navigation objects also carry video IDs. They are links to a
            # different page, not videos playable on the current page.
            if (target_path and not target_path.startswith('/m/player/') and
                    target_path.rstrip('/') != current_path.rstrip('/')):
                previous = match.end()
                continue
        before = text[previous:match.start()]
        name_start = before.rfind('"name":"')
        description = 'Play video'
        if name_start >= 0:
            name_start += len('"name":"')
            name_ends = [position for position in
                         (before.find('","genres"', name_start),
                          before.find('","video_type"', name_start))
                         if position >= 0]
            if name_ends:
                description = before[name_start:min(name_ends)]
            else:
                simple_names = re.findall(r'"name":"([^"\\]*(?:\\.[^"\\]*)*)"', before)
                if simple_names:
                    description = simple_names[-1]
        description = description.replace('\\\\"', '\\"')

        after_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        after = text[match.end():after_end]
        parent = re.search(r'"parent_page":\{.*?"html_url":"([^"]+)"', after, re.S)
        if page_path and parent and clean_url(parent.group(1)).rstrip('/') != clean_url(page_path).rstrip('/'):
            previous = match.end()
            continue
        try:
            description = json.loads('"' + description + '"')
        except Exception:
            description = re.sub('<[^>]+>', '', description)
        out.append({'video_id': video_id,
                    'label': html.unescape(description).strip() or 'Play video'})
        seen.add(video_id)
        previous = match.end()
    if not out and not matches and not page_path:
        ids = re.findall(r'"videoId":"(\d+)".*?"accountId":"(\d+)"', text)
        for video_id, account_id in ids:
            if video_id not in seen:
                out.append({'video_id': video_id, 'account_id': account_id, 'label': 'Play video'})
                seen.add(video_id)
    return _order_videos(out)


def search(query='', page=1, genres=None, decades=None, category=None, sort=''):
    params = {'q': query, 'page_number': page}
    if genres: params['genres'] = genres
    if decades: params['decades'] = decades
    if category: params['media_category'] = category
    if sort: params['sort'] = sort
    return get_json('/api/v3/search/', params)


def filters():
    return get_json('/api/v3/search/filters')


def collection_filters():
    return get_json('/api/v3/search/filters/collections')


def profile_filters():
    for obj in _flight_objects(get_html('/profile/')):
        if 'defaultData' in obj and isinstance(obj.get('categories'), list) and 'sorting' in obj:
            return obj
    raise NZOSError('The profile-role filters are unavailable. Use the Profiles folder instead.')


def collection_search(theme, page=1, sort=''):
    return get_json('/api/v3/search/collection/' + str(int(theme)), {'page_number': page, 'sort': sort})


def profile_search(role, page=1, sort='last_name'):
    groups = get_json('/api/v3/search/profiles', {'profile_category': role, 'page_number': page, 'sort': sort})
    return groups[0] if isinstance(groups, list) and groups else {'results': [], 'pagination': {}}


def interview_search(group_id, page=1):
    return get_json('/api/v3/search/interview-group/' + str(int(group_id)) + '/interviews', {'page_number': page})


def playback(video_id):
    payload = {'eventType': 'play', 'platform': 'web', 'name': 'NZOS Kodi Add-on',
               'appVersion': '1.1.4',
               'device': {'deviceId': 'Kodi', 'deviceType': 'tv', 'userAgent': UA}}
    raw, _ = request('/api/v3/user/playback/' + str(video_id), payload)
    result = json.loads(raw.decode('utf-8'))
    content = result.get('content') or {}
    token, url = content.get('jwtToken'), content.get('url')
    if not token or not url:
        raise NZOSError('This title is not available for playback. Account, rental or regional restrictions may apply.')
    if not url.startswith('https://'):
        raise NZOSError('No secure playback API was returned for this title.')
    raw, _ = request(url, headers={'Authorization': 'Bearer ' + token})
    media = json.loads(raw.decode('utf-8'))
    dash = None
    for source in media.get('sources', []):
        if source.get('type') == 'application/dash+xml' and source.get('src', '').startswith('https://'):
            keys = source.get('key_systems') or {}
            widevine = keys.get('com.widevine.alpha') or {}
            if widevine.get('license_url', '').startswith('https://'):
                dash = (source['src'], widevine['license_url'])
                break
    if not dash:
        raise NZOSError('No Kodi-compatible Widevine DASH stream was returned for this title.')
    return {'manifest': dash[0], 'license': dash[1], 'title': media.get('name', ''),
            'session_id': result.get('sessionId') or '',
            'plot': media.get('long_description') or media.get('description') or '',
            'poster': media.get('poster') or media.get('thumbnail') or '',
            'duration': int((media.get('duration') or 0) / 1000),
            # Brightcove can include metadata/thumbnail WebVTT tracks whose cue
            # payload is an encoded identifier. Kodi renders those as subtitles
            # unless we explicitly keep only genuine language tracks.
            'subtitles': list(dict.fromkeys(x.get('src') for x in media.get('text_tracks', [])
                          if str(x.get('src') or '').startswith('https://') and str(x.get('kind', '')).lower()
                          in ('captions', 'subtitles')))}
