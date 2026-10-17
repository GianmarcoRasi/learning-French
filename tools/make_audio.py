#!/usr/bin/env python3
"""Generate the audio tracks of the lessons.

Each lesson marks the parts to be read aloud with HTML comments:

    <!-- audio:repeat 01-salutations -->
    ...
    <!-- /audio -->

    <!-- audio:listen 06-au-cafe | Léa=f; Tom=m -->
    ...
    <!-- /audio -->

Inside a block, **bold** text is French, *(italic in parentheses)* is the
Italian translation, and any other text is Italian.

- `repeat` blocks are read in order. A list item of the form
  `**French** (*Italiano*) notes` is a drill: French, Italian, notes,
  "Ripeti", French again, then a pause long enough to repeat.
- `listen` blocks are played twice: first the French only, then line by line
  with the Italian translation. A list item may start with a speaker label
  (`Léa: **...** (*...*)`); speakers get a female (f) or male (m) voice as
  declared after the `|`.

Each block becomes audio/<lesson>/<name>.mp3.

Usage:
    python tools/make_audio.py                     # all lessons
    python tools/make_audio.py lessons/01-bonjour.md
    python tools/make_audio.py --dry-run lessons/01-bonjour.md
"""

import argparse
import asyncio
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".audio-cache"

NARRATOR = "it-IT-ElsaNeural"
FRENCH = "fr-FR-DeniseNeural"
SPEAKER_VOICES = {
    "f": ["fr-FR-DeniseNeural", "fr-FR-VivienneMultilingualNeural"],
    "m": ["fr-FR-HenriNeural", "fr-FR-RemyMultilingualNeural"],
}

FRENCH_RATE = "-10%"      # drills and dialogues, slightly slower than normal
ECHO_RATE = "-20%"        # the French repeated right before the pause
ITALIAN_RATE = "+0%"

REPEAT_FACTOR = 1.6       # pause = this × length of the French + REPEAT_EXTRA
REPEAT_EXTRA = 1.5
REPEAT_MIN = 3.0

SAMPLE_RATE = 24000

BLOCK_RE = re.compile(
    r"<!--\s*audio:(?P<mode>repeat|listen)\s+(?P<name>[\w-]+)\s*(?:\|(?P<voices>.*?))?-->"
    r"(?P<body>.*?)<!--\s*/audio\s*-->",
    re.S,
)
HEADING_RE = re.compile(r"^#+\s*(?P<fr>.+?)\s*\(\*(?P<it>.+?)\*\)\s*$")
ITEM_RE = re.compile(
    r"^(?:(?P<speaker>[^*:]+?)\s*:\s*)?\*\*(?P<fr>.+?)\*\*\s*\(\*(?P<it>.+?)\*\)(?P<rest>.*)$"
)
INLINE_RE = re.compile(r"\*\*(?P<fr>.+?)\*\*|\(\*(?P<it>.+?)\*\)|`(?P<code>[^`]+)`")
LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
SYMBOL_RE = re.compile("[\U0001F000-\U0001FFFF☀-➿️]")


# ---------------------------------------------------------------- parsing

def clean(text):
    text = LINK_RE.sub(r"\1", text)
    text = SYMBOL_RE.sub("", text)
    text = text.replace("*", "").replace("_", " ")
    return " ".join(text.split())


def spoken(text):
    """True if the text has something to pronounce, not just punctuation."""
    return any(c.isalnum() for c in text)


def segments(text):
    """Split a line of markdown into (lang, text) pieces."""
    out = []

    def plain(chunk):
        chunk = clean(chunk).strip(" —-–")
        if chunk:
            out.append(("it", chunk))

    pos = 0
    for m in INLINE_RE.finditer(text):
        plain(text[pos:m.start()])
        if m.group("fr"):
            out.append(("fr", clean(m.group("fr"))))
        elif m.group("it"):
            out.append(("it", clean(m.group("it"))))
        else:
            code = m.group("code").strip("-")
            # Short letter groups (`ou`, `s`) are spelled out letter by letter.
            if len(code) <= 3 and code.isalpha():
                code = ", ".join(code)
            out.append(("it", code))
        pos = m.end()
    plain(text[pos:])

    # Consecutive Italian pieces are one sentence: say them in one breath.
    merged = []
    for lang, piece in out:
        if merged and lang == "it" == merged[-1][0]:
            merged[-1] = ("it", merged[-1][1] + " " + piece)
        else:
            merged.append((lang, piece))
    return [(lang, re.sub(r"\s+([,.;:!?])", r"\1", piece))
            for lang, piece in merged if spoken(piece)]


def elements(body):
    """Yield ("heading" | "item" | "para", text) for the lines of a block."""
    para = []
    for raw in body.splitlines() + [""]:
        line = raw.strip()
        if line.startswith(">"):
            line = line.lstrip("> ").strip()
        is_item = re.match(r"^([-*+]|\d+\.)\s+", line)
        if para and (not line or is_item or line.startswith("#")):
            yield "para", " ".join(para)
            para = []
        if not line or line.startswith("|") or line.startswith("<!--"):
            continue
        if line.startswith("#"):
            yield "heading", line
        elif is_item:
            yield "item", line[is_item.end():]
        else:
            para.append(line)


# ---------------------------------------------------------------- scripts
#
# A script is a list of steps: ("say", voice, rate, text), ("pause", seconds)
# or ("repeat_pause",), a pause sized on the last thing said.

def say(voice, text, rate=None):
    if rate is None:
        rate = ITALIAN_RATE if voice == NARRATOR else FRENCH_RATE
    return ("say", voice, rate, text)


def read_segments(segs, french=FRENCH):
    steps = []
    for lang, text in segs:
        steps.append(say(french if lang == "fr" else NARRATOR, text))
        steps.append(("pause", 0.4))
    return steps


def heading_steps(line):
    m = HEADING_RE.match(line)
    if m:
        segs = [("fr", clean(m["fr"])), ("it", clean(m["it"]))]
    else:
        segs = [("it", clean(line.lstrip("#")))]
    return read_segments(segs) + [("pause", 0.8)]


def repeat_script(body):
    steps = []
    in_drill = False
    for kind, text in elements(body):
        m = ITEM_RE.match(text) if kind == "item" else None
        if not m:
            in_drill = False
            if kind == "heading":
                steps += heading_steps(text)
            else:
                steps += read_segments(segments(text)) + [("pause", 0.6)]
            continue
        if not in_drill:
            steps += [say(NARRATOR, "Ascolta e ripeti."), ("pause", 1.0)]
            in_drill = True
        fr, it = clean(m["fr"]), clean(m["it"])
        steps += [say(FRENCH, fr), ("pause", 0.6), say(NARRATOR, it), ("pause", 0.5)]
        rest = segments(m["rest"])
        if rest:
            steps += read_segments(rest)
        steps += [
            say(NARRATOR, "Ripeti."), ("pause", 0.3),
            say(FRENCH, fr, ECHO_RATE), ("repeat_pause",),
        ]
    return steps


def parse_voices(spec):
    """'Léa=f; Tom=m' -> {'Léa': voice, 'Tom': voice}"""
    voices, used = {}, {"f": 0, "m": 0}
    for part in (spec or "").split(";"):
        if "=" not in part:
            continue
        name, gender = (s.strip() for s in part.split("=", 1))
        pool = SPEAKER_VOICES.get(gender, [FRENCH])
        voices[name] = pool[used.get(gender, 0) % len(pool)]
        used[gender] = used.get(gender, 0) + 1
    return voices


def listen_script(body, voices_spec):
    voices = parse_voices(voices_spec)
    title, lines = None, []   # lines: (voice, [(lang, text), ...])
    for kind, text in elements(body):
        if kind == "heading":
            title = text
            continue
        m = ITEM_RE.match(text) if kind == "item" else None
        speaker = m["speaker"].strip() if m and m["speaker"] else None
        if speaker:
            text = text.split(":", 1)[1]
        lines.append((voices.get(speaker, FRENCH), segments(text)))

    steps = []
    if title:
        steps += heading_steps(title)
    steps += [say(NARRATOR, "Primo ascolto. Ascolta senza leggere."), ("pause", 1.5)]
    for voice, segs in lines:
        for lang, text in segs:
            if lang == "fr":
                steps += [say(voice, text), ("pause", 0.7)]
    steps += [("pause", 2.0), say(NARRATOR, "Ora ascolta di nuovo, con la traduzione."), ("pause", 1.5)]
    for voice, segs in lines:
        steps += read_segments(segs, french=voice)
        steps.append(("pause", 0.8))
    steps += [("pause", 1.0), say(NARRATOR, "Ora leggi il testo ad alta voce.")]
    return steps


def lesson_tracks(path):
    text = path.read_text(encoding="utf-8")
    for m in BLOCK_RE.finditer(text):
        if m["mode"] == "repeat":
            steps = repeat_script(m["body"])
        else:
            steps = listen_script(m["body"], m["voices"])
        yield m["name"], steps


# ---------------------------------------------------------------- audio

def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(out.stdout)


async def synthesize(voice, rate, text):
    """Return a cached WAV of the text, generating it if needed."""
    import edge_tts

    key = hashlib.sha1(f"{voice}|{rate}|{text}".encode()).hexdigest()
    wav = CACHE / f"{key}.wav"
    if wav.exists():
        return wav
    CACHE.mkdir(exist_ok=True)
    mp3 = CACHE / f"{key}.mp3"
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    for attempt in range(4):
        try:
            await edge_tts.Communicate(text, voice, rate=rate, proxy=proxy).save(str(mp3))
            break
        except Exception as e:
            if attempt == 3:
                raise RuntimeError(f"TTS failed for {voice}: {text!r}") from e
            await asyncio.sleep(2 ** attempt)
    ffmpeg("-i", str(mp3), "-ar", str(SAMPLE_RATE), "-ac", "1", str(wav))
    mp3.unlink()
    return wav


def silence(seconds, tmp):
    wav = Path(tmp) / f"silence-{seconds:.2f}.wav"
    if not wav.exists():
        ffmpeg("-f", "lavfi", "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono", "-t", f"{seconds:.2f}", str(wav))
    return wav


async def build_track(steps, out):
    with tempfile.TemporaryDirectory() as tmp:
        parts, last = [], 0.0
        for step in steps:
            if step[0] == "say":
                wav = await synthesize(*step[1:])
                last = duration(wav)
                parts.append(wav)
            elif step[0] == "pause":
                parts.append(silence(step[1], tmp))
            else:
                parts.append(silence(max(REPEAT_MIN, last * REPEAT_FACTOR + REPEAT_EXTRA), tmp))
        listing = Path(tmp) / "parts.txt"
        listing.write_text("".join(f"file '{p}'\n" for p in parts))
        out.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg("-f", "concat", "-safe", "0", "-i", str(listing),
               "-codec:a", "libmp3lame", "-q:a", "4", str(out))


def print_script(name, steps):
    print(f"\n=== {name}")
    for step in steps:
        if step[0] == "say":
            print(f"  [{step[1]} {step[2]}] {step[3]}")
        elif step[0] == "pause":
            print(f"  ... {step[1]}s")
        else:
            print("  ... (time to repeat)")


async def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("lessons", nargs="*", type=Path, help="lesson files (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="print what would be read, generate nothing")
    parser.add_argument("--only", help="generate only the track with this name")
    args = parser.parse_args()

    lessons = args.lessons or sorted((ROOT / "lessons").glob("*.md"))
    for lesson in lessons:
        for name, steps in lesson_tracks(lesson):
            if args.only and name != args.only:
                continue
            if args.dry_run:
                print_script(name, steps)
                continue
            out = ROOT / "audio" / lesson.stem / f"{name}.mp3"
            print(f"{out.relative_to(ROOT)} ...", end=" ", flush=True)
            await build_track(steps, out)
            print(f"{duration(out) / 60:.1f} min")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
