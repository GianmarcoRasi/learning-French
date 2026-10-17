#!/usr/bin/env python3
"""Generate the audio tracks of the lessons.

Each lesson marks the parts to be read aloud with HTML comments:

    <!-- audio:repeat 01-salutations -->
    ...
    <!-- /audio -->

    <!-- audio:listen 08-au-cafe | Léa=f; Tom=m -->
    ...
    <!-- /audio -->

Inside a block, text is French and *(italic in parentheses)* is its Italian
translation, read entirely by the Italian voice.

- `repeat` blocks are read in order. A list item of the form
  `**French** (*Italiano*) notes` is a drill: French, Italian, notes,
  "Répète", French again, then a pause long enough to repeat.
- `listen` blocks are played twice: first the French only, then line by line
  with the Italian translation. A list item may start with a bold speaker
  label (`**Léa :** ...`); speakers get a female (f) or male (m) voice as
  declared after the `|`.

Blocks with the same name go into the same track, audio/<lesson>/<name>.mp3.

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

FRENCH_RATE = "-10%"      # slightly slower than normal speech
ECHO_RATE = "-20%"        # the French repeated right before the pause
ITALIAN_RATE = "+0%"

TRANSLATION_GAP = 0.25    # between a French sentence and its Italian translation
SENTENCE_GAP = 0.8        # between one sentence (or French/Italian pair) and the next

REPEAT_FACTOR = 1.8       # pause = this × length of the French + REPEAT_EXTRA
REPEAT_EXTRA = 2.5
REPEAT_MIN = 4.0

# What the voice says around the lesson text, French first.
DRILL_START = [("fr", "Écoute et répète."), ("it", "Ascolta e ripeti.")]
REPEAT = "Répète."
FIRST_LISTEN = [("fr", "Première écoute. Écoute sans lire."), ("it", "Primo ascolto. Ascolta senza leggere.")]
SECOND_LISTEN = [("fr", "Deuxième écoute, avec la traduction."), ("it", "Secondo ascolto, con la traduzione.")]
READ_ALOUD = [("fr", "Maintenant, lis le texte à voix haute."), ("it", "Ora leggi il testo ad alta voce.")]

SAMPLE_RATE = 24000

BLOCK_RE = re.compile(
    r"<!--\s*audio:(?P<mode>repeat|listen)\s+(?P<name>[\w-]+)\s*(?:\|(?P<voices>.*?))?-->"
    r"(?P<body>.*?)<!--\s*/audio\s*-->",
    re.S,
)
DRILL_RE = re.compile(r"^\*\*(?P<fr>[^*]+?)\*\*\s*\(\*(?P<it>.+?)\*\)(?P<rest>.*)$")
SPEAKER_RE = re.compile(r"^\*\*(?P<speaker>[^*]+?)\s*:\s*\*\*\s*(?P<line>.*)$")
TRANSLATION_RE = re.compile(r"\(\*(.+?)\*\)")
LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
SYMBOL_RE = re.compile("[\U0001F000-\U0001FFFF←-⇿☀-➿️]")


# ---------------------------------------------------------------- parsing

def clean(text):
    text = LINK_RE.sub(r"\1", text)
    text = SYMBOL_RE.sub("", text)
    text = re.sub(r"_{2,}", "…", text)            # blanks in the exercises
    text = re.sub(r"[*`#]", "", text)
    text = " ".join(text.split()).strip(" —-–").lstrip(",;:. ")
    return re.sub(r"\s+([,.;!?])", r"\1", text)


def spoken(text):
    """True if the text has something to pronounce, not just punctuation."""
    return any(c.isalnum() for c in text)


def split_languages(text):
    """French text with (*Italian*) translations, each said in one voice."""
    out, pos = [], 0
    for m in TRANSLATION_RE.finditer(text):
        out += [("fr", text[pos:m.start()]), ("it", m[1])]
        pos = m.end()
    out.append(("fr", text[pos:]))
    return out


def segments(text):
    """Split a line of markdown into the (lang, text) pieces to say."""
    merged = []
    for lang, piece in split_languages(text):
        piece = clean(piece)
        if not piece:
            continue
        if merged and merged[-1][0] == lang:
            merged[-1] = (lang, merged[-1][1] + " " + piece)
        else:
            merged.append((lang, piece))
    return [(lang, piece) for lang, piece in merged if spoken(piece)]


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
        if not line or line[0] in "|<" or line.startswith("🎧"):
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


def read(segs, french=FRENCH, gap=SENTENCE_GAP):
    steps = []
    for i, (lang, text) in enumerate(segs):
        translated = lang == "fr" and i + 1 < len(segs) and segs[i + 1][0] == "it"
        steps += [say(french if lang == "fr" else NARRATOR, text),
                  ("pause", TRANSLATION_GAP if translated else gap)]
    return steps


def repeat_script(body):
    steps = []
    in_drill = False
    for kind, text in elements(body):
        m = DRILL_RE.match(text) if kind == "item" else None
        if not m:
            in_drill = False
            steps += read(segments(text)) + [("pause", 0.6 if kind == "heading" else 0.2)]
            continue
        if not in_drill:
            steps += read(DRILL_START) + [("pause", 0.5)]
            in_drill = True
        fr, it = clean(m["fr"]), clean(m["it"])
        steps += [say(FRENCH, fr), ("pause", TRANSLATION_GAP), say(NARRATOR, it), ("pause", SENTENCE_GAP)]
        steps += read(segments(m["rest"]))
        steps += [say(FRENCH, REPEAT), ("pause", 0.5), say(FRENCH, fr, ECHO_RATE), ("repeat_pause",)]
    return steps


def parse_voices(spec):
    """'Léa=f; Tom=m' -> {'Léa': voice, 'Tom': voice}"""
    voices, used = {}, {}
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
    title, lines = [], []   # lines: (voice, [(lang, text), ...])
    for kind, text in elements(body):
        if kind == "heading":
            title = segments(text)
            continue
        voice = FRENCH
        m = SPEAKER_RE.match(text) if kind == "item" else None
        if m:
            voice, text = voices.get(m["speaker"], FRENCH), m["line"]
        lines.append((voice, segments(text)))

    steps = read(title) + [("pause", 1.0)]
    steps += read(FIRST_LISTEN) + [("pause", 1.0)]
    for voice, segs in lines:
        steps += read([s for s in segs if s[0] == "fr"], french=voice, gap=1.0)
    steps += [("pause", 1.5)] + read(SECOND_LISTEN) + [("pause", 1.0)]
    for voice, segs in lines:
        steps += read(segs, french=voice) + [("pause", 0.4)]
    steps += [("pause", 1.0)] + read(READ_ALOUD) + [("pause", 1.5)]
    return steps


def lesson_tracks(path):
    """{track name: steps}, in the order the tracks appear in the lesson."""
    tracks = {}
    for m in BLOCK_RE.finditer(path.read_text(encoding="utf-8")):
        if m["mode"] == "repeat":
            steps = repeat_script(m["body"])
        else:
            steps = listen_script(m["body"], m["voices"])
        tracks.setdefault(m["name"], []).extend(steps)
    return tracks


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
    """Return a cached WAV of the text, without the silence around it."""
    key = hashlib.sha1(f"{voice}|{rate}|{text}".encode()).hexdigest()
    trimmed = CACHE / f"{key}.trim.wav"
    if not trimmed.exists():
        wav = await download(key, voice, rate, text)
        # The voices come with up to a second of silence at each end; cut it
        # (keeping a few ms) so that the pauses are exactly the ones we set.
        edge = "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05"
        ffmpeg("-i", str(wav), "-af", f"{edge},areverse,{edge},areverse", str(trimmed))
    return trimmed


async def download(key, voice, rate, text):
    import edge_tts

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
        for name, steps in lesson_tracks(lesson).items():
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
