from __future__ import annotations

import argparse
import hashlib
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pygame
import pyfiglet
from colorama import Back, Fore, Style, init
from mutagen import File as MutagenFile
import yt_dlp

init(autoreset=True)

APP_NAME = "ASCII Media Player"
APP_VERSION = "2.1.0"
PLAYABLE_EXTENSIONS = {".mp3", ".wav", ".ogg"}
CONVERTIBLE_EXTENSIONS = {".flac", ".aac", ".m4a", ".webm", ".opus", ".wma"}
SUPPORTED_EXTENSIONS = PLAYABLE_EXTENSIONS | CONVERTIBLE_EXTENSIONS


def clear_screen() -> None:
    print("\033[2J\033[H", end="")


def format_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def cache_directory() -> Path:
    if os.name == "nt":
        root = Path(os.getenv("LOCALAPPDATA", tempfile.gettempdir()))
    else:
        root = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
    path = root / "ascii-media-player"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ffmpeg_help() -> str:
    if os.name == "nt":
        return "Install FFmpeg with: winget install Gyan.FFmpeg"
    if "ANDROID_ROOT" in os.environ or "TERMUX_VERSION" in os.environ:
        return "Install FFmpeg in Termux with: pkg install ffmpeg"
    return "Install FFmpeg with your package manager, for example: sudo apt install ffmpeg"


class KeyReader:
    """Non-blocking keyboard input for Windows and POSIX terminals."""

    def __init__(self) -> None:
        self._fd: Optional[int] = None
        self._saved_attrs = None
        self._enabled = False

    def start(self) -> None:
        if self._enabled or not sys.stdin.isatty():
            return
        if os.name != "nt":
            import termios
            import tty

            self._fd = sys.stdin.fileno()
            self._saved_attrs = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
        self._enabled = True

    def stop(self) -> None:
        if not self._enabled:
            return
        if os.name != "nt" and self._fd is not None and self._saved_attrs is not None:
            import termios

            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._saved_attrs)
        self._enabled = False

    def __enter__(self) -> "KeyReader":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()

    def read(self) -> Optional[str]:
        if not self._enabled:
            return None
        if os.name == "nt":
            return self._read_windows()
        return self._read_posix()

    @staticmethod
    def _read_windows() -> Optional[str]:
        import msvcrt

        if not msvcrt.kbhit():
            return None
        key = msvcrt.getwch()
        if key in ("\x00", "\xe0"):
            special = msvcrt.getwch()
            return {"K": "LEFT", "M": "RIGHT", "H": "UP", "P": "DOWN"}.get(special)
        if key == " ":
            return "SPACE"
        return key.lower()

    def _read_posix(self) -> Optional[str]:
        import select

        if self._fd is None:
            return None
        ready, _, _ = select.select([self._fd], [], [], 0)
        if not ready:
            return None
        data = os.read(self._fd, 8).decode(errors="ignore")
        if data.startswith("\x1b["):
            return {"A": "UP", "B": "DOWN", "C": "RIGHT", "D": "LEFT"}.get(data[-1])
        if data == " ":
            return "SPACE"
        return data[:1].lower() if data else None


@dataclass
class Track:
    source: Path
    playable: Path
    title: str
    duration: float


class ASCIIMediaPlayer:
    def __init__(self, media_dir: Optional[str] = None, no_banner: bool = False) -> None:
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        pygame.mixer.pre_init(44100, -16, 2, 1024)
        pygame.init()
        pygame.mixer.init()

        self.media_dir = Path(media_dir).expanduser().resolve() if media_dir else None
        self.no_banner = no_banner
        self.ffmpeg = shutil.which("ffmpeg")
        self.key_reader = KeyReader()
        self.playlist: list[Path] = []
        self.current_index = 0
        self.current_track: Optional[Track] = None
        self.running = True
        self.playing = False
        self.paused = False
        self.volume = 0.72
        self.previous_volume = self.volume
        self.track_offset = 0.0
        self.track_started_at = 0.0
        self.pause_started_at = 0.0
        self.visualizer = [0.0] * 48
        self.visualizer_trails = [0.0] * 48
        self.last_frame = 0.0
        self.status = "Ready"
        self.status_until = 0.0

    def set_status(self, message: str, seconds: float = 3.0) -> None:
        self.status = message
        self.status_until = time.monotonic() + seconds

    def startup_animation(self) -> None:
        if self.no_banner:
            return
        clear_screen()
        banner = pyfiglet.figlet_format("ASCII", font="slant", width=100)
        print(Fore.CYAN + banner)
        print(Fore.WHITE + "MEDIA PLAYER" + Style.DIM + f"  v{APP_VERSION}")
        print(Style.DIM + "Local playback. Terminal visuals. No account required.")
        time.sleep(1.0)

    def choose_media_directory(self) -> bool:
        while True:
            if self.media_dir and self.media_dir.is_dir() and self.scan_directory(self.media_dir):
                return True
            clear_screen()
            print(Fore.CYAN + APP_NAME)
            print("Enter a folder containing audio files, or Q to quit.")
            value = input("> ").strip().strip('"')
            if value.lower() == "q":
                return False
            path = Path(value).expanduser()
            if path.is_dir() and self.scan_directory(path.resolve()):
                self.media_dir = path.resolve()
                return True
            print(Fore.YELLOW + "No supported audio files were found in that folder.")
            time.sleep(1.2)
            self.media_dir = None

    def scan_directory(self, directory: Path) -> bool:
        self.media_dir = directory
        self.playlist = sorted(
            (
                path
                for path in directory.rglob("*")
                if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
            ),
            key=lambda path: str(path).lower(),
        )
        self.current_index = min(self.current_index, max(0, len(self.playlist) - 1))
        return bool(self.playlist)

    def conversion_target(self, source: Path) -> Path:
        signature = f"{source.resolve()}:{source.stat().st_mtime_ns}:{source.stat().st_size}"
        digest = hashlib.sha256(signature.encode()).hexdigest()[:16]
        return cache_directory() / f"{source.stem}-{digest}.wav"

    def convert_to_wav(self, source: Path, show_progress: bool = False) -> Optional[Path]:
        if not self.ffmpeg:
            self.set_status(ffmpeg_help(), 8)
            return None
        target = self.conversion_target(source)
        if target.exists() and target.stat().st_size > 0:
            return target

        command = [
            self.ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(target),
        ]
        try:
            if show_progress:
                self.set_status(f"Converting {source.name}", 30)
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            return target if target.exists() else None
        except (subprocess.CalledProcessError, OSError) as error:
            detail = error.stderr.decode(errors="ignore").strip() if isinstance(error, subprocess.CalledProcessError) and error.stderr else str(error)
            self.set_status(f"Conversion failed: {detail or source.name}", 6)
            return None

    @staticmethod
    def duration_for(path: Path) -> float:
        try:
            metadata = MutagenFile(path)
            if metadata is not None and metadata.info is not None:
                return float(getattr(metadata.info, "length", 0.0) or 0.0)
        except Exception:
            pass
        try:
            return float(pygame.mixer.Sound(str(path)).get_length())
        except Exception:
            return 0.0

    def prepare_track(self, source: Path) -> Optional[Track]:
        playable = source
        if source.suffix.lower() not in PLAYABLE_EXTENSIONS:
            playable = self.convert_to_wav(source, show_progress=True)
            if playable is None:
                return None
        return Track(
            source=source,
            playable=playable,
            title=source.stem,
            duration=self.duration_for(playable),
        )

    def play_current(self, start: float = 0.0) -> None:
        if not self.playlist:
            return
        source = self.playlist[self.current_index]
        track = self.prepare_track(source)
        if track is None:
            self.next_track()
            return
        try:
            pygame.mixer.music.load(str(track.playable))
            pygame.mixer.music.set_volume(self.volume)
            if start > 0:
                pygame.mixer.music.play(start=max(0.0, start))
            else:
                pygame.mixer.music.play()
        except Exception as error:
            self.set_status(f"Unable to play {source.name}: {error}", 6)
            return

        self.current_track = track
        self.track_offset = max(0.0, start)
        self.track_started_at = time.monotonic()
        self.pause_started_at = 0.0
        self.playing = True
        self.paused = False
        self.set_status(f"Playing {source.name}")

    def stop(self) -> None:
        pygame.mixer.music.stop()
        self.playing = False
        self.paused = False

    def next_track(self) -> None:
        if not self.playlist:
            return
        self.current_index = (self.current_index + 1) % len(self.playlist)
        self.play_current()

    def previous_track(self) -> None:
        if not self.playlist:
            return
        self.current_index = (self.current_index - 1) % len(self.playlist)
        self.play_current()

    def toggle_pause(self) -> None:
        if not self.playing:
            self.play_current()
            return
        if self.paused:
            pygame.mixer.music.unpause()
            paused_for = time.monotonic() - self.pause_started_at
            self.track_started_at += paused_for
            self.paused = False
            self.set_status("Resumed")
        else:
            pygame.mixer.music.pause()
            self.pause_started_at = time.monotonic()
            self.paused = True
            self.set_status("Paused")

    def current_position(self) -> float:
        if not self.playing:
            return 0.0
        now = self.pause_started_at if self.paused else time.monotonic()
        return max(0.0, self.track_offset + (now - self.track_started_at))

    def seek(self, delta: float) -> None:
        if not self.current_track:
            return
        position = self.current_position() + delta
        if self.current_track.duration:
            position = min(position, max(0.0, self.current_track.duration - 0.1))
        position = max(0.0, position)
        was_paused = self.paused
        self.play_current(start=position)
        if was_paused:
            pygame.mixer.music.pause()
            self.pause_started_at = time.monotonic()
            self.paused = True
        self.set_status(f"Seek {delta:+.0f} seconds")

    def change_volume(self, delta: float) -> None:
        self.volume = min(1.0, max(0.0, self.volume + delta))
        pygame.mixer.music.set_volume(self.volume)
        self.set_status(f"Volume {round(self.volume * 100)}%")

    def toggle_mute(self) -> None:
        if self.volume > 0:
            self.previous_volume = self.volume
            self.volume = 0.0
        else:
            self.volume = max(0.1, self.previous_volume)
        pygame.mixer.music.set_volume(self.volume)
        self.set_status("Muted" if self.volume == 0 else f"Volume {round(self.volume * 100)}%")

    def prompt(self, label: str) -> str:
        self.key_reader.stop()
        try:
            print("\n" + label)
            return input("> ").strip()
        finally:
            self.key_reader.start()

    def search_local(self) -> None:
        query = self.prompt("Search this library")
        if not query:
            return
        matches = [index for index, path in enumerate(self.playlist) if query.lower() in path.name.lower()]
        if not matches:
            self.set_status(f"No local match for: {query}", 4)
            return
        self.current_index = matches[0]
        self.play_current()

    def download_audio(self) -> None:
        if self.media_dir is None:
            return
        query = self.prompt("Enter a video URL or search phrase")
        if not query:
            return
        target = str(self.media_dir / "%(title).180B [%(id)s].%(ext)s")
        options = {
            "format": "bestaudio/best",
            "outtmpl": target,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }
        self.set_status("Downloading audio", 120)
        try:
            with yt_dlp.YoutubeDL(options) as downloader:
                source = query if "://" in query else f"ytsearch1:{query}"
                downloader.extract_info(source, download=True)
            self.scan_directory(self.media_dir)
            self.current_index = max(0, len(self.playlist) - 1)
            self.play_current()
        except Exception as error:
            self.set_status(f"Download failed: {error}", 8)

    def update_visualizer(self) -> None:
        columns = max(20, min(64, (shutil.get_terminal_size((100, 30)).columns - 4) // 2))
        if len(self.visualizer) != columns:
            self.visualizer = [0.0] * columns
            self.visualizer_trails = [0.0] * columns

        active = self.playing and not self.paused
        position = self.current_position()
        for index in range(columns):
            phase = position * (2.0 + (index % 7) * 0.08) + index * 0.53
            wave = (math.sin(phase) + math.sin(phase * 0.47 + index)) * 0.22 + 0.48
            noise = random.random() * 0.34
            target = max(0.0, min(1.0, wave + noise)) if active else 0.02
            self.visualizer[index] += (target - self.visualizer[index]) * (0.45 if target > self.visualizer[index] else 0.18)
            self.visualizer_trails[index] = max(self.visualizer[index], self.visualizer_trails[index] - 0.035)

    def progress_line(self, width: int) -> str:
        if not self.current_track or self.current_track.duration <= 0:
            return "-" * width
        ratio = min(1.0, self.current_position() / self.current_track.duration)
        filled = min(width, max(0, int(ratio * width)))
        if filled >= width:
            return "=" * width
        return "=" * filled + ">" + "-" * max(0, width - filled - 1)

    def draw(self) -> None:
        terminal = shutil.get_terminal_size((100, 30))
        width = max(48, min(110, terminal.columns))
        graph_height = max(6, min(12, terminal.lines - 13))
        content_width = width - 4

        clear_screen()
        print(Back.WHITE + Fore.BLACK + f" {APP_NAME.upper()} " + Style.RESET_ALL + Style.DIM + f" v{APP_VERSION}")
        track_name = self.current_track.source.name if self.current_track else self.playlist[self.current_index].name
        state = "PAUSED" if self.paused else "PLAYING" if self.playing else "READY"
        print(Fore.CYAN + track_name[:content_width])
        print(Style.DIM + f"{state}  {self.current_index + 1}/{len(self.playlist)}  {self.media_dir}")

        position = self.current_position()
        duration = self.current_track.duration if self.current_track else 0.0
        time_label = f"{format_time(position)} / {format_time(duration)}" if duration else format_time(position)
        progress_width = max(10, content_width - len(time_label) - 3)
        print(f"[{self.progress_line(progress_width)}] {time_label}")

        volume_width = 18
        volume_count = round(self.volume * volume_width)
        print(f"VOL [{'#' * volume_count}{'-' * (volume_width - volume_count)}] {round(self.volume * 100):3d}%")
        print("+" + "-" * (len(self.visualizer) * 2) + "+")
        palette = [Fore.BLUE, Fore.CYAN, Fore.GREEN, Fore.YELLOW, Fore.MAGENTA]
        for row in range(graph_height, 0, -1):
            threshold = row / graph_height
            cells = []
            for index, value in enumerate(self.visualizer):
                if value >= threshold:
                    color = palette[min(len(palette) - 1, int(value * len(palette)))]
                    cells.append(color + "##" + Style.RESET_ALL)
                elif self.visualizer_trails[index] >= threshold:
                    cells.append(Style.DIM + ".." + Style.RESET_ALL)
                else:
                    cells.append("  ")
            print("|" + "".join(cells) + "|")
        print("+" + "-" * (len(self.visualizer) * 2) + "+")

        if time.monotonic() > self.status_until:
            self.status = "Space pause  N/P track  Arrows seek/volume  M mute  / search  Y download  Q quit"
        print(Fore.WHITE + self.status[:content_width])

    def handle_key(self, key: Optional[str]) -> None:
        if not key:
            return
        actions = {
            "SPACE": self.toggle_pause,
            "n": self.next_track,
            "p": self.previous_track,
            "LEFT": lambda: self.seek(-5),
            "RIGHT": lambda: self.seek(5),
            "UP": lambda: self.change_volume(0.05),
            "DOWN": lambda: self.change_volume(-0.05),
            "m": self.toggle_mute,
            "/": self.search_local,
            "y": self.download_audio,
        }
        if key == "q":
            self.running = False
            return
        action = actions.get(key)
        if action:
            action()

    def run(self) -> int:
        self.startup_animation()
        if not self.choose_media_directory():
            return 0
        self.play_current()
        try:
            with self.key_reader:
                while self.running:
                    now = time.monotonic()
                    self.handle_key(self.key_reader.read())
                    if self.playing and not self.paused and not pygame.mixer.music.get_busy():
                        self.next_track()
                    if now - self.last_frame >= 1 / 12:
                        self.update_visualizer()
                        self.draw()
                        self.last_frame = now
                    time.sleep(0.01)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
            pygame.quit()
            clear_screen()
        return 0


def batch_convert(directory: str) -> int:
    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 2
    player = ASCIIMediaPlayer(no_banner=True)
    candidates = [path for path in root.rglob("*") if path.suffix.lower() in CONVERTIBLE_EXTENSIONS]
    if not candidates:
        print("No convertible files found.")
        return 0
    failures = 0
    for index, source in enumerate(candidates, 1):
        print(f"[{index}/{len(candidates)}] {source.name}")
        if player.convert_to_wav(source, show_progress=True) is None:
            failures += 1
    pygame.quit()
    print(f"Converted {len(candidates) - failures} file(s); {failures} failed.")
    return 1 if failures else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Terminal audio player with an ASCII visualizer")
    parser.add_argument("media_dir", nargs="?", help="Folder to scan recursively for audio")
    parser.add_argument("--convert-only", metavar="DIR", help="Convert supported compressed formats into cached WAV files")
    parser.add_argument("--no-banner", action="store_true", help="Skip the startup banner")
    parser.add_argument("--version", action="version", version=f"%(prog)s {APP_VERSION}")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.convert_only:
        return batch_convert(args.convert_only)
    return ASCIIMediaPlayer(media_dir=args.media_dir, no_banner=args.no_banner).run()


if __name__ == "__main__":
    raise SystemExit(main())
