# Changelog

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
