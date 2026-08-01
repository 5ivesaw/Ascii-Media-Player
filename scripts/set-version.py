#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$')


def replace(path: Path, pattern: str, replacement: str) -> None:
    text = path.read_text(encoding='utf-8')
    updated, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if count == 0:
        raise SystemExit(f'Version pattern not found in {path.relative_to(ROOT)}')
    path.write_text(updated, encoding='utf-8')


def current() -> str:
    match = re.search(r'^APP_VERSION\s*=\s*["\']([^"\']+)', (ROOT/'app.py').read_text(), re.MULTILINE)
    if not match:
        raise SystemExit('APP_VERSION not found')
    return match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('version', nargs='?')
    parser.add_argument('--print', action='store_true', dest='print_version')
    args = parser.parse_args()
    if args.print_version:
        print(current())
        return 0
    if not args.version or not SEMVER.fullmatch(args.version):
        raise SystemExit('Provide a semantic version such as 2.2.0')
    version = args.version
    major, minor, patch = map(int, version.split('.'))
    version_code = major * 1_000_000 + minor * 1_000 + patch

    replace(ROOT/'app.py', r'^APP_VERSION\s*=\s*["\'][^"\']+["\']', f'APP_VERSION = "{version}"')
    replace(ROOT/'docs/site-config.js', r"version:\s*['\"][^'\"]+['\"]", f"version: '{version}'")
    replace(ROOT/'android/app/build.gradle', r"versionCode\s+\d+", f'versionCode {version_code}')
    replace(ROOT/'android/app/build.gradle', r"versionName\s+['\"][^'\"]+['\"]", f"versionName '{version}'")

    version_json = json.loads((ROOT/'docs/version.json').read_text())
    version_json['version'] = version
    (ROOT/'docs/version.json').write_text(json.dumps(version_json, indent=2) + '\n')

    index = (ROOT/'docs/index.html').read_text()
    index = re.sub(r'VERSION\s+\d+\.\d+\.\d+', f'VERSION {version}', index)
    index = re.sub(r'Version\s+\d+\.\d+\.\d+', f'Version {version}', index)
    index = re.sub(r'>v\d+\.\d+<', f'>v{major}.{minor}<', index)
    (ROOT/'docs/index.html').write_text(index)

    readme = (ROOT/'README.md').read_text()
    readme = re.sub(r'## Version \d+\.\d+', f'## Version {major}.{minor}', readme)
    (ROOT/'README.md').write_text(readme)
    print(version)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
