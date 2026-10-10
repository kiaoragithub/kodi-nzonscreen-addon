# NZ On Screen for Kodi

[![Kodi 21 Omega](https://img.shields.io/badge/Kodi-21%20Omega-17B2E7)](https://kodi.tv/)
[![Python 3](https://img.shields.io/badge/Python-3-3776AB)](https://www.python.org/)
[![Tests](https://github.com/kiaoragithub/kodi-nzonscreen-addon/actions/workflows/validate.yml/badge.svg)](https://github.com/kiaoragithub/kodi-nzonscreen-addon/actions/workflows/validate.yml)
[![Version](https://img.shields.io/badge/version-1.1.4-brightgreen)](https://github.com/kiaoragithub/kodi-nzonscreen-addon)

![NZ On Screen for Kodi](resources/fanart.png)

<p align="center">
  <img src="resources/icon.png" alt="NZ On Screen add-on icon" width="256">
</p>

An unofficial Kodi video add-on for browsing and playing the public catalogue at
[NZ On Screen](https://www.nzonscreen.com/). It is designed for Kodi 21 Omega and Python 3.

## Features

- Browse television, film, series, music videos, music artists, commercials, short films,
  web productions, collections, interview collections, profiles and NZOS+
- Search by live NZ On Screen categories, genres and decades
- Browse collection themes, profile roles, paginated interview groups and nested seasons
- Open first-level and deeper nested website pages
- Play single videos and correctly ordered multi-part programmes
- Display the exact trailer, excerpt, part or credits label during playback
- Show available metadata, artwork and genuine subtitle/caption tracks
- Retrieve short-lived playback tokens only when playback starts
- Use encrypted MPEG-DASH/Widevine through Kodi InputStream Adaptive
- Sign in with password saving disabled by default and an explicit Yes/No choice
- Browse the NZ On Screen watchlist and use authenticated NZOS+ rentals
- Resume viewing progress across Kodi and the NZ On Screen website

## Recommended installation — automatic updates

1. Download [`repository.nzonscreen-1.0.1.zip`](https://kiaoragithub.github.io/kodi-nzonscreen-addon/repository.nzonscreen-1.0.1.zip).
2. In Kodi, open **Settings → System → Add-ons** and enable **Unknown sources** if needed.
3. Open **Settings → Add-ons → Install from zip file** and select the downloaded repository ZIP.
4. Choose **Install from repository → NZ On Screen Add-on Repository → Video add-ons → NZ On Screen → Install**.

Installing through the repository allows Kodi to receive future add-on updates automatically.

## Direct installation

Download [`NZ-On-Screen-Kodi-1.1.4.zip`](https://github.com/kiaoragithub/kodi-nzonscreen-addon/raw/main/NZ-On-Screen-Kodi-1.1.4.zip),
then select **Settings → Add-ons → Install from zip file** in Kodi. Direct installation works,
but installing the repository first is recommended for automatic updates.

Kodi may ask to install or enable InputStream Adaptive and the Widevine CDM when a protected
video is played for the first time.

## Playback behaviour

- A page containing one playable video starts it directly.
- A page containing multiple clips offers **Play all parts** or a choice of individual clips.
- **Play all parts** plays every clip consecutively in one Kodi playlist.
- Numbered programme parts are shown in their natural order, with credits last.
- Rental, account, rights and geographic restrictions continue to be enforced by NZ On Screen.
- The public catalogue includes restricted titles; general search does not expose rental entitlements.
  The earlier availability toggle had no effect and has been removed.
- Rental clips are labelled separately from public trailers. Complete checkout in the website browser.
- Provider filenames are replaced with the website title and the selected clip label.

## Accounts and privacy

Sign-in uses NZ On Screen's normal CSRF-protected API. Session cookies are stored in the
add-on profile and refreshed by the playback service after sign-in or sign-out. Cookie writes
are atomic and use owner-only permissions where the operating system supports them.

Choose **No** when asked to save a password to keep the password out of Kodi settings.
Choosing **Yes** stores it locally in Kodi settings **without encryption**; masking it in
the settings screen is not encryption. Turning password saving off clears saved credentials
the next time the add-on is opened. Signing out also clears saved credentials.

Watchlist requests use the website's normalized item types. Resume updates are associated
with the actual NZOS stream; other Kodi videos are not recorded as NZOS viewing.
Payments, account changes and rental checkout stay on nzonscreen.com.

## Compatibility checks

See the [10 October 2026 maintenance audit](docs/maintenance-2026-10-10.md) for the tested URLs,
confirmed fixes, provider denials and remaining limitations. Live checks verified public page data,
playback responses, DASH manifests and genuine captions. They did **not** establish decoded Kodi
playback, startup audio continuity or successful authenticated rental playback.

Manual Kodi 21 checks are still required for playback startup, captions, playlist transitions,
return navigation, installation/update dialogs, sign-in/out, password Yes/No and an entitled rental.

## Troubleshooting

If a title does not play:

1. Confirm the installed add-on version under **Add-ons → My add-ons → Video add-ons → NZ On Screen**.
2. Check that InputStream Adaptive is installed and enabled.
3. Restart Kodi after a Widevine installation or update.
4. Try another public title to distinguish an add-on problem from a title-specific restriction.
5. [Open a bug report](https://github.com/kiaoragithub/kodi-nzonscreen-addon/issues/new?template=bug_report.yml) with the exact title, page URL, Kodi version and relevant Kodi log lines.

Do not publish complete Kodi logs without checking them for personal information.

## Development

Run the parser regression tests with:

```bash
python -m unittest discover -s tests -v
```

Every change to the parser or repository metadata is automatically checked by GitHub Actions.
Rebuild both release ZIP copies, metadata and checksums with `python scripts/build_release.py`
after updating the source version and release documentation. CI checks Python 3.9 and 3.12,
including the service and a reproducible rebuild.
See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidance and [CHANGELOG.md](CHANGELOG.md)
for release history.

## Project links

- [Install using the NZ On Screen repository](https://kiaoragithub.github.io/kodi-nzonscreen-addon/)
- [Download the latest direct-install ZIP](https://github.com/kiaoragithub/kodi-nzonscreen-addon/raw/main/NZ-On-Screen-Kodi-1.1.4.zip)
- [Read the release history](CHANGELOG.md)
- [Report a problem or request a feature](https://github.com/kiaoragithub/kodi-nzonscreen-addon/issues)
- [View the source code](https://github.com/kiaoragithub/kodi-nzonscreen-addon)

## Legal and availability

This is an unofficial community project and is not affiliated with or endorsed by NZ On Screen.
Content, availability, rental access, accounts, regional restrictions, DRM and rights are controlled
by NZ On Screen and its providers. The add-on does not bypass login, payment, DRM or geographic restrictions.

Licensed under GPL-3.0-or-later. See [LICENSE.txt](LICENSE.txt).

Keywords: Kodi add-on, Kodi video add-on, New Zealand television, New Zealand film, NZ On Screen,
Aotearoa screen history, Python Kodi plugin.
