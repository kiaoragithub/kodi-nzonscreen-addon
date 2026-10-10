# Changelog

## 1.1.4 — 2026-10-10

- Browse real season folders and recover their episode lists from the public parent-series tree.
- Paginate interview groups, and add live collection-theme and profile-role filters.
- Route nested Search links, preserve repeated filters, and validate legacy redirects against their final page.
- Read structured Next.js data without executing scripts; validate each clip's own parent and deduplicate IDs.
- Order numbered episodes, numbered prefixes and ordinal programme parts naturally, with credits last.
- Use the website title and exact clip label instead of technical provider filenames; distinguish rental clips from trailers.
- Offer Play all parts inside multipart folders and complete cancelled/failed playback resolvers.
- Refresh shared session cookies per request, save them atomically with private permissions, normalize watchlist types,
  and prevent credentials/tokens from leaking through raw error messages.
- Cache final progress, associate it with the actual NZOS stream, and avoid attributing other Kodi playback to NZOS.
- Correct the account-settings link and Kodi 21 settings schema; retain explicit Save password Yes/No,
  clear saved credentials on sign-out, and remove the unused availability toggle.
- Correct source/support metadata and the release directory index; add reproducible release tooling.
- Expand offline live-structure, navigation, account-contract, progress, security and package regression coverage.
- Document the signed-out live audit and the remaining account/Kodi-device validation requirements.

## 1.1.3 — 2026-09-29

- Exclude episode-card player IDs from series folders when the card points to a different title page.
- Preserve direct title playback and the existing parts, clips and credits selection.
- Add a regression test for video-type episode cards seen on the live Country Calendar series page.

## 1.1.2 — 2026-09-10

- Populate Series, Music videos, Profiles and other catalogue folders through the live,
  paginated NZ On Screen search API instead of client-rendered landing-page HTML.
- Add direct folders for Music artists, Interview collections, Commercials, Short films and Web productions.
- Recognize the current `media_type_category` search field so watchlist actions remain available.
- Reject child-page navigation video IDs on series folders, preventing the wrong embedded video from appearing.
- Generate decade filters from the current year instead of a hard-coded year.
- Expand navigation, account preference, version consistency and package icon regression tests.

## 1.1.1 — 2026-09-09

- Replace the installed add-on icon with the supplied green NZ On Screen artwork.
- Add clearer public project, installation, download, support and release links.
- Publish synchronized direct-install and automatic-update repository packages.

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
