import os
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib import nzos


ADDON = xbmcaddon.Addon('plugin.video.nzonscreen')
SESSION_FILE = os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo('profile')), 'session.cookies')
WINDOW = xbmcgui.Window(10000)


def save_progress(player):
    video_id = WINDOW.getProperty('NZOS.VideoId')
    session_id = WINDOW.getProperty('NZOS.SessionId')
    if not video_id or not session_id:
        return
    try:
        nzos.update_watching_progress(video_id, int(player.getTime()), session_id)
    except Exception as exc:
        xbmc.log('NZ On Screen progress update failed: %s' % exc, xbmc.LOGWARNING)


def run():
    nzos.configure_session(SESSION_FILE)
    monitor = xbmc.Monitor()
    player = xbmc.Player()
    was_playing = False
    last_update = 0
    while not monitor.abortRequested():
        playing = player.isPlayingVideo()
        if playing and WINDOW.getProperty('NZOS.VideoId'):
            now = time.monotonic()
            if now - last_update >= 15:
                save_progress(player)
                last_update = now
            was_playing = True
        elif was_playing:
            save_progress(player)
            WINDOW.clearProperty('NZOS.VideoId')
            WINDOW.clearProperty('NZOS.SessionId')
            was_playing = False
            last_update = 0
        if monitor.waitForAbort(1):
            break


if __name__ == '__main__':
    run()
