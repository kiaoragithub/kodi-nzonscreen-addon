import html
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

BASE = 'https://www.nzonscreen.com'
UA = 'Mozilla/5.0 (Linux; Android TV) Kodi/21 NZOnScreen-Addon/1.0.5'


class NZOSError(Exception):
    pass


def request(path, data=None, headers=None, timeout=25):
    url = path if path.startswith('http') else BASE + ('/' if not path.startswith('/') else '') + path
    body = json.dumps(data).encode('utf-8') if data is not None else None
    hdr = {'User-Agent': UA, 'Accept': 'application/json, text/html;q=0.9, */*;q=0.8'}
    if data is not None:
        hdr.update({'Content-Type': 'application/json', 'Origin': BASE, 'Referer': BASE + '/'})
    if headers:
        hdr.update(headers)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, body, hdr), timeout=timeout,
                                    context=ssl.create_default_context()) as response:
            return response.read(), response.headers.get('Content-Type', '')
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', 'replace')[:300]
        raise NZOSError('NZ On Screen returned HTTP %s: %s' % (exc.code, detail))
    except (urllib.error.URLError, OSError) as exc:
        raise NZOSError('Could not connect to NZ On Screen: %s' % exc)


def get_json(path, params=None):
    if params:
        path += ('&' if '?' in path else '?') + urllib.parse.urlencode(params, doseq=True)
    raw, _ = request(path)
    return json.loads(raw.decode('utf-8'))


def get_html(path):
    raw, _ = request(path)
    return raw.decode('utf-8', 'replace')


class LinkParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.in_main = False
        self.depth = 0
        self.current = None
        self.links = []
        self.title = ''
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'main':
            self.in_main, self.depth = True, 1
        elif self.in_main:
            self.depth += 1
        if tag == 'title':
            self.in_title = True
        if self.in_main and tag == 'a' and a.get('href'):
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
        if self.in_main:
            self.depth -= 1
            if tag == 'main' or self.depth <= 0:
                self.in_main = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.current:
            self.current['text'].append(data)


def clean_url(url):
    url = urllib.parse.urljoin(BASE + '/', html.unescape(url))
    parsed = urllib.parse.urlsplit(url)
    if parsed.netloc not in ('www.nzonscreen.com', 'nzonscreen.com'):
        return ''
    return parsed.path + (('?' + parsed.query) if parsed.query else '')


SKIP = ('/login/', '/contact/', '/who-we-are/', '/how-we-work/', '/faqs/',
        '/website-disclaimer/', '/digital-media-trust-', '/nz-on-screen-nzos-ts-cs-',
        '/tv-terms-and-conditions/', '/png/', '/_next/', '/m/player/')


def page_links(path):
    source = get_html(path)
    parser = LinkParser()
    parser.feed(source)
    found, seen = [], set()
    for link in parser.links:
        url = clean_url(link['url'])
        if not url or url in seen or url == clean_url(path) or url == '/' or any(url.startswith(x) for x in SKIP):
            continue
        label = re.sub(r'\s+', ' ', link.get('label', '')).strip(' -|')
        if not label or label.lower() in ('more info', 'see more', 'sign in', 'search rapu'):
            continue
        image = urllib.parse.urljoin(BASE + '/', html.unescape(link.get('image', '')))
        found.append({'label': label[:180], 'url': url, 'image': image})
        seen.add(url)
    return {'title': parser.title.replace('| NZ On Screen', '').strip(), 'links': found,
            'videos': extract_videos(source, path)}


def extract_videos(source, page_path=''):
    # Next.js serialises the same fields with escaped quotes in its RSC payload.
    text = source.replace('\\"', '"')
    # account_id used to follow video_id, but NZ On Screen no longer includes it
    # in current page payloads. Match the stable video navigation object instead.
    navigation = re.compile(
        r'"navigation":\{[^{}]*?"navigation_type":"(?:video|page)"[^{}]*?'
        r'"video_id":"?(\d+)"?[^{}]*?\}', re.S)
    out, seen = [], set()
    matches = list(navigation.finditer(text))
    previous = 0
    for index, match in enumerate(matches):
        video_id = match.group(1)
        if video_id in seen:
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
    if not out:
        ids = re.findall(r'"videoId":"(\d+)".*?"accountId":"(\d+)"', text)
        for video_id, account_id in ids:
            if video_id not in seen:
                out.append({'video_id': video_id, 'account_id': account_id, 'label': 'Play video'})
                seen.add(video_id)
    part_words = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                  'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10}
    part_numbers = []
    for entry in out:
        found = re.search(r'\bpart\s+(\d+|%s)\b' % '|'.join(part_words), entry['label'].lower())
        token = found.group(1) if found else ''
        part_numbers.append(part_words[token] if token in part_words else
                            (int(token) if token.isdigit() else 0))
    if sum(number > 0 for number in part_numbers) >= 2:
        indexed = list(enumerate(out))
        indexed.sort(key=lambda pair: (0, part_numbers[pair[0]]) if part_numbers[pair[0]] else
                     ((2, pair[0]) if 'credit' in pair[1]['label'].lower() else (1, pair[0])))
        out = [entry for _, entry in indexed]
    return out


def search(query='', page=1, genres=None, decades=None, category=None, sort=''):
    params = {'q': query, 'page_number': page}
    if genres: params['genres'] = genres
    if decades: params['decades'] = decades
    if category: params['media_category'] = category
    if sort: params['sort'] = sort
    return get_json('/api/v3/search/', params)


def filters():
    return get_json('/api/v3/search/filters')


def playback(video_id):
    payload = {'eventType': 'play', 'platform': 'web', 'name': 'NZOS Kodi Add-on',
               'appVersion': '1.0.5',
               'device': {'deviceId': 'Kodi', 'deviceType': 'tv', 'userAgent': UA}}
    raw, _ = request('/api/v3/user/playback/' + str(video_id), payload)
    result = json.loads(raw.decode('utf-8'))
    content = result.get('content') or {}
    token, url = content.get('jwtToken'), content.get('url')
    if not token or not url:
        raise NZOSError(result.get('message') or 'This title is not available for public playback.')
    raw, _ = request(url, headers={'Authorization': 'Bearer ' + token})
    media = json.loads(raw.decode('utf-8'))
    dash = None
    for source in media.get('sources', []):
        if source.get('type') == 'application/dash+xml' and source.get('src', '').startswith('https://'):
            keys = source.get('key_systems') or {}
            widevine = keys.get('com.widevine.alpha') or {}
            if widevine.get('license_url'):
                dash = (source['src'], widevine['license_url'])
                break
    if not dash:
        raise NZOSError('No Kodi-compatible Widevine DASH stream was returned for this title.')
    return {'manifest': dash[0], 'license': dash[1], 'title': media.get('name', ''),
            'plot': media.get('long_description') or media.get('description') or '',
            'poster': media.get('poster') or media.get('thumbnail') or '',
            'duration': int((media.get('duration') or 0) / 1000),
            # Brightcove can include metadata/thumbnail WebVTT tracks whose cue
            # payload is an encoded identifier. Kodi renders those as subtitles
            # unless we explicitly keep only genuine language tracks.
            'subtitles': [x.get('src') for x in media.get('text_tracks', [])
                          if x.get('src') and str(x.get('kind', '')).lower()
                          in ('captions', 'subtitles')]}
