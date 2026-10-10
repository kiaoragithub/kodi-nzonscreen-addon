import os
import time
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import nzos


ADDON = xbmcaddon.Addon('plugin.video.nzonscreen')
SESSION_FILE = os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo('profile')), 'session.cookies')
WINDOW = xbmcgui.Window(10000)


class ProgressTracker:
    """Associate progress with the actual NZOS stream, not stale window state."""
    def __init__(self, window):
        self.window = window
        self.active = None
        self.position = 0
        self.last_update = 0

    def save(self):
        if self.active and self.active[1]:
            try:
                nzos.update_watching_progress(self.active[0], self.position, self.active[1])
            except Exception:
                xbmc.log('NZ On Screen progress update failed; account access may be unavailable.',
                         xbmc.LOGWARNING)

    def finish(self):
        self.save()
        if self.active and (self.window.getProperty('NZOS.VideoId'),
                            self.window.getProperty('NZOS.SessionId')) == self.active[:2]:
            for key in ('NZOS.VideoId', 'NZOS.SessionId', 'NZOS.Manifest'):
                self.window.clearProperty(key)
        self.active = None
        self.position = 0
        self.last_update = 0

    def tick(self, player, now):
        pending = tuple(self.window.getProperty('NZOS.' + key)
                        for key in ('VideoId', 'SessionId', 'Manifest'))
        context = None
        if player.isPlayingVideo() and pending[0] and pending[2]:
            try:
                playing_file = player.getPlayingFile()
                params = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(playing_file).query))
                if playing_file == pending[2] or (
                        playing_file.startswith('plugin://plugin.video.nzonscreen?') and
                        params.get('video_id') == pending[0]):
                    context = pending
            except Exception:
                pass
        if context != self.active:
            self.finish()
            self.active = context
        if not self.active:
            return
        try:
            self.position = max(0, int(player.getTime()))
        except Exception:
            return
        if now - self.last_update >= 15:
            self.save()
            self.last_update = now


def run():
    nzos.configure_session(SESSION_FILE)
    monitor = xbmc.Monitor()
    player = xbmc.Player()
    tracker = ProgressTracker(WINDOW)
    while not monitor.abortRequested():
        tracker.tick(player, time.monotonic())
        if monitor.waitForAbort(1):
            break
    tracker.finish()


if __name__ == '__main__':
    run()
