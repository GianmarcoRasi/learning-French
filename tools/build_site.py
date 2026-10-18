#!/usr/bin/env python3
"""Build the lessons website, to read and listen to the lessons on a phone.

Every lesson in lessons/french-italian/ and lessons/french-only/ becomes an
HTML page, and each 🎧 link to a track becomes an audio player in the text.
The audio files are copied next to the pages, with the same relative paths
as in the repository, so the links in the lessons keep working.

The site is published on GitHub Pages by .github/workflows/pages.yml.

Usage:
    python tools/build_site.py              # writes _site/
    python tools/build_site.py --out DIR
"""

import argparse
import html
import re
import shutil
from pathlib import Path

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent.parent
VERSIONS = [
    ("french-italian", "Avec la traduction"),
    ("french-only", "Seulement en français"),
]

KOFI = "https://ko-fi.com/qwark992"
SUPPORT = (
    f'<p class="support">Ce cours te plaît ? (<em>Ti piace questo corso?</em>) '
    f'<a href="{KOFI}">☕ Offre-moi un café</a> (<em>Offrimi un caffè</em>)</p>'
)

# A paragraph that is only a 🎧 link to a track, as written in the lessons.
AUDIO_LINK = re.compile(r'<p>🎧 <a href="([^"]+\.mp3)">([^<]+)</a></p>')
LESSON_LINK = re.compile(r'href="([^":]+)\.md"')

STYLE = """
:root {
  --bg: #fbfaf7; --fg: #1f2328; --muted: #656d76; --accent: #1f4fa3;
  --card: #ffffff; --line: #e3e1db; --em: #5b6470;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #15171b; --fg: #e6e6e6; --muted: #9aa0a8; --accent: #8db4ff;
    --card: #1e2127; --line: #30343c; --em: #a9b0ba;
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  font: 18px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
main { max-width: 720px; margin: 0 auto; padding: 0 16px 64px; }
a { color: var(--accent); }
em { color: var(--em); }
h1 { font-size: 1.6em; line-height: 1.25; margin: 0.6em 0 0.4em; }
h2 { font-size: 1.3em; line-height: 1.3; margin-top: 2em; }
h3 { font-size: 1.1em; line-height: 1.35; margin-top: 1.8em; }
li { margin: 0.25em 0; }
hr { border: 0; border-top: 1px solid var(--line); margin: 2em 0; }
table { border-collapse: collapse; width: 100%; display: block; overflow-x: auto; }
th, td { border: 1px solid var(--line); padding: 6px 10px; text-align: left; }
details {
  background: var(--card); border: 1px solid var(--line); border-radius: 10px;
  padding: 8px 14px; margin: 1.5em 0;
}
summary { cursor: pointer; padding: 6px 0; }
audio { display: block; width: 100%; margin: 0.6em 0 1em; }
.bar {
  position: sticky; top: 0; z-index: 1; background: var(--bg);
  border-bottom: 1px solid var(--line);
}
.bar div {
  max-width: 720px; margin: 0 auto; padding: 10px 16px;
  display: flex; gap: 12px; align-items: center; font-size: 15px;
}
.bar a { text-decoration: none; }
.bar .grow { flex: 1; }
.bar button {
  font: inherit; color: var(--fg); background: var(--card);
  border: 1px solid var(--line); border-radius: 8px; padding: 4px 10px;
}
.lessons { list-style: none; padding: 0; }
.lessons li {
  background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  padding: 14px 16px; margin: 12px 0;
}
.lessons .title { font-weight: 600; display: block; margin-bottom: 6px; }
.lessons a { display: inline-block; margin: 4px 16px 4px 0; }
.note { color: var(--muted); font-size: 15px; }
.support { margin-top: 3em; text-align: center; font-size: 15px; color: var(--muted); }
"""

# Only one track plays at a time, and the speed button sets the speed of
# every track (remembered between visits).
SCRIPT = """
const speeds = [1, 0.85, 0.7, 1.15];
const button = document.getElementById('speed');
let speed = 1;
try { speed = parseFloat(localStorage.getItem('speed')) || 1; } catch (e) {}
function applySpeed() {
  button.textContent = speed + '×';
  document.querySelectorAll('audio').forEach(a => {
    a.defaultPlaybackRate = speed; a.playbackRate = speed;
  });
}
button.addEventListener('click', () => {
  speed = speeds[(speeds.indexOf(speed) + 1) % speeds.length];
  try { localStorage.setItem('speed', speed); } catch (e) {}
  applySpeed();
});
document.addEventListener('play', e => {
  document.querySelectorAll('audio').forEach(a => { if (a !== e.target) a.pause(); });
  e.target.playbackRate = speed;
}, true);
applySpeed();
"""


def page(title, body, home, bar=""):
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#1f4fa3">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Français">
<link rel="manifest" href="{home}manifest.webmanifest">
<title>{html.escape(title)}</title>
<style>{STYLE}</style>
</head>
<body>
{bar}
<main>
{body}
</main>
</body>
</html>
"""


def lesson_title(text):
    match = re.search(r"^# (.+)$", text, re.M)
    return match.group(1) if match else ""


def render_lesson(md, text):
    body = md.render(text)
    body = AUDIO_LINK.sub(
        lambda m: f'<audio controls preload="none" src="{m.group(1)}"'
        f' title="{m.group(2)}"></audio>',
        body,
    )
    return LESSON_LINK.sub(r'href="\1.html"', body)


def build(out):
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "audio", out / "audio")

    md = MarkdownIt("commonmark", {"typographer": False}).enable("table")
    lessons = {}
    for version, _ in VERSIONS:
        for path in sorted((ROOT / "lessons" / version).glob("*.md")):
            text = path.read_text(encoding="utf-8")
            title = lesson_title(text)
            # The plain-text title, for the browser tab and the lesson list.
            plain = re.sub(r"[*_]", "", title)
            lessons.setdefault(path.stem, {})[version] = plain

            other = next(v for v, _ in VERSIONS if v != version)
            label = dict(VERSIONS)[other]
            bar = (
                '<nav class="bar"><div>'
                '<a href="../../index.html">← Leçons</a>'
                '<span class="grow"></span>'
                f'<a href="../{other}/{path.stem}.html">{label}</a>'
                '<button id="speed" type="button" aria-label="Vitesse">1×</button>'
                "</div></nav>"
            )
            body = render_lesson(md, text) + SUPPORT + f"<script>{SCRIPT}</script>"
            target = out / "lessons" / version / f"{path.stem}.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(page(plain, body, "../../", bar), encoding="utf-8")

    items = []
    for stem, titles in sorted(lessons.items()):
        name = titles.get("french-italian") or next(iter(titles.values()))
        links = "".join(
            f'<a href="lessons/{version}/{stem}.html">{label}</a>'
            for version, label in VERSIONS
            if version in titles
        )
        items.append(
            f'<li><span class="title">{html.escape(name)}</span>{links}</li>'
        )
    index = (
        "<h1>Apprendre le français</h1>"
        '<p class="note">Un cours de français pour les italiens. '
        "(<em>Un corso di francese per italiani.</em>)</p>"
        f'<ul class="lessons">{"".join(items)}</ul>'
        + SUPPORT
    )
    (out / "index.html").write_text(page("Apprendre le français", index, ""), encoding="utf-8")
    (out / "manifest.webmanifest").write_text(
        '{"name": "Apprendre le français", "short_name": "Français",'
        ' "start_url": "./index.html", "display": "standalone",'
        ' "background_color": "#fbfaf7", "theme_color": "#1f4fa3"}\n',
        encoding="utf-8",
    )
    # Serve the files as they are, without Jekyll.
    (out / ".nojekyll").write_text("")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    build(args.out)
    print(f"Site written to {args.out}")


if __name__ == "__main__":
    main()
