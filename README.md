<p align="center">
  <a href="https://5ivesaw.github.io/Ascii-Media-Player/">
    <img src="docs/assets/logo.svg" width="92" alt="ASCII Media Player logo">
  </a>
</p>

<h1 align="center">ASCII Media Player</h1>

<p align="center">
  Local audio playback with a real-time ASCII spectrum, available as a terminal application and an installable browser player.
</p>

<p align="center">
  <a href="https://5ivesaw.github.io/Ascii-Media-Player/">Launch the web player</a>
  ·
  <a href="#desktop-installation">Desktop installation</a>
  ·
  <a href="#platform-support">Platform support</a>
  ·
  <a href="#publishing-from-termux">Publish from Termux</a>
</p>

<p align="center">
  <img src="docs/assets/terminal-frame.svg" alt="ASCII Media Player interface preview">
</p>

## Overview

ASCII Media Player is a local-first audio player built around two interfaces:

- A Python terminal application for Windows and Linux.
- An offline-capable browser application for Windows, Linux, and Android.

The terminal build scans music folders recursively, handles playback and seeking, converts unsupported formats through FFmpeg, caches converted audio, and optionally downloads audio with `yt-dlp`. The web build analyzes local audio with the Web Audio API and never uploads the selected files.

## Version 2.1

The 2.1 website upgrade adds:

- A redesigned responsive product site and app shell.
- A multi-track local queue with previous, next, repeat, shuffle, and remove controls.
- Spectrum and waveform ASCII rendering modes.
- Four visual themes and adjustable visualizer density.
- Keyboard shortcuts, improved focus states, and reduced-motion support.
- A generated signal demo with no bundled copyrighted media.
- An install prompt for compatible PWA browsers.
- Better offline caching and update handling.
- PNG and SVG application artwork for Android and desktop installation.
- Search metadata, a social preview card, `robots.txt`, `sitemap.xml`, and a Pages fallback page.
- Automatic GitHub Pages deployment on every relevant push to `main`.
- A Termux publisher that detects the repository, calculates the Pages URL, enables Pages, updates the repository website field, validates the project, commits, pushes, and waits for deployment.

## Platform support

| Platform | Terminal application | Web application | Recommended route |
|---|---:|---:|---|
| Windows 10/11 | Supported | Supported | Terminal application or installed PWA |
| Linux | Supported | Supported | Terminal application or installed PWA |
| Android | Not targeted | Supported | Installed PWA or browser |

Android support is delivered through the browser edition. This avoids presenting Pygame audio and raw terminal input in Termux as a fully supported Android desktop experience.

## Desktop installation

### Requirements

- Python 3.10 or newer
- FFmpeg for FLAC, AAC, M4A, WebM, Opus, and WMA conversion
- An ANSI-capable terminal

### Install

```bash
git clone https://github.com/5ivesaw/Ascii-Media-Player.git
cd Ascii-Media-Player
python -m pip install -r requirements.txt
```

### Run

```bash
python app.py "/path/to/music"
```

Interactive folder selection:

```bash
python app.py
```

Skip the startup animation:

```bash
python app.py "/path/to/music" --no-banner
```

Pre-convert compatible files into reusable cached WAV files:

```bash
python app.py --convert-only "/path/to/music"
```

## Terminal controls

| Key | Action |
|---|---|
| `Space` | Play or pause |
| `N` | Next track |
| `P` | Previous track |
| `Left` / `Right` | Seek backward or forward five seconds |
| `Up` / `Down` | Raise or lower volume |
| `M` | Toggle mute |
| `/` | Search the local library |
| `Y` | Download through `yt-dlp` |
| `Q` | Quit |

## Web player

The production website lives in `docs/` and deploys through GitHub Pages.

Live site: https://5ivesaw.github.io/Ascii-Media-Player/

The browser player supports:

- Multi-file selection and drag-and-drop.
- A local queue with current-track highlighting.
- MP3, WAV, OGG, FLAC, M4A, and any other format decoded by the browser.
- Real-time spectrum and waveform ASCII modes.
- Play, pause, previous, next, seek, volume, repeat, shuffle, and fullscreen.
- Theme and density controls.
- A generated signal demo.
- Offline shell caching.
- PWA installation on supported Android and desktop browsers.

To preview locally:

```bash
python -m http.server 8000 --directory docs
```

Then open `http://localhost:8000`.

## Publishing from Termux

The included `scripts/publish-termux.sh` performs the complete publish flow. It:

1. Clones the latest `main` branch.
2. Replaces project files with this upgrade.
3. Detects `OWNER/REPOSITORY` from the Git remote.
4. Calculates the GitHub Pages URL.
5. Rewrites managed repository and site links.
6. Validates Python, JavaScript, JSON, XML, and required website files.
7. Commits and pushes to `main`.
8. Enables Pages with the workflow publishing source when GitHub CLI authentication is available.
9. Updates the repository website field to the deployed Pages URL.
10. Waits for the Pages workflow and prints the final address.

Run it from the extracted package:

```bash
bash scripts/publish-termux.sh
```

The script supports another repository URL as its first argument:

```bash
bash scripts/publish-termux.sh https://github.com/OWNER/REPOSITORY.git
```

## GitHub Pages deployment

The workflow in `.github/workflows/pages.yml` runs whenever `docs/` or the workflow changes on `main`. It validates the static site, uploads `docs/` as the Pages artifact, and deploys it to the `github-pages` environment.

The publisher uses the authenticated GitHub CLI to set the repository homepage to the calculated site URL. This API step requires repository administration access. The website deployment still works if that metadata update is skipped.

## Project structure

```text
.
├── app.py
├── requirements.txt
├── README.md
├── LICENSE
├── scripts/
│   ├── configure-site.sh
│   ├── publish-termux.sh
│   └── validate-project.py
├── .github/
│   └── workflows/
│       ├── pages.yml
│       └── validate.yml
└── docs/
    ├── index.html
    ├── 404.html
    ├── styles.css
    ├── player.js
    ├── site-config.js
    ├── sw.js
    ├── manifest.webmanifest
    ├── robots.txt
    ├── sitemap.xml
    ├── version.json
    └── assets/
        ├── logo.svg
        ├── wordmark.svg
        ├── terminal-frame.svg
        ├── og-card.svg
        ├── og-card.png
        ├── icon-192.png
        ├── icon-512.png
        └── maskable-512.png
```

## Privacy

Audio selected in the web player is opened through local object URLs and analyzed on-device. The project contains no upload endpoint, account system, analytics SDK, tracking pixel, or remote media database.

The optional terminal `yt-dlp` command makes network requests only when explicitly invoked. Users are responsible for following the rules and copyright requirements that apply to the selected source.

## Development checks

```bash
python -m py_compile app.py
python scripts/validate-project.py
node --check docs/player.js
node --check docs/sw.js
```

## License

Released under the MIT License. See [LICENSE](LICENSE).

[repository]: https://github.com/5ivesaw/Ascii-Media-Player
[site]: https://5ivesaw.github.io/Ascii-Media-Player/
