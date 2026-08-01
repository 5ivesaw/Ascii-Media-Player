from __future__ import annotations

import json
import py_compile
import re
import struct
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ERRORS: list[str] = []


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[tuple[str, str]] = []
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"] or "")
        for attribute in ("src", "href"):
            value = values.get(attribute)
            if value:
                self.references.append((attribute, value))


def check(condition: bool, message: str) -> None:
    if not condition:
        ERRORS.append(message)


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    return struct.unpack(">II", data[16:24])


def read_version() -> str:
    text = (ROOT / "app.py").read_text(encoding="utf-8")
    match = re.search(r'^APP_VERSION\s*=\s*["\']([^"\']+)', text, re.MULTILINE)
    if not match:
        raise ValueError("APP_VERSION was not found")
    return match.group(1)


required = [
    ROOT / "app.py",
    ROOT / "requirements.txt",
    ROOT / "README.md",
    ROOT / "LICENSE",
    ROOT / ".github/workflows/pages.yml",
    ROOT / ".github/workflows/release.yml",
    ROOT / ".github/workflows/validate.yml",
    ROOT / "scripts/build-desktop.py",
    ROOT / "scripts/configure-site.sh",
    ROOT / "scripts/install-linux.sh",
    ROOT / "scripts/install-macos.sh",
    ROOT / "scripts/install-windows.ps1",
    ROOT / "scripts/publish-termux.sh",
    ROOT / "scripts/release-termux.sh",
    ROOT / "scripts/set-version.py",
    ROOT / "packaging/README-WINDOWS.txt",
    ROOT / "packaging/README-LINUX.txt",
    ROOT / "packaging/README-MACOS.txt",
    ROOT / "packaging/RUN-ASCII-MEDIA-PLAYER.cmd",
    ROOT / "packaging/install-local-linux.sh",
    ROOT / "packaging/ASCII Media Player.command",
    ROOT / "android/settings.gradle",
    ROOT / "android/build.gradle",
    ROOT / "android/gradle.properties",
    ROOT / "android/app/build.gradle",
    ROOT / "android/app/src/main/AndroidManifest.xml",
    ROOT / "android/app/src/main/java/lol/goat/asciimediaplayer/MainActivity.java",
    ROOT / "android/app/src/main/res/values/strings.xml",
    ROOT / "android/app/src/main/res/values/styles.xml",
    DOCS / "index.html",
    DOCS / "404.html",
    DOCS / "styles.css",
    DOCS / "player.js",
    DOCS / "site-config.js",
    DOCS / "sw.js",
    DOCS / "manifest.webmanifest",
    DOCS / "version.json",
    DOCS / "robots.txt",
    DOCS / "sitemap.xml",
    DOCS / ".nojekyll",
    DOCS / "assets/logo.svg",
    DOCS / "assets/wordmark.svg",
    DOCS / "assets/terminal-frame.svg",
    DOCS / "assets/og-card.svg",
    DOCS / "assets/og-card.png",
    DOCS / "assets/icon-192.png",
    DOCS / "assets/icon-512.png",
    DOCS / "assets/maskable-512.png",
]
for path in required:
    check(path.exists(), f"Missing required file: {path.relative_to(ROOT)}")

if ERRORS:
    for error in ERRORS:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

for script in (ROOT / "app.py", ROOT / "scripts/build-desktop.py", ROOT / "scripts/set-version.py"):
    try:
        py_compile.compile(str(script), doraise=True)
    except py_compile.PyCompileError as error:
        ERRORS.append(f"Python syntax in {script.relative_to(ROOT)}: {error.msg}")

for path in (DOCS / "manifest.webmanifest", DOCS / "version.json"):
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        ERRORS.append(f"Invalid JSON in {path.name}: {error}")

xml_files = [
    DOCS / "sitemap.xml",
    ROOT / "android/app/src/main/AndroidManifest.xml",
    ROOT / "android/app/src/main/res/values/strings.xml",
    ROOT / "android/app/src/main/res/values/colors.xml",
    ROOT / "android/app/src/main/res/values/styles.xml",
    *sorted((DOCS / "assets").glob("*.svg")),
]
for path in xml_files:
    try:
        ElementTree.parse(path)
    except Exception as error:
        ERRORS.append(f"Invalid XML in {path.relative_to(ROOT)}: {error}")

parser = AssetParser()
parser.feed((DOCS / "index.html").read_text(encoding="utf-8"))
for duplicate in sorted({value for value in parser.ids if parser.ids.count(value) > 1}):
    ERRORS.append(f"Duplicate HTML id: {duplicate}")
for required_id in (
    "player", "platforms", "downloads", "install", "downloadWindows",
    "downloadAndroid", "downloadLinux", "downloadMacArm", "downloadMacIntel",
    "recommendedDownload", "heroDownload",
):
    check(required_id in parser.ids, f"Missing required HTML id: {required_id}")

for attribute, reference in parser.references:
    if reference.startswith(("http://", "https://", "#", "mailto:", "data:")):
        continue
    local = reference.split("?", 1)[0].split("#", 1)[0]
    if local:
        check((DOCS / local).exists(), f"Broken local {attribute} reference: {reference}")

manifest = json.loads((DOCS / "manifest.webmanifest").read_text(encoding="utf-8"))
for icon in manifest.get("icons", []):
    check((DOCS / icon["src"]).exists(), f"Manifest icon missing: {icon['src']}")

expected_pngs = {
    "icon-192.png": (192, 192),
    "icon-512.png": (512, 512),
    "maskable-512.png": (512, 512),
    "og-card.png": (1200, 630),
}
for name, expected in expected_pngs.items():
    try:
        actual = png_dimensions(DOCS / "assets" / name)
        check(actual == expected, f"{name} is {actual}, expected {expected}")
    except Exception as error:
        ERRORS.append(f"Invalid PNG {name}: {error}")

for folder, expected in {
    "mipmap-mdpi": (48, 48),
    "mipmap-hdpi": (72, 72),
    "mipmap-xhdpi": (96, 96),
    "mipmap-xxhdpi": (144, 144),
    "mipmap-xxxhdpi": (192, 192),
}.items():
    for icon_name in ("ic_launcher.png", "ic_launcher_round.png"):
        icon = ROOT / "android/app/src/main/res" / folder / icon_name
        check(icon.exists(), f"Missing Android icon: {icon.relative_to(ROOT)}")
        if icon.exists():
            try:
                check(png_dimensions(icon) == expected, f"Wrong Android icon size: {icon.relative_to(ROOT)}")
            except Exception as error:
                ERRORS.append(f"Invalid Android PNG {icon.relative_to(ROOT)}: {error}")

sw_text = (DOCS / "sw.js").read_text(encoding="utf-8")
for match in re.findall(r"['\"](\./[^'\"]+)['\"]", sw_text):
    relative = match[2:]
    if relative not in {"", "/"}:
        check((DOCS / relative).exists(), f"Service worker asset missing: {match}")

config_text = (DOCS / "site-config.js").read_text(encoding="utf-8")
for key in ("repositoryUrl", "siteUrl"):
    match = re.search(rf"{key}:\s*['\"]([^'\"]+)", config_text)
    check(bool(match), f"site-config.js is missing {key}")
    if match:
        parsed = urlparse(match.group(1))
        check(parsed.scheme == "https" and bool(parsed.netloc), f"Invalid {key}: {match.group(1)}")

try:
    version = read_version()
    check(re.fullmatch(r"\d+\.\d+\.\d+", version) is not None, f"Invalid semantic version: {version}")
    version_json = json.loads((DOCS / "version.json").read_text())
    check(version_json.get("version") == version, "docs/version.json does not match APP_VERSION")
    config_version = re.search(r"version:\s*['\"]([^'\"]+)", config_text)
    check(bool(config_version) and config_version.group(1) == version, "site-config.js version does not match APP_VERSION")
    android_gradle = (ROOT / "android/app/build.gradle").read_text()
    android_version = re.search(r"versionName\s+['\"]([^'\"]+)", android_gradle)
    check(bool(android_version) and android_version.group(1) == version, "Android versionName does not match APP_VERSION")
    major, minor, patch = map(int, version.split("."))
    expected_code = major * 1_000_000 + minor * 1_000 + patch
    code_match = re.search(r"versionCode\s+(\d+)", android_gradle)
    check(bool(code_match) and int(code_match.group(1)) == expected_code, "Android versionCode is not derived from APP_VERSION")
except Exception as error:
    ERRORS.append(f"Version consistency check failed: {error}")

release_workflow = (ROOT / ".github/workflows/release.yml").read_text()
for needle in (
    "windows-2025", "ubuntu-22.04", "ubuntu-22.04-arm", "macos-15-intel", "macos-15",
    "assembleRelease", "gh release create", "SHA256SUMS.txt", "actions/upload-artifact@v7",
):
    check(needle in release_workflow, f"Release workflow is missing: {needle}")

main_activity = (ROOT / "android/app/src/main/java/lol/goat/asciimediaplayer/MainActivity.java").read_text()
for needle in ("onShowFileChooser", "file:///android_asset/index.html", "setJavaScriptEnabled(true)", "onShowCustomView"):
    check(needle in main_activity, f"Android wrapper is missing: {needle}")

all_text = "\n".join(
    path.read_text(encoding="utf-8", errors="ignore")
    for path in ROOT.rglob("*")
    if path.is_file()
    and "__pycache__" not in path.parts
    and path.name != "validate-project.py"
    and path.suffix.lower() in {".html", ".css", ".js", ".json", ".md", ".xml", ".txt", ".yml", ".yaml", ".sh", ".py", ".gradle", ".java", ".ps1", ".cmd"}
)
for placeholder in ("__REPO_URL__", "__SITE_URL__", "TODO_REPLACE"):
    check(placeholder not in all_text, f"Unresolved placeholder: {placeholder}")

if ERRORS:
    for error in ERRORS:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("Validation passed")
print(f"Checked {len(required)} required files, release targets, Android wrapper, website assets, versions, JSON, XML, PNG dimensions, and Python syntax.")
