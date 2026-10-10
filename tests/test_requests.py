import http.cookiejar
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import urllib.error
import urllib.parse
from unittest.mock import MagicMock, patch

from resources.lib import nzos


class RequestTests(unittest.TestCase):
    def test_watchlist_types_match_live_website_normalization(self):
        with patch.object(nzos, '_account_write') as write:
            nzos.add_to_my_list('39644', 'Music video')
            write.assert_called_once_with('/api/v3/user/my-list/', 'POST',
                                          {'itemId': '39644', 'itemType': 'music-video'})

    def test_search_preserves_unicode_ampersand_quotes_and_repeated_filters(self):
        with patch.object(nzos, 'request', return_value=(b'{}', 'application/json')) as request:
            nzos.search('Māori & "music"', 2, [39, 49], [1980, 1990], ['Film', 'Television'], '-last_published_at')
        values = urllib.parse.parse_qs(urllib.parse.urlsplit(request.call_args.args[0]).query)
        self.assertEqual(values['q'], ['Māori & "music"'])
        self.assertEqual(values['genres'], ['39', '49'])
        self.assertEqual(values['decades'], ['1980', '1990'])
        self.assertEqual(values['media_category'], ['Film', 'Television'])
        self.assertEqual(values['page_number'], ['2'])

    def test_login_and_logout_keep_csrf_protection(self):
        with patch.object(nzos, 'get_json', return_value={'csrf_token': 'test-csrf'}), \
                patch.object(nzos, 'request', return_value=(b'{}', 'application/json')) as request:
            nzos.login('test@example.com', 'test-password')
            self.assertEqual(request.call_args.args[2], {'X-CSRFToken': 'test-csrf'})
            nzos.logout()
            self.assertEqual(request.call_args.args[2], {'X-CSRFToken': 'test-csrf'})

    def test_error_bodies_never_leak_secrets(self):
        for code in (400, 401, 403, 404, 429, 500):
            error = urllib.error.HTTPError('https://example.test', code, 'error', {},
                                          io.BytesIO(b'{"password":"private-secret","token":"private-token"}'))
            message = str(nzos._http_error(error))
            self.assertNotIn('private-', message)
            self.assertIn(str(code), message)

    def test_region_and_entitlement_denials_are_distinct(self):
        for body, word in ((b'[{"error_subcode":"CLIENT_GEO"}]', 'location'),
                           (b'{"errorMessage":"User not entitled to play this asset"}', 'rental')):
            error = urllib.error.HTTPError('https://example.test', 403, 'error', {}, io.BytesIO(body))
            self.assertIn(word, str(nzos._http_error(error)))

    def test_insecure_request_is_rejected_before_network(self):
        with patch.object(nzos, '_opener') as opener:
            with self.assertRaises(nzos.NZOSError): nzos.request('http://example.test', headers={'Authorization': 'secret'})
            opener.open.assert_not_called()

    def test_subtitles_keep_only_genuine_secure_unique_tracks(self):
        content = {'sources': [{'type': 'application/dash+xml', 'src': 'https://example.test/a.mpd',
                               'key_systems': {'com.widevine.alpha': {'license_url': 'https://example.test/wv'}}}],
                   'text_tracks': [{'src': 'https://example.test/thumb.vtt', 'kind': 'metadata'},
                                   {'src': 'https://example.test/thumb2.vtt', 'kind': 'thumbnails'},
                                   {'src': 'https://example.test/en.vtt', 'kind': 'captions'},
                                   {'src': 'https://example.test/en.vtt', 'kind': 'captions'},
                                   {'src': 'https://example.test/mi.vtt', 'kind': 'subtitles'},
                                   {'src': 'http://example.test/unsafe.vtt', 'kind': 'captions'}]}
        responses = [(json.dumps({'content': {'jwtToken': 'test-token', 'url': 'https://example.test/api'}}).encode(), ''),
                     (json.dumps(content).encode(), '')]
        with patch.object(nzos, 'request', side_effect=responses) as request:
            media = nzos.playback('123')
        self.assertEqual(media['subtitles'], ['https://example.test/en.vtt', 'https://example.test/mi.vtt'])
        self.assertEqual(request.call_args.kwargs['headers'], {'Authorization': 'Bearer test-token'})

    def test_insecure_api_and_license_fail_closed(self):
        with patch.object(nzos, 'request', return_value=(b'{"content":{"jwtToken":"secret","url":"http://example.test/api"}}', '')) as req:
            with self.assertRaises(nzos.NZOSError): nzos.playback('123')
            self.assertEqual(req.call_count, 1)
        content = {'sources': [{'type': 'application/dash+xml', 'src': 'https://example.test/a.mpd',
                               'key_systems': {'com.widevine.alpha': {'license_url': 'http://example.test/wv'}}}]}
        with patch.object(nzos, 'request', side_effect=[(b'{"content":{"jwtToken":"secret","url":"https://example.test/api"}}', ''),
                                                       (json.dumps(content).encode(), '')]):
            with self.assertRaises(nzos.NZOSError): nzos.playback('123')

    def test_account_network_errors_are_normalized(self):
        with patch.object(nzos, 'get_json', return_value={'csrf_token': 'csrf'}), \
                patch.object(nzos, '_reload_session'), patch.object(nzos, '_opener') as opener:
            opener.open.side_effect = urllib.error.URLError('private-token')
            with self.assertRaises(nzos.NZOSError) as error: nzos.add_to_my_list(1, 'Film')
        self.assertNotIn('private-token', str(error.exception))


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.original = nzos._cookies, nzos._opener
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'session.cookies'
        nzos.configure_session(str(self.path))

    def tearDown(self):
        nzos._cookies, nzos._opener = self.original
        self.directory.cleanup()

    def cookie(self, value):
        return http.cookiejar.Cookie(0, 'sessionid', value, None, False, 'www.nzonscreen.com',
                                    False, False, '/', True, True, None, True, None, None, {}, False)

    def test_cookie_saved_atomically_with_owner_only_permissions(self):
        nzos._cookies.set_cookie(self.cookie('session-a'))
        nzos._save_session()
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)
        self.assertEqual(list(Path(self.directory.name).iterdir()), [self.path])
        nzos._cookies.clear(); nzos._reload_session()
        self.assertEqual(list(nzos._cookies)[0].value, 'session-a')

    def test_service_reload_observes_external_login_and_logout(self):
        external = http.cookiejar.MozillaCookieJar(str(self.path))
        external.set_cookie(self.cookie('new-session'))
        external.save(ignore_discard=True)
        nzos._reload_session()
        self.assertEqual(list(nzos._cookies)[0].value, 'new-session')
        external.clear(); external.save(ignore_discard=True)
        nzos._reload_session()
        self.assertEqual(list(nzos._cookies), [])

    def test_readonly_request_does_not_overwrite_shared_session(self):
        response = MagicMock(); response.read.return_value = b'{}'
        response.headers.get.return_value = 'application/json'
        with patch.object(nzos, '_opener') as opener, patch.object(nzos, '_save_session') as save:
            opener.open.return_value.__enter__.return_value = response
            nzos.request('/api/v3/user/me')
            save.assert_not_called()


if __name__ == '__main__': unittest.main()
