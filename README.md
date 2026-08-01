<p align="center">
  <img src="docs/assets/logo.svg" width="88" alt="ASCII Media Player logo">
</p>

<h1 align="center">ASCII Media Player</h1>

<p align="center">
  A local-first audio player with a terminal interface, live ASCII visualization, format conversion, and an installable browser edition.
</p>

<p align="center">
  <a href="https://5ivesaw.github.io/Ascii-Media-Player/">Open the web player</a>
  ·
  <a href="#desktop-installation">Desktop installation</a>
  ·
  <a href="#platform-support">Platform support</a>
</p>

<p align="center">
  <img src="docs/assets/terminal-frame.svg" alt="ASCII Media Player terminal preview">
</p>

## What it is

ASCII Media Player turns local audio into a responsive text-mode experience. The project now has two surfaces:

- A Python terminal player for Windows and Linux.
- A browser/PWA player for Windows, Linux, and Android.

The terminal build handles recursive library scanning, playback controls, cached FFmpeg conversion, local search, and optional `yt-dlp` downloads. The web build reads local files directly in the browser and generates its spectrum from the Web Audio API. Files selected in the web player are not uploaded.

## Highlights

- Plays MP3, WAV, and OGG directly through Pygame.
- Converts FLAC, AAC, M4A, WebM, Opus, and WMA to cached WAV files through FFmpeg.
- Uses non-blocking keyboard input on both Windows and POSIX terminals.
- Scans nested folders and sorts the library consistently.
- Supports pause, track navigation, seeking, volume, mute, and local search.
- Includes optional URL or search-based audio downloading through `yt-dlp`.
- Includes a responsive website with a real local-audio visualizer.
- Installs as an offline-capable PWA on supported browsers.
- Requires no account, cloud library, or media upload.

## Platform support

| Platform | Terminal application | Web application | Recommended route |
|---|---:|---:|---|
| Windows 10/11 | Supported | Supported | Terminal application |
| Linux | Supported | Supported | Terminal application |
| Android | Not targeted | Supported as PWA | Web application |

Android support is provided by the browser edition because Pygame audio and raw terminal input are not reliable across Android terminal environments. This keeps Android support functional instead of marking an untested Termux path as supported.

## Desktop installation

### Requirements

- Python 3.10 or newer
- FFmpeg for compressed formats outside MP3, WAV, and OGG
- A terminal with ANSI color support

### Install

```bash
git clone https://github.com/5ivesaw/Ascii-Media-Player.git
cd Ascii-Media-Player
python -m pip install -r requirements.txt
```

### Run

Pass a music folder directly:

```bash
python app.py "/path/to/music"
```

Or launch without a path and select the folder interactively:

```bash
python app.py
```

Skip the startup banner:

```bash
python app.py "/path/to/music" --no-banner
```

Convert supported compressed files into reusable cached WAV files:

```bash
python app.py --convert-only "/path/to/music"
```

## FFmpeg installation

### Windows

```powershell
winget install Gyan.FFmpeg
```

Restart the terminal after installation.

### Debian, Ubuntu, Pop!_OS

```bash
sudo apt update
sudo apt install ffmpeg
```

### Fedora

Install FFmpeg from the RPM Fusion repositories available for your Fedora release.

### Arch Linux

```bash
sudo pacman -S ffmpeg
```

## Controls

| Key | Action |
|---|---|
| `Space` | Play or pause |
| `N` | Next track |
| `P` | Previous track |
| `Left` / `Right` | Seek backward or forward five seconds |
| `Up` / `Down` | Raise or lower volume |
| `M` | Toggle mute |
| `/` | Search the local library |
| `Y` | Download from a URL or search phrase with `yt-dlp` |
| `Q` | Quit |

## Web player

The website is stored in `docs/` and is deployed with GitHub Pages.

It supports:

- Local file selection and drag-and-drop.
- MP3, WAV, OGG, FLAC, M4A, and other formats supported by the browser.
- Live frequency analysis with the Web Audio API.
- Playback, seeking, volume, and fullscreen controls.
- A generated signal demo that requires no sample music.
- Offline shell caching through a service worker.
- PWA installation on Android and desktop browsers.

Open the hosted player:

https://5ivesaw.github.io/Ascii-Media-Player/

To preview it locally, serve the `docs` directory rather than opening the HTML file directly, because service workers require HTTP or HTTPS:

```bash
python -m http.server 8000 --directory docs
```

Then open `http://localhost:8000`.

## Project structure

```text
.
├── app.py
├── requirements.txt
├── README.md
├── LICENSE
├── .github/
│   └── workflows/
│       └── pages.yml
└── docs/
    ├── index.html
    ├── styles.css
    ├── player.js
    ├── manifest.webmanifest
    ├── sw.js
    └── assets/
        ├── logo.svg
        └── terminal-frame.svg
```

## Privacy

The terminal application reads files from the folder you choose. The browser application creates local object URLs and analyzes audio on-device. The project does not include an upload endpoint, user account system, analytics SDK, or remote media database.

The optional `yt-dlp` function makes external network requests only when you explicitly use the `Y` command. Follow the terms and copyright rules that apply to the source you access.

## Development checks

```bash
python -m py_compile app.py
node --check docs/player.js
```

For the website, also test file loading, seeking, the generated signal demo, responsive layout, and PWA installation from a local HTTP server.

## License

Released under the MIT License. See [LICENSE](LICENSE).
