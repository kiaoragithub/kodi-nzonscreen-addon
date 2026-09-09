# Contributing

Bug reports and focused pull requests are welcome.

## Reporting playback problems

Please include:

- The exact title and NZ On Screen page URL
- Whether the failure affects a direct click, a chosen clip or both
- Kodi version and operating system
- Installed NZ On Screen add-on version
- Relevant error lines from the Kodi log

Remove personal information, tokens and unrelated log content before posting.

## Code changes

1. Keep compatibility with Kodi 21 Omega and Python 3.
2. Do not add mechanisms that bypass rentals, accounts, geographic restrictions or DRM.
3. Add a regression test for parser and routing fixes.
4. Run `python -m unittest discover -s tests -v` before opening a pull request.
5. Keep the source version, repository metadata, ZIP name and checksums synchronized for releases.
