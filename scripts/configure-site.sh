#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_INPUT="${1:-}"
SITE_INPUT="${2:-}"

if [[ -z "$REPOSITORY_INPUT" ]] && git -C "$ROOT_DIR" remote get-url origin >/dev/null 2>&1; then
  REPOSITORY_INPUT="$(git -C "$ROOT_DIR" remote get-url origin)"
fi

if [[ -z "$REPOSITORY_INPUT" ]]; then
  REPOSITORY_INPUT="https://github.com/5ivesaw/Ascii-Media-Player.git"
fi

python3 - "$ROOT_DIR" "$REPOSITORY_INPUT" "$SITE_INPUT" <<'PY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

root = Path(sys.argv[1]).resolve()
remote = sys.argv[2].strip()
requested_site = sys.argv[3].strip()


def parse_repository(value: str) -> tuple[str, str]:
    value = value.strip().rstrip('/')
    if value.startswith('git@github.com:'):
        path = value.split(':', 1)[1]
    elif value.startswith('ssh://git@github.com/'):
        path = value.split('github.com/', 1)[1]
    elif value.startswith('http://') or value.startswith('https://'):
        parsed = urlparse(value)
        if parsed.hostname not in {'github.com', 'www.github.com'}:
            raise SystemExit(f'Only github.com repositories are supported: {value}')
        path = parsed.path.lstrip('/')
    elif '/' in value and '://' not in value:
        path = value
    else:
        raise SystemExit(f'Could not parse GitHub repository: {value}')

    path = re.sub(r'\.git$', '', path).strip('/')
    parts = path.split('/')
    if len(parts) != 2 or not all(parts):
        raise SystemExit(f'Expected OWNER/REPOSITORY, got: {path}')
    return parts[0], parts[1]


owner, repository = parse_repository(remote)
repo_url = f'https://github.com/{owner}/{repository}'
if requested_site:
    site_url = requested_site.rstrip('/') + '/'
elif repository.lower() == f'{owner.lower()}.github.io':
    site_url = f'https://{owner.lower()}.github.io/'
else:
    site_url = f'https://{owner.lower()}.github.io/{repository}/'

config_path = root / 'docs' / 'site-config.js'
old_repo = 'https://github.com/5ivesaw/Ascii-Media-Player'
old_site = 'https://5ivesaw.github.io/Ascii-Media-Player/'
if config_path.exists():
    existing = config_path.read_text(encoding='utf-8')
    repo_match = re.search(r"repositoryUrl:\s*['\"]([^'\"]+)", existing)
    site_match = re.search(r"siteUrl:\s*['\"]([^'\"]+)", existing)
    if repo_match:
        old_repo = repo_match.group(1).rstrip('/')
    if site_match:
        old_site = site_match.group(1).rstrip('/') + '/'

config_path.write_text(
    "window.ASCII_MEDIA_PLAYER_CONFIG = Object.freeze({\n"
    "  version: '2.1.0',\n"
    f"  repositoryUrl: {repo_url!r},\n"
    f"  siteUrl: {site_url!r}\n"
    "});\n",
    encoding='utf-8',
)

text_files = [
    root / 'README.md',
    root / 'docs' / 'index.html',
    root / 'docs' / '404.html',
    root / 'docs' / 'robots.txt',
    root / 'docs' / 'sitemap.xml',
]

for path in text_files:
    text = path.read_text(encoding='utf-8')
    text = text.replace(old_repo, repo_url)
    text = text.replace(old_site, site_url)
    # Also normalize the package defaults if an earlier configuration was incomplete.
    text = text.replace('https://github.com/5ivesaw/Ascii-Media-Player', repo_url)
    text = text.replace('https://5ivesaw.github.io/Ascii-Media-Player/', site_url)
    path.write_text(text, encoding='utf-8')

# Ensure managed README reference definitions are deterministic.
readme_path = root / 'README.md'
readme = readme_path.read_text(encoding='utf-8')
readme = re.sub(r'^\[repository\]:\s*.*$', f'[repository]: {repo_url}', readme, flags=re.MULTILINE)
readme = re.sub(r'^\[site\]:\s*.*$', f'[site]: {site_url}', readme, flags=re.MULTILINE)
readme_path.write_text(readme, encoding='utf-8')

info = {
    'owner': owner,
    'repository': repository,
    'slug': f'{owner}/{repository}',
    'repository_url': repo_url,
    'clone_url': f'{repo_url}.git',
    'site_url': site_url,
}
(root / '.site-info.json').write_text(json.dumps(info, indent=2) + '\n', encoding='utf-8')

print(f'Repository: {repo_url}')
print(f'Pages URL:  {site_url}')
PY
