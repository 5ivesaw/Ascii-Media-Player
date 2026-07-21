# Ascii-Media-Player
## A terminal-based ASCII media player that supports MP3s and YouTube downloads, with visualizer and FFmpeg-powered format conversion. Made for fun and nostalgia, built in Python.




# 🎵 ASCII Media Player 🎥
A retro-style terminal-based media player that turns your audio experience into ASCII art!  
Built with Python, FFmpeg, and yt-dlp.

---

## 📦 Download (EXE Version)
You can download the latest **standalone Windows `.exe` build** from [Here](https://www.mediafire.com/file/488ytx7sp1xx7xp/Ascii+Media+Player.exe/file) Or, if you want the python download it [here](https://github.com/goatdotlol/Ascii-Media-Player/blob/b91f277e9d4f4358e02cfb6a919e2442f9787d3d/app.py)


> ✅ No Python needed – just download and run `Ascii Media Player.exe`

### 🛠 FFmpeg Not Found?

If you get an error like **"FFmpeg not found"** or the player doesn't start, follow these steps:

1. Go to [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Click **Windows**, then download a build from **gyan.dev** or **BtbN** (they’re trusted sources)
3. Unzip the downloaded file
4. Inside the `bin` folder, you’ll find:
   - `ffmpeg.exe`
   - `ffplay.exe`
   - `ffprobe.exe`

Copy all **three files** (`ffmpeg.exe`, `ffplay.exe`, and `ffprobe.exe`) into the same folder as `Ascii Media Player.exe`.

---

## 💡 Features
- 🎧 Play MP3, WAV, OGG, FLAC, and other audio formats
- 📺 Converts unsupported formats using FFmpeg
- 🔊 Terminal-based ASCII visualizer
- 🔎 Search & play music from YouTube with `yt-dlp`
- 🎮 Keyboard controls for playback and volume
- 📝 Fully standalone EXE or runnable via Python

---

## 🎮 Controls

| Key         | Action                     |
|-------------|----------------------------|
| `Spacebar`  | Play / Pause               |
| `n`         | Next track                 |
| `p`         | Previous track             |
| `↑` / `↓`   | Volume Up / Volume Down    |
| `s`         | Search and download from YouTube |
| `q`         | Quit player                |

---

### 🐍 Run from source (Python)

Make sure Python 3.9+ is installed.

1. Clone the repo:
   ```bash
   git clone https://github.com/goatdotlol/Ascii-Media-Player
   cd Ascii-Media-Player
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run:
   ```bash
   python app.py
   ```

---

### 📦 Requirements

```
numpy
Pillow
pygame
mutagen
colorama
yt-dlp
pyfiglet
```

Install with:

```bash
pip install -r requirements.txt
```

---

### 📫 Contact

dont

---

### 📄 License

MIT License © 2025 juihyioytigutgi7fevrii
