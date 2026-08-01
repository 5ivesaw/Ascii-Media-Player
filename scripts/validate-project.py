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


required = [
    ROOT / "app.py",
    ROOT / "requirements.txt",
    ROOT / "README.md",
    ROOT / "LICENSE",
    ROOT / ".github/workflows/pages.yml",
    ROOT / ".github/workflows/validate.yml",
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

try:
    py_compile.compile(str(ROOT / "app.py"), doraise=True)
except py_compile.PyCompileError as error:
    ERRORS.append(f"Python syntax: {error.msg}")

for path in (DOCS / "manifest.webmanifest", DOCS / "version.json"):
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        ERRORS.append(f"Invalid JSON in {path.name}: {error}")

for path in [DOCS / "sitemap.xml", *sorted((DOCS / "assets").glob("*.svg"))]:
    try:
        ElementTree.parse(path)
    except Exception as error:
        ERRORS.append(f"Invalid XML in {path.relative_to(ROOT)}: {error}")

parser = AssetParser()
parser.feed((DOCS / "index.html").read_text(encoding="utf-8"))
for duplicate in sorted({value for value in parser.ids if parser.ids.count(value) > 1}):
    ERRORS.append(f"Duplicate HTML id: {duplicate}")

for attribute, reference in parser.references:
    if reference.startswith(("http://", "https://", "#", "mailto:", "data:")):
        continue
    local = reference.split("?", 1)[0].split("#", 1)[0]
    if not local:
        continue
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

sw_text = (DOCS / "sw.js").read_text(encoding="utf-8")
for match in re.findall(r"['\"](\./[^'\"]+)['\"]", sw_text):
    relative = match[2:]
    if relative in {"", "/"}:
        continue
    check((DOCS / relative).exists(), f"Service worker asset missing: {match}")

config_text = (DOCS / "site-config.js").read_text(encoding="utf-8")
for key in ("repositoryUrl", "siteUrl"):
    match = re.search(rf"{key}:\s*['\"]([^'\"]+)", config_text)
    check(bool(match), f"site-config.js is missing {key}")
    if match:
        parsed = urlparse(match.group(1))
        check(parsed.scheme == "https" and bool(parsed.netloc), f"Invalid {key}: {match.group(1)}")

all_text = "\n".join(
    path.read_text(encoding="utf-8", errors="ignore")
    for path in ROOT.rglob("*")
    if path.is_file() and path.name != "validate-project.py" and path.suffix.lower() in {".html", ".css", ".js", ".json", ".md", ".xml", ".txt", ".yml", ".yaml", ".sh", ".py"}
)
for placeholder in ("__REPO_URL__", "__SITE_URL__", "TODO_REPLACE"):
    check(placeholder not in all_text, f"Unresolved placeholder: {placeholder}")

if ERRORS:
    for error in ERRORS:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("Validation passed")
print(f"Checked {len(required)} required files, HTML references, JSON, XML, PNG dimensions, Python syntax, and site configuration.")
