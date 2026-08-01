#!/usr/bin/env bash
set -euo pipefail

DEFAULT_REPO="https://github.com/5ivesaw/Ascii-Media-Player.git"
REPO_URL="${1:-$DEFAULT_REPO}"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$(mktemp -d)"
KEEP_WORK="${KEEP_WORK:-0}"

cleanup() {
  if [[ "$KEEP_WORK" == "1" ]]; then
    echo "Temporary repository kept at: $WORK_DIR/repository"
  else
    rm -rf "$WORK_DIR"
  fi
}
trap cleanup EXIT

say() { printf '\n[%s] %s\n' "ASCII" "$*"; }
fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

command -v git >/dev/null 2>&1 || fail "git is required. In Termux run: pkg install git"
command -v python3 >/dev/null 2>&1 || fail "python is required. In Termux run: pkg install python"

if command -v gh >/dev/null 2>&1; then
  if ! gh auth status --hostname github.com >/dev/null 2>&1; then
    say "GitHub CLI needs a one-time login to enable Pages and update the repository website field."
    gh auth login --hostname github.com --git-protocol https --web
  fi
  gh auth setup-git >/dev/null 2>&1 || true
fi

say "Cloning the current repository"
git clone "$REPO_URL" "$WORK_DIR/repository"
cd "$WORK_DIR/repository"

if git show-ref --verify --quiet refs/heads/main; then
  git switch main
elif git show-ref --verify --quiet refs/remotes/origin/main; then
  git switch -c main --track origin/main
else
  fail "The repository does not contain a main branch."
fi

git pull --ff-only origin main

say "Replacing project files with the v2.1 upgrade"
find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -a "$SOURCE_DIR"/. .
rm -f .site-info.json

say "Detecting repository and configuring the live site URL"
bash scripts/configure-site.sh "$REPO_URL"

say "Validating the project"
python3 scripts/validate-project.py
if command -v node >/dev/null 2>&1; then
  node --check docs/player.js
  node --check docs/sw.js
else
  echo "Node.js is not installed; JavaScript syntax will also be checked by GitHub Actions."
fi

if ! git config user.name >/dev/null; then
  git config user.name "FiveSaw"
fi
if ! git config user.email >/dev/null; then
  git config user.email "150168566+5ivesaw@users.noreply.github.com"
fi

SITE_URL="$(python3 -c 'import json; print(json.load(open(".site-info.json"))["site_url"])')"
SLUG="$(python3 -c 'import json; print(json.load(open(".site-info.json"))["slug"])')"

# This generated file is useful locally but does not belong in the repository.
rm -f .site-info.json

git add -A
if git diff --cached --quiet; then
  say "The repository already matches this upgrade"
  CHANGED=0
else
  git commit -m "Upgrade ASCII Media Player site to v2.1"
  say "Pushing main"
  git push origin main
  CHANGED=1
fi

if command -v gh >/dev/null 2>&1 && gh auth status --hostname github.com >/dev/null 2>&1; then
  say "Enabling GitHub Pages with the Actions workflow"
  if gh api "repos/$SLUG/pages" >/dev/null 2>&1; then
    printf '%s' '{"build_type":"workflow","https_enforced":true}' | gh api --method PUT "repos/$SLUG/pages" --input - >/dev/null || true
  else
    printf '%s' '{"build_type":"workflow"}' | gh api --method POST "repos/$SLUG/pages" --input - >/dev/null || true
  fi

  say "Updating the repository website field"
  gh api --method PATCH "repos/$SLUG" \
    -f homepage="$SITE_URL" \
    -f description="Local-first terminal and browser audio player with a live ASCII visualizer." >/dev/null || \
    echo "Repository metadata update was denied, but the code push and Pages workflow are unaffected."

  if [[ "$CHANGED" == "0" ]]; then
    gh workflow run pages.yml --repo "$SLUG" >/dev/null 2>&1 || true
  fi

  say "Waiting for the Pages deployment"
  sleep 4
  RUN_ID="$(gh run list --repo "$SLUG" --workflow pages.yml --limit 1 --json databaseId --jq '.[0].databaseId' 2>/dev/null || true)"
  if [[ -n "$RUN_ID" && "$RUN_ID" != "null" ]]; then
    gh run watch "$RUN_ID" --repo "$SLUG" --exit-status || true
  else
    echo "The workflow has not appeared yet. It will still run automatically from the push."
  fi
else
  echo
  echo "GitHub CLI is unavailable, so Pages settings and the repository website field were not changed through the API."
  echo "The committed Pages workflow will deploy automatically if Pages is already enabled."
fi

say "Finished"
echo "Repository: https://github.com/$SLUG"
echo "Website:    $SITE_URL"
if command -v termux-open-url >/dev/null 2>&1; then
  termux-open-url "$SITE_URL" >/dev/null 2>&1 || true
fi
