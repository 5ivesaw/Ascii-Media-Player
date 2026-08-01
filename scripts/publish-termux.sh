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

for tool in git python3 gh; do
  command -v "$tool" >/dev/null 2>&1 || fail "$tool is required. In Termux run: pkg install git python nodejs gh"
done

if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  say "GitHub CLI needs a one-time browser login"
  gh auth login --hostname github.com --git-protocol https --web
fi
gh auth setup-git >/dev/null 2>&1 || true

say "Cloning the current repository"
git clone "$REPO_URL" "$WORK_DIR/repository"
cd "$WORK_DIR/repository"
if git show-ref --verify --quiet refs/remotes/origin/main; then
  git switch -C main --track origin/main
elif git show-ref --verify --quiet refs/heads/main; then
  git switch main
else
  fail "The repository does not contain a main branch"
fi
git pull --ff-only origin main

say "Applying the FiveSaw v2.2.1 release upgrade"
find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
(
  cd "$SOURCE_DIR"
  tar \
    --exclude='./.git' \
    --exclude='./build' \
    --exclude='./dist' \
    --exclude='./release-assets' \
    --exclude='./__pycache__' \
    --exclude='*/__pycache__' \
    -cf - .
) | tar -xf -
rm -rf build dist release-assets .site-info.json

bash scripts/configure-site.sh "$REPO_URL"
python3 scripts/validate-project.py
if command -v node >/dev/null 2>&1; then
  node --check docs/player.js
  node --check docs/sw.js
fi

if ! git config user.name >/dev/null; then git config user.name "FiveSaw"; fi
if ! git config user.email >/dev/null; then git config user.email "150168566+5ivesaw@users.noreply.github.com"; fi

VERSION="$(python3 scripts/set-version.py --print)"
TAG="v$VERSION"
SITE_URL="$(python3 -c 'import json; print(json.load(open(".site-info.json"))["site_url"])')"
SLUG="$(python3 -c 'import json; print(json.load(open(".site-info.json"))["slug"])')"
rm -f .site-info.json

say "Creating or restoring stable Android signing secrets"
SIGN_DIR="$HOME/.config/ascii-media-player/signing"
ENV_FILE="$SIGN_DIR/android-signing.env"
mkdir -p "$SIGN_DIR"
chmod 700 "$SIGN_DIR"
if [[ ! -f "$ENV_FILE" || ! -f "$SIGN_DIR/release.jks" ]]; then
  if ! command -v keytool >/dev/null 2>&1 || ! command -v openssl >/dev/null 2>&1; then
    pkg install -y openjdk-21 openssl-tool
  fi
  STORE_PASSWORD="$(openssl rand -hex 24)"
  KEY_PASSWORD="$(openssl rand -hex 24)"
  KEY_ALIAS="ascii-media-player"
  keytool -genkeypair -noprompt \
    -keystore "$SIGN_DIR/release.jks" \
    -storepass "$STORE_PASSWORD" \
    -keypass "$KEY_PASSWORD" \
    -alias "$KEY_ALIAS" \
    -keyalg RSA -keysize 4096 -validity 10000 \
    -dname "CN=ASCII Media Player, OU=Release, O=FiveSaw, L=Maharagama, C=LK"
  cat > "$ENV_FILE" <<EOF
ANDROID_STORE_PASSWORD='$STORE_PASSWORD'
ANDROID_KEY_PASSWORD='$KEY_PASSWORD'
ANDROID_KEY_ALIAS='$KEY_ALIAS'
EOF
  chmod 600 "$ENV_FILE" "$SIGN_DIR/release.jks"
fi
# shellcheck disable=SC1090
source "$ENV_FILE"
KEYSTORE_BASE64="$(base64 "$SIGN_DIR/release.jks" | tr -d '\r\n')"
printf '%s' "$KEYSTORE_BASE64" | gh secret set ANDROID_KEYSTORE_BASE64 --repo "$SLUG"
printf '%s' "$ANDROID_STORE_PASSWORD" | gh secret set ANDROID_STORE_PASSWORD --repo "$SLUG"
printf '%s' "$ANDROID_KEY_PASSWORD" | gh secret set ANDROID_KEY_PASSWORD --repo "$SLUG"
printf '%s' "$ANDROID_KEY_ALIAS" | gh secret set ANDROID_KEY_ALIAS --repo "$SLUG"

# Allow the release workflow to publish release assets. This is best-effort because
# repository-level policy can be controlled separately by GitHub.
gh api --method PUT "repos/$SLUG/actions/permissions/workflow" \
  -f default_workflow_permissions=write \
  -F can_approve_pull_request_reviews=false >/dev/null 2>&1 || true

say "Committing and pushing main"
git add -A
if git diff --cached --quiet; then
  say "Main already contains this upgrade"
else
  git commit -m "Add cross-platform release pipeline v$VERSION"
  git push origin main
fi
HEAD_SHA="$(git rev-parse HEAD)"

say "Enabling GitHub Pages and setting the repository website"
if gh api "repos/$SLUG/pages" >/dev/null 2>&1; then
  printf '%s' '{"build_type":"workflow"}' | gh api --method PUT "repos/$SLUG/pages" --input - >/dev/null 2>&1 || true
else
  printf '%s' '{"build_type":"workflow"}' | gh api --method POST "repos/$SLUG/pages" --input - >/dev/null 2>&1 || true
fi
gh api --method PATCH "repos/$SLUG" \
  -f homepage="$SITE_URL" \
  -f description="Cross-platform local audio player with live ASCII visualization and automated releases." >/dev/null || true

say "Publishing release tag $TAG"
if git ls-remote --exit-code --tags origin "refs/tags/$TAG" >/dev/null 2>&1; then
  REMOTE_TAG_SHA="$(git ls-remote --tags origin "refs/tags/$TAG^{}" | awk '{print $1}')"
  [[ -n "$REMOTE_TAG_SHA" ]] || REMOTE_TAG_SHA="$(git ls-remote --tags origin "refs/tags/$TAG" | awk '{print $1}')"
  if [[ "$REMOTE_TAG_SHA" != "$HEAD_SHA" ]]; then
    fail "Tag $TAG already exists on another commit. Increase the version and retry."
  fi
  gh workflow run release.yml --repo "$SLUG" -f tag="$TAG"
else
  git tag -a "$TAG" -m "ASCII Media Player $TAG"
  git push origin "$TAG"
fi

say "Waiting for the release workflow"
sleep 6
RUN_ID="$(gh run list --repo "$SLUG" --workflow release.yml --limit 8 --json databaseId,headBranch,event --jq '.[] | select(.headBranch == "'"$TAG"'" or .event == "workflow_dispatch") | .databaseId' | head -n 1)"
if [[ -n "$RUN_ID" && "$RUN_ID" != "null" ]]; then
  if ! gh run watch "$RUN_ID" --repo "$SLUG" --exit-status; then
    echo
    echo "Release build failed. Showing failed job logs:"
    gh run view "$RUN_ID" --repo "$SLUG" --log-failed || true
    exit 1
  fi
else
  echo "The run has not appeared yet. Open: https://github.com/$SLUG/actions/workflows/release.yml"
fi

say "Finished"
echo "Repository: https://github.com/$SLUG"
echo "Website:    $SITE_URL"
echo "Release:    https://github.com/$SLUG/releases/tag/$TAG"
echo "Signing:    $SIGN_DIR"
if command -v termux-open-url >/dev/null 2>&1; then
  termux-open-url "https://github.com/$SLUG/releases/tag/$TAG" >/dev/null 2>&1 || true
fi
