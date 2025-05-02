import os
import sys
import time
import threading
import random
import numpy as np
from PIL import Image
import pygame
from mutagen.mp3 import MP3
import io
import msvcrt
from colorama import init, Fore, Back, Style
import yt_dlp as youtube_dl
import pyfiglet
import subprocess
import shutil
import argparse

# Initialize colorama
init(autoreset=True)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

class ASCIIMediaPlayer:
    PLAYABLE_EXTS = ['.mp3', '.wav', '.ogg']
    SUPPORTED_EXTS = PLAYABLE_EXTS + ['.flac', '.aac', '.m4a', '.webm']

    def __init__(self, media_dir=None, convert_only=False):
        pygame.mixer.init()
        pygame.init()
        self.volume = 0.7
        self.prev_volume = self.volume
        self.playlist = []
        self.current_index = 0
        self.playing = False
        self.paused = False
        self.running = True
        self.last_key_check = 0
        self.visualizer_data = [0]*32
        self.visualizer_depth = [0]*32
        self.color_wave = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA]
        self.color_index = 0
        self.ffmpeg = shutil.which('ffmpeg')

        if not self.ffmpeg:
            msg = (
                "FFmpeg was not found on your system.\n"
                "To install it, follow these steps:\n\n"
                "1. Open CMD and run this command: \n"
                "   winget install ffmpeg\n\n"
                "2. After installation, restart this program.\n"
                "3. If ffmpeg still isn't found, add its folder (usually C:\\Program Files\\ffmpeg\\bin) to your PATH.\n"
            )
            with open("FFMPEG_MISSING_INSTRUCTIONS.txt", 'w') as f:
                f.write(msg)
            os.startfile("FFMPEG_MISSING_INSTRUCTIONS.txt")

        self.directory = media_dir

    def startup_animation(self):
        clear_screen()
        words = ["ASCII", "MEDIA", "PLAYER", "by goat.lol"]
        for word in words:
            banner = pyfiglet.figlet_format(word, width=80)
            clear_screen()
            for line in banner.splitlines():
                print(Fore.CYAN + line)
            time.sleep(0.8)
            clear_screen()
            print(Back.WHITE + " " * 80)
            time.sleep(0.2)
        time.sleep(0.5)

    def prompt_directory(self):
        clear_screen()
        print("Enter path to media folder:")
        path = input('> ').strip('"') or self.directory
        if path and os.path.isdir(path) and self.load_directory(path):
            return
        print("No supported media found. Try again.")
        time.sleep(1)
        self.prompt_directory()

    def load_directory(self, directory):
        self.directory = directory
        self.playlist = []
        for root, _, files in os.walk(directory):
            for f in files:
                if os.path.splitext(f)[1].lower() in self.SUPPORTED_EXTS:
                    self.playlist.append(os.path.join(root, f))
        return bool(self.playlist)

    def convert_to_wav(self, src, show_progress=False):
        if not self.ffmpeg:
            return None
        wav = os.path.splitext(src)[0] + '.wav'
        cmd = [self.ffmpeg, '-y', '-i', src, '-vn',
               '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2', wav]
        if show_progress:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                if 'time=' in line:
                    print(line.strip(), end='\r')
            proc.wait()
        else:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return wav if os.path.exists(wav) else None

    def play_file(self, file_path=None):
        if file_path and file_path in self.playlist:
            self.current_index = self.playlist.index(file_path)
        path = self.playlist[self.current_index]
        self.stop()
        ext = os.path.splitext(path)[1].lower()
        if ext not in self.PLAYABLE_EXTS:
            if self.ffmpeg:
                print(Fore.YELLOW + f"Converting {ext} → .wav, please wait..." + Style.RESET_ALL)
                wav = self.convert_to_wav(path, show_progress=True)
                if wav:
                    path = wav
                else:
                    print(Fore.RED + "Conversion failed – skipping track." + Style.RESET_ALL)
                    time.sleep(1)
                    return
            else:
                print(Fore.RED + "ffmpeg missing: can't convert this format!" + Style.RESET_ALL)
                time.sleep(1)
                return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()
            self.playing = True
            self.paused = False
        except Exception as e:
            print(f"Error playing {path}: {e}")
            time.sleep(1)

    def stop(self):
        pygame.mixer.music.stop()
        self.playing = False
        self.paused = False

    def next_track(self):
        self.stop()
        self.current_index = (self.current_index + 1) % len(self.playlist)
        self.play_file()

    def prev_track(self):
        self.stop()
        self.current_index = (self.current_index - 1) % len(self.playlist)
        self.play_file()

    def change_volume(self, d):
        self.volume = max(0, min(1, self.volume + d))
        pygame.mixer.music.set_volume(self.volume)

    def toggle_mute(self):
        if self.volume > 0:
            self.prev_volume = self.volume
            self.change_volume(-self.volume)
        else:
            self.change_volume(self.prev_volume)

    def seek(self, seconds):
        if not self.playing or not self.playlist:
            return
        pos = pygame.mixer.music.get_pos() / 1000
        new_pos = max(0, pos + seconds)
        path = self.playlist[self.current_index]
        try:
            pygame.mixer.music.load(path)
            # pygame 2.1+ supports start parameter
            pygame.mixer.music.play(start=new_pos)
            pygame.mixer.music.set_volume(self.volume)
            if self.paused:
                pygame.mixer.music.pause()
        except Exception as e:
            print(f"Seek failed: {e}")

    def update_visualizer(self):
        for i in range(32):
            tgt = random.randint(0, 10) if self.playing and not self.paused else 0
            self.visualizer_data[i] += (tgt - self.visualizer_data[i]) * 0.2
            self.visualizer_depth[i] += (self.visualizer_data[i] - self.visualizer_depth[i]) * 0.1

    def draw_visualizer(self):
        w, h = 32 * 3, 10
        print(Fore.WHITE + '+' + '-' * w + '+')
        for row in range(h):
            line = '|' + ''.join(
                (self.color_wave[(self.color_index + i) % len(self.color_wave)] + '██' + Style.RESET_ALL)
                if h - row <= int(self.visualizer_data[i])
                else ('▓▓' if h - row <= int(self.visualizer_depth[i]) else '  ')
                for i in range(32)
            ) + '|'
            print(line)
        print(Fore.WHITE + '+' + '-' * w + '+')
        self.color_index = (self.color_index + 1) % len(self.color_wave)

    def draw_info(self):
        clear_screen()
        print(Back.BLUE + Fore.WHITE + ' ASCII MEDIA PLAYER ' + Style.RESET_ALL)
        now = os.path.basename(self.playlist[self.current_index])
        print(Fore.CYAN + f"Now Playing: {now}")
        pos = pygame.mixer.music.get_pos() / 1000
        print(f"Time: {int(pos // 60)}:{int(pos % 60):02d}")
        vb = int(self.volume * 10)
        print('Volume: [' + '■' * vb + '-' * (10 - vb) + ']')
        self.draw_visualizer()
        print('Controls: Space Play/Pause | N Next | P Prev | ←/→ Seek ±5s | ↑/↓ Vol | M Mute | S Search | Q Quit')

    def search(self):
        self.stop()
        print('Search:')
        q = input('> ').strip()
        for i, f in enumerate(self.playlist):
            if q.lower() in os.path.basename(f).lower():
                self.current_index = i
                self.play_file()
                return
        opts = {
            'format': 'bestaudio',
            'outtmpl': '%(title)s.%(ext)s',
            'progress_hooks': [self.ydl_hook]
        }
        with youtube_dl.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch:{q}", download=True)['entries'][0]
                fname = f"{info['title']}.{info['ext']}"
                self.playlist.append(fname)
                self.current_index = len(self.playlist) - 1
                self.play_file(fname)
            except:
                print('Not found anywhere')
                time.sleep(1)

    def ydl_hook(self, d):
        if d['status'] == 'downloading':
            print(f"Downloading {d['filename']} {d['_percent_str']}", end='\r')

    def check_keyboard(self):
        if msvcrt.kbhit():
            k = msvcrt.getch()
            if k == b'\xe0':  # special keys (arrows, etc.)
                k2 = msvcrt.getch()
                if k2 == b'K':       # ←
                    self.seek(-5)
                elif k2 == b'M':     # →
                    self.seek(5)
                elif k2 == b'H':     # ↑
                    self.change_volume(0.1)
                elif k2 == b'P':     # ↓
                    self.change_volume(-0.1)
                return
            k = k.decode('utf-8', errors='ignore').lower()
        else:
            return

        if k == 'q':
            self.running = False
        elif k == ' ':
            self.pause_resume()
        elif k == 'n':
            self.next_track()
        elif k == 'p':
            self.prev_track()
        elif k in ('+', '='):
            self.change_volume(0.1)
        elif k == '-':
            self.change_volume(-0.1)
        elif k == 'm':
            self.toggle_mute()
        elif k == 's':
            self.search()

    def pause_resume(self):
        if self.paused:
            pygame.mixer.music.unpause()
            self.paused = False
        else:
            pygame.mixer.music.pause()
            self.paused = True

    def run(self):
        self.startup_animation()
        self.prompt_directory()
        while self.running:
            self.update_visualizer()
            self.draw_info()
            if self.playing and not pygame.mixer.music.get_busy() and not self.paused:
                self.next_track()
            if time.time() - self.last_key_check > 0.1:
                self.check_keyboard()
                self.last_key_check = time.time()
            time.sleep(0.05)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--convert-only', help='Directory to run converter on')
    parser.add_argument('media_dir', nargs='?')
    args = parser.parse_args()
    ASCIIMediaPlayer(
        media_dir=args.media_dir,
        convert_only=bool(args.convert_only)
    ).run()
