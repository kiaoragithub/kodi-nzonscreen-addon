# Changelog

## 1.1.0 — 2026-09-09

- Add session-only NZ On Screen account sign-in and sign-out.
- Add My watchlist and authenticated NZOS+ rental playback.
- Read website resume positions and synchronize playback progress every 15 seconds.
- Use session-only login by default and never handle card details inside Kodi.
- Add an optional Save password Yes/No setting, disabled by default with a security warning.
- Keep rental checkout, transaction management and account security on nzonscreen.com.

## 1.0.7 — 2026-09-09

- Keep a stable DASH video representation from playback startup.
- Prevent the brief audio mute caused by a startup representation resync on affected Kodi devices.
- Preserve existing Search, direct playback and Play all parts behaviour.

## 1.0.6 — 2026-09-09

- Fix Search returning to the add-on root after the on-screen keyboard closes.
- Render entered search terms directly into a Kodi results listing.
- Start Play all parts outside the active playable-item resolver to prevent Kodi crashes.
- Preserve direct single-video playback and ordered multi-part playlists.

## 1.0.5 — 2026-09-09

- Add a Play all parts option to every page containing multiple video clips.
- Queue naturally ordered programme parts in a Kodi video playlist.
- Keep individual trailer, excerpt, part and credits selection available.
- Return to the originating page or results list after the playlist finishes.

## 1.0.4 — 2026-09-09

- Keep search results at a persistent Kodi container URL.
- Return to the same search-results list after playback instead of reopening search.
- Preserve the selected query and results page across playback.

## 1.0.3 — 2026-09-09

- Validate extracted video IDs against their parent NZ On Screen page.
- Preserve exact trailer, excerpt, part and credits labels during Kodi playback.
- Correctly decode clip labels containing quotation marks.
- Naturally order multi-part programmes and place credits last.
- Validate 265 video mappings across 99 live title pages.

## 1.0.2 — 2026-09-09

- Restore direct playback after NZ On Screen removed the nearby `account_id` field from page data.
- Support current single-video and multi-video navigation objects.
- Add parser regression tests.
- Remove generated Python cache files from the installation ZIP.

## 1.0.1 — 2026-09-09

- Filter metadata and thumbnail WebVTT tracks from Kodi subtitles.

## 1.0.0 — 2026-09-09

- Initial public release.
