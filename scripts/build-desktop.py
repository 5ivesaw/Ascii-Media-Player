#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def app_version() -> str:
    match = re.search(r'^APP_VERSION\s*=\s*["\']([^"\']+)', (ROOT / 'app.py').read_text(encoding='utf-8'), re.MULTILINE)
    if not match:
        raise SystemExit('APP_VERSION was not found in app.py')
    return match.group(1)


def run_pyinstaller() -> Path:
    dist = ROOT / 'dist'
    build = ROOT / 'build'
    for path in (dist, build):
        if path.exists():
            shutil.rmtree(path)
    command = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm', '--clean', '--onefile', '--noupx',
        '--name', 'ASCII-Media-Player',
        '--collect-all', 'pygame',
        '--collect-all', 'pyfiglet',
        '--collect-all', 'mutagen',
        '--collect-all', 'yt_dlp',
        str(ROOT / 'app.py'),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    suffix = '.exe' if os.name == 'nt' else ''
    binary = dist / f'ASCII-Media-Player{suffix}'
    if not binary.exists():
        raise SystemExit(f'PyInstaller output was not found: {binary}')
    return binary


def zip_add(zf: zipfile.ZipFile, path: Path, arcname: str, executable: bool = False) -> None:
    info = zipfile.ZipInfo.from_file(path, arcname)
    mode = 0o755 if executable else 0o644
    info.external_attr = (stat.S_IFREG | mode) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    with path.open('rb') as handle:
        zf.writestr(info, handle.read())


def package(binary: Path, platform: str, arch: str) -> list[Path]:
    version = app_version()
    output = ROOT / 'release-assets'
    output.mkdir(exist_ok=True)
    created: list[Path] = []

    if platform == 'windows':
        exe_name = f'ASCII-Media-Player-v{version}-Windows-{arch}.exe'
        exe_path = output / exe_name
        shutil.copy2(binary, exe_path)
        archive = output / f'ASCII-Media-Player-v{version}-Windows-{arch}.zip'
        readme = ROOT / 'packaging/README-WINDOWS.txt'
        launcher = ROOT / 'packaging/RUN-ASCII-MEDIA-PLAYER.cmd'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zf:
            zip_add(zf, exe_path, exe_name)
            zip_add(zf, readme, 'README-WINDOWS.txt')
            zip_add(zf, launcher, 'RUN-ASCII-MEDIA-PLAYER.cmd')
            zip_add(zf, ROOT / 'LICENSE', 'LICENSE')
        created.extend([exe_path, archive])

    elif platform == 'linux':
        label = 'x64' if arch == 'x64' else 'arm64'
        raw_name = f'ASCII-Media-Player-v{version}-Linux-{label}'
        raw_path = output / raw_name
        shutil.copy2(binary, raw_path)
        raw_path.chmod(0o755)
        archive = output / f'{raw_name}.tar.gz'
        with tempfile.TemporaryDirectory() as temp:
            package_root = Path(temp) / f'ASCII-Media-Player-v{version}-Linux-{label}'
            package_root.mkdir()
            app_target = package_root / 'ascii-media-player'
            shutil.copy2(binary, app_target)
            app_target.chmod(0o755)
            shutil.copy2(ROOT / 'packaging/README-LINUX.txt', package_root / 'README-LINUX.txt')
            shutil.copy2(ROOT / 'packaging/install-local-linux.sh', package_root / 'install.sh')
            (package_root / 'install.sh').chmod(0o755)
            shutil.copy2(ROOT / 'LICENSE', package_root / 'LICENSE')
            with tarfile.open(archive, 'w:gz') as tf:
                tf.add(package_root, arcname=package_root.name)
        created.extend([raw_path, archive])

    elif platform == 'macos':
        label = 'Apple-Silicon' if arch == 'arm64' else 'Intel'
        archive = output / f'ASCII-Media-Player-v{version}-macOS-{label}.zip'
        readme = ROOT / 'packaging/README-MACOS.txt'
        launcher_source = ROOT / 'packaging/ASCII Media Player.command'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zf:
            zip_add(zf, binary, 'ascii-media-player', executable=True)
            zip_add(zf, launcher_source, 'ASCII Media Player.command', executable=True)
            zip_add(zf, readme, 'README-MACOS.txt')
            zip_add(zf, ROOT / 'LICENSE', 'LICENSE')
        created.append(archive)
    else:
        raise SystemExit(f'Unsupported platform: {platform}')

    return created


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', choices=['windows', 'linux', 'macos'], required=True)
    parser.add_argument('--arch', choices=['x64', 'arm64'], required=True)
    args = parser.parse_args()
    binary = run_pyinstaller()
    subprocess.run([str(binary), '--version'], cwd=ROOT, check=True)
    for path in package(binary, args.platform, args.arch):
        print(path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
