# NZ On Screen compatibility audit — 10 October 2026

Release: **1.1.4**, following baseline **1.1.3** at commit
`5f6b3864248fa0b3b1fa6270f4d69101f11e6c4e`.

Confirmed defects required an update. This is a signed-out public-site and source/package audit,
not a certificate that every title or a physical Kodi installation works.

## Evidence and scope

- Clean checkout of the existing main branch; no pre-existing local changes were present.
- Baseline: 18 automated tests and the original package validation passed.
- 50 distinct website page URLs inspected: 47 primary URLs, the current settings route and two
  legacy title redirects. One obsolete account route returned 404; settings redirected to sign-in.
- Every live general-search category queried once; 12 categories and 45 genres exposed by the filter API.
- 18 general search requests: all categories, page 2, Unicode/ampersands, quoted terms, empty results,
  captioned genre, and combined television/1980s filtering. Browser search returned 20 of 56 Howard
  Morrison results; Load More returned 40 of 56.
- Dedicated APIs inspected for interview-group pagination (pages 1 and 2), collection themes,
  a history-themed collection result, and director-role profiles. Fifteen collection themes and
  23 profile roles were observed. Public Next.js bundles were read to verify API contracts; they
  were not executed by the add-on parser.
- 43 clip IDs mapped across the sampled content pages, including trailers, six- and eight-episode
  programmes, six documentary parts plus credits, music videos and interviews. Folder cards were
  distinguished from clips belonging to the current page.
- Playback initiation and media metadata requested for 21 IDs: **16 compatible responses**,
  **2 rental-entitlement denials**, **3 geographic denials**. No denial was circumvented.
- Three DASH manifests were retrieved and parsed: Patu!, Cloth, and A Deaf Child in the Family.
  All included audio/video adaptations and Widevine signalling; the last also had a text adaptation.
  No media segments were downloaded and no Widevine challenge/licence was acquired.
- Genuine WebVTT cues were checked for all seven 1951 clips and A Deaf Child in the Family.
  Those tracks were language captions and did not contain thumbnail `#xywh` payloads.
- Offline reduced fixtures retain 43 observed page-data cases, covering 15 content/page types.
  They omit tokens, cookies, account data, prose descriptions and artwork bytes.
- Latest existing validation runs on the baseline main commit were successful. No open GitHub
  issue was returned by the repository's open-issue search.

Requests used cached responses for subsequent parser checks, with at most three concurrent public
page/bundle reads and two concurrent playback checks. There was no site-wide crawl, login guessing,
payment operation or repeated attempt to bypass a restriction.

## Comparison and root causes

| Confirmed gap in 1.1.3 | Observed evidence | General correction in 1.1.4 |
|---|---|---|
| Deep season URL classified as a playable episode | K Road Chronicles has SeasonPage at `/all-series/k-road-chronicles/season-4/`, containing no episode list | Use page types and season-folder routing; read the parent public series tree and retain only that season's children |
| Client-rendered/folded catalogue data can be absent from HTML anchors | Series tree contains four seasons; individual SeasonPage is sparse | Decode Next.js JSON strings, supplement real page cards, expose season folders |
| Interview groups lose complete pagination | Funny As reports 100 interviews, ScreenTalk 374; server HTML has only the first 20 interview cards | Use the site's paginated interview-group API |
| Collection themes and profile roles unsupported | Live filters expose 15 themes and 23 roles | Add matching filter folders and dedicated paginated API queries |
| Nested Search treated as a normal scraped page | Search links route through `page`; the search interface is interactive | Route bare Search to the keyboard and query/filter URLs to results, preserving repeated values |
| Legacy parent validation can reject redirected content | `/title/flat-3-2013` and `/title/pulp-comedy-1996` redirect to reorganized series URLs | Validate the returned page against its final same-site URL |
| Regex parent/card bounds depend on serialized layout | Current site has hero videos, nested rails, episode cards and repeated navigation data | Prefer structured hydration objects; validate each object's own parent/target, deduplicate IDs, retain bounded legacy compatibility |
| Natural order only recognizes `part one` forms | Live labels also use `Episode 1`, `01: Maar`, and `The first of six parts` | Recognize all these numbering forms and place credits last |
| Technical provider names appear during playback | Black Sheeps metadata returns a long encoding/CTA filename; Cloth and Patu! have provider naming variants | Propagate the website title while preserving the exact clip label and validated video ID |
| Multipart folder view lacks Play all | Only the playable-page selection dialog offers it | Add the action to multipart folders as well |
| Cancelled resolver and dependency refusal never finish | Source paths return without `setResolvedUrl(False)`; playpage exceptions use directory completion | Complete the correct Kodi resolver on cancellation/failure |
| Long-running service cannot see later sign-in/out | Service loads cookies once, but plugin invocations write a separate jar | Reload before requests, skip unchanged writes, atomic private cookie-file replacement |
| Progress end update queries a stopped player, and stale IDs can affect unrelated playback | `getTime()` is called after playback stops; shared window values are used for any playing video | Cache the last position, associate it with the actual manifest/plugin item, preserve a new playlist item's session |
| Watchlist item types do not match website normalization | Live MyListToggle lowercases and replaces spaces/underscores with hyphens | Normalize POST item types the same way |
| Obsolete account link | `/account/` returns 404; live account menu links `/settings` | Use current account-settings URL and keep account/payment actions in the browser |
| Settings mix old attributes with Kodi's v1 schema | No group/control elements, old default attributes and old password masking attribute | Use Kodi 21 groups, child defaults/controls and hidden password input; remove the unused availability toggle |
| Sensitive server bodies can enter logs | HTTP errors include the first 300 raw response characters | Map status/known region/entitlement codes to safe messages without echoing body contents |
| Insecure API/licence URLs are not explicitly rejected | Source accepts a returned playback URL and any licence URL | Require HTTPS API, DASH, Widevine licence and caption URLs |
| Package directory still promotes 1.0.1 | `docs/zips/plugin.video.nzonscreen/index.html` links only 1.0.1 | Generate a latest-first release index |
| Metadata source points to the content site rather than add-on code | Existing addon.xml source URL | Correct source/support links and synchronize repository metadata |

These are confirmed present structures and source gaps. A historical website snapshot was not
available, so this audit does not claim every gap was introduced since the previous release,
or that any unobserved category was removed/renamed. Existing live category/genre names are
fetched dynamically rather than assumed from old names.

## Requirement-by-requirement result

| Requested check | Result and limit |
|---|---|
| 1. Home and every folder | All original root routes reviewed; all API-backed root categories queried; featured/TV/film/NZOS+ pages parsed. New theme/role/season folders covered offline. Account folders need authenticated testing. |
| 2. Search entry points, terms, filters, pagination, return | Root/nested routes, special characters, repeated filters, empty/cancelled queries and paging covered. Browser Load More verified. Physical Kodi return/history remains manual. |
| 3. Single-video/direct playback | IDs and resolver calls checked; compatible API/manifest responses confirmed. Actual Kodi decode not tested. |
| 4. Multiple videos/clips/trailers/credits/parts | Gallery, Pictures of Susan, Mārama, Terry, Under the Mountain and 1951 structures checked. |
| 5. Individual/Play all order | Selection and playlist contents verified with Kodi mocks, observed sequences and shuffled numbering regressions. Actual continuous playback remains manual. |
| 6. Correct titles | IDs/labels validated per object; website title now replaces provider filenames. No assertion based on viewing decoded footage. |
| 7. Music structures | Aua Atu Rā, Cloth, Baked Beans, Goldenhorse and Che Fu checked; MusicPage and artist links covered. Aua Atu Rā was geographically denied. |
| 8–9. New types and deep links | Fifteen observed types, season nesting, interview groups, specialized filters and legacy redirects checked. Unavailable/external-only players report no supported video rather than guessing a stream. |
| 10. IDs/parent/duplicates | Forty-three mappings, same-site/foreign parents, duplicate IDs, related cards and legacy-fallback rejection covered. |
| 11. APIs/tokens/DASH/Widevine/InputStream | Public playback API/token/media contracts confirmed; three parsed MPDs; licence URLs present. Omega InputStream source lists existing properties. No CDM/device licence acquisition. |
| 12. Startup audio | Fixed-resolution selection retained and checked in mocks. Audio continuity cannot be established without a Kodi/audio device. |
| 13. Captions/subtitles | Genuine caption files confirmed; metadata/thumbnail/unknown/insecure/duplicate tracks excluded by regression tests. Kodi caption rendering remains manual. |
| 14. Return after playback | Existing no-redirect Search and non-resolver playlist approach preserved; cancellation fixed. Container selection/history after playback remains manual. |
| 15. Signed-out browsing | Confirmed for public pages/search/playback examples; normal rights denials retained. |
| 16. Sign-in/out/password/session | Live login/logout/CSRF routes and payloads reviewed; Yes/No, masking/defaults, cookie refresh/private atomic writes and secret-safe errors tested offline. No real account login performed. |
| 17. Watchlist/resume/entitled rentals | Endpoint/type/progress contracts and mocked lifecycle covered. Real watchlist, resume persistence and entitled rental playback unavailable without a test account and active entitlement. Watchlist currently uses the site's observed pageSize=100 request. |
| 18. Restrictions | Two entitlement and three region denials confirmed; safe distinct messages added. No payment/login/DRM/region bypass. |
| 19. Kodi 21/Python 3 | Source compiled, supported Kodi API calls reviewed, settings schema corrected; CI covers Python 3.9/3.12. No Kodi executable in this environment. |
| 20. Art/metadata/legal/docs/support/history | PNG icon (512×512) and fanart (1920×1080) decoded and visually inspected, retained unchanged; source/support links, privacy/limits and changelog updated. |
| 21. Both install methods | Repository installer manifest/endpoints and direct ZIP structure checked; runtime Kodi installation/update is manual. |
| 22. Version consistency | 1.1.4 in source manifest, mirror, UA, playback appVersion, metadata, tests, new ZIP filenames and README. Archived version references intentionally retained. Repository installer remains 1.0.1. |
| 23. ZIP/checksums/XML/cache | Current ZIP equality, CRCs, single-root structure, exact included-source bytes, XML validity and all published MD5 sidecars checked. Current packages exclude caches and compiled files; archived releases preserved. |
| 24. Existing/new tests | Existing tests retained; new observed-structure, routing, API/security, settings, session, service and package regressions included. |
| 25. Actions/issues | Baseline Actions green, open issue search empty; workflow expanded to two Python versions, service compilation and reproducible release rebuild. Final push validation must be checked separately. |

## Manual validation still required

On an actual Kodi 21 Omega device with InputStream Adaptive and a supported Widevine CDM:

1. Install/update via the repository and separately install the direct ZIP; verify version 1.1.4.
2. Open every root folder, theme/role folder and K Road Chronicles season; test nested Search and Next page.
3. Play Patu!, Cloth, a public trailer and a captioned 1951 part. Observe startup audio and subtitle rendering.
4. Choose individual parts, cancel selection, decline a missing dependency, and play complete multipart playlists.
5. Stop/end playback and confirm the original folder/results and selected item remain available without a new keyboard prompt.
6. Sign in with No, sign out, then repeat with explicit Yes and disable saving; inspect only your own local settings.
7. Add/remove a watchlist item, resume after restarting Kodi, switch to an unrelated add-on and verify no NZOS progress attribution.
8. With an already active rental entitlement, test the entitled film. Check expired entitlement and regional denials without bypassing them.

The public API results provide high confidence (0.95) in the identified structures and fixes.
Decoded playback, audio and authenticated account flows remain **unverified**, not assumed successful.
Overall end-to-end compatibility confidence is **0.75** until the manual checks above pass.

## Exact page inventory

All 50 page URLs below were requested. HTTP 200 on a login redirect verifies the signed-out gate, not account access.

| Requested path (on https://www.nzonscreen.com) | HTTP | Redirect destination, when different |
|---|---|---|
| / | 200 | — |
| /television-in-nz/ | 200 | — |
| /film-in-nz/ | 200 | — |
| /nzos/ | 200 | — |
| /search/ | 200 | — |
| /collection/ | 200 | — |
| /profile/ | 200 | — |
| /interviews/screentalk/ | 200 | — |
| /welcome-to-the-new-nz-on-screen/ | 200 | — |
| /login/ | 200 | — |
| /signup/ | 200 | — |
| /account/ | 404 |  |
| /all-series/country-calendar/ | 200 | — |
| /all-series/under-the-mountain/ | 200 | — |
| /all-series/koha/why-stay-home-on-a-friday-nite-part-one-1989/ | 200 | — |
| /all-series/gallery/gallery-fred-dagg-and-company-1973/ | 200 | — |
| /all-series/david-lomas-investigates/david-lomas-investigates-episode-one-2020/ | 200 | — |
| /videos/pictures-of-susan-2012/ | 200 | — |
| /videos/patu-1983/ | 200 | — |
| /videos/terry-and-the-gunrunners-full-series-1985/ | 200 | — |
| /videos/mum-im-alien-pregnant/ | 200 | — |
| /videos/black-sheeps-2026/ | 200 | — |
| /videos/dear-john-basf-commercial-1981/ | 200 | — |
| /videos/nice-hot-bath-1995/ | 200 | — |
| /videos/marama-2025/ | 200 | — |
| /videos/coming-home-in-the-dark-2021/ | 200 | — |
| /all-music-videos/aua-atu-ra-marlon-williams-2025/ | 200 | — |
| /all-music-videos/cloth-1997/ | 200 | — |
| /all-music-videos/baked-beans-1977/ | 200 | — |
| /music-artists/goldenhorse/ | 200 | — |
| /music-artists/che-fu/ | 200 | — |
| /collection/politics/ | 200 | — |
| /collection/top-ten-nz-tv-ads/ | 200 | — |
| /collection/nz-short-film-collection/ | 200 | — |
| /profile/taika-waititi/ | 200 | — |
| /profile/brynley-stent/ | 200 | — |
| /interviews/flight-of-the-conchords-funny-as-interview/ | 200 | — |
| /interviews/screentalk-legends-annie-collins/ | 200 | — |
| /interviews/ginette-mcdonald-fires-nymphomaniacs-and-lynn-of-tawa/ | 200 | — |
| /all-series/k-road-chronicles/ | 200 | — |
| /all-series/k-road-chronicles/season-4/ | 200 | — |
| /all-series/k-road-chronicles/season-4/k-road-chronicles-series-four-episode-seven-2024/ | 200 | — |
| /all-series/under-the-mountain/under-the-mountain-full-series-1981/ | 200 | — |
| /interviews/funny-as/ | 200 | — |
| /videos/1951-2001/ | 200 | — |
| /videos/a-deaf-child-in-the-family-1969/ | 200 | — |
| /m/more-info/all-series/country-calendar/ | 200 | — |
| /settings | 200 | /login/?next=%2Fsettings%2F |
| /title/flat-3-2013 | 200 | /all-series/flat3/ |
| /title/pulp-comedy-1996 | 200 | /all-series/pulp-comedy/ |

## Exact playback API inventory

These are API contract checks; they do not establish decoded Kodi playback. No tokens or signed URLs are retained here.

| Parent path | Clip / public video ID | Result |
|---|---|---|
| /all-series/gallery/gallery-fred-dagg-and-company-1973/ | Interviews about the NZBC / 6394817352112 | Playable API response |
| /all-series/gallery/gallery-fred-dagg-and-company-1973/ | Interviews about Daylight Savings / 6394830030112 | Playable API response |
| /videos/patu-1983/ | Patu! / 6392424229112 | Playable API response |
| /videos/mum-im-alien-pregnant/ | The trailer for this feature film. / 6405343526112 | Geographic denial |
| /videos/black-sheeps-2026/ | The trailer for this feature film. / 6405345569112 | Playable API response |
| /videos/marama-2025/ | Mārama / 6404389980112 | Rental entitlement denied |
| /videos/marama-2025/ | The trailer for this feature film / 6393473255112 | Playable API response |
| /videos/coming-home-in-the-dark-2021/ | Coming Home in the Dark / 6406227948112 | Rental entitlement denied |
| /all-music-videos/aua-atu-ra-marlon-williams-2025/ | Marlon Williams - Aua Atu Rā / 6403551170112 | Geographic denial |
| /all-music-videos/cloth-1997/ | Cloth - The New Loungehead feat. Sulata / 6402667456112 | Playable API response |
| /all-music-videos/baked-beans-1977/ | Mother Goose - 'Baked Beans' / 6393345956112 | Playable API response |
| /interviews/screentalk-legends-annie-collins/ | Screentalk Legends - Annie Collins / 6394368105112 | Playable API response |
| /all-series/k-road-chronicles/season-4/k-road-chronicles-series-four-episode-seven-2024/ | Episode 7: Food for Thought / 6403622864112 | Geographic denial |
| /videos/1951-2001/ | The first of six parts of this full length documentary. / 6393114402112 | Playable API response |
| /videos/1951-2001/ | The second of 6 parts of this full length documentary. / 6394658180112 | Playable API response |
| /videos/1951-2001/ | The third of 6 parts of this full length documentary. / 6394656309112 | Playable API response |
| /videos/1951-2001/ | The fourth of 6 parts of this full length documentary. / 6394656204112 | Playable API response |
| /videos/1951-2001/ | The fifth of 6 parts of this full length documentary. / 6394658083112 | Playable API response |
| /videos/1951-2001/ | The sixth of 6 parts of this full length documentary. / 6394657951112 | Playable API response |
| /videos/1951-2001/ | The credits from this documentary. / 6394653897112 | Playable API response |
| /videos/a-deaf-child-in-the-family-1969/ | A full length short film. / 6393378357112 | Playable API response |

Final local validation: **70 unittest cases passed**, including 43 live-page fixture subcases. Standalone package validation runs eight of those same cases and is not added to the total.
