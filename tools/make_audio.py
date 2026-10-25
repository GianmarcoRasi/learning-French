#!/usr/bin/env python3
"""Generate the audio tracks of the lessons.

Each lesson marks the parts to be read aloud with HTML comments:

    <!-- audio:repeat 01-salutations -->
    ...
    <!-- /audio -->

    <!-- audio:listen 08-au-cafe | Léa=f; Tom=m -->
    ...
    <!-- /audio -->

Each lesson is written once for each language of translation, in
lessons/french-<language>/ (french-italian, french-english). Inside a block,
text is French and *(italic in parentheses)* is its translation, read by the
voice of that language. That voice never says French: when a translation
quotes French words (in **bold**, or a group of letters in `code`), it is
followed by what to say instead, in a comment tagged with the language:

    (*Con gli amici si usa **tu**.*)<!-- it: Con gli amici si dà del tu. -->
    (*With friends you use **tu**.*)<!-- en: With friends you use the informal word. -->

The script stops if one is missing. Single letters in `code` are fine: the
voice says the letter.

- `repeat` blocks are read in order. A list item of the form
  `**French** (*Italiano*) notes` is a drill: French, Italian, notes,
  "Répète", French again, then a pause long enough to repeat.
- `listen` blocks are played twice: first the French only, then line by line
  with the Italian translation. A list item may start with a bold speaker
  label (`**Léa :** ...`); speakers get a female (f) or male (m) voice as
  declared after the `|`.

Blocks with the same name go into the same track,
audio/french-<language>/<lesson>/<name>.mp3.

Each lesson also has a French-only version, for review: the script writes it
from the Italian lesson to lessons/french-only/<lesson>.md, without the
translations, and builds its tracks in audio/french-only/<lesson>/. Lines
that are only Italian (exercise items to translate) are kept. Text between <!-- bilingual --> and
<!-- /bilingual --> is left out of it; text in a <!-- french-only ... -->
comment appears only in it.

Usage:
    python tools/make_audio.py                     # all lessons
    python tools/make_audio.py lessons/french-english/01-bonjour.md
    python tools/make_audio.py --dry-run lessons/french-italian/01-bonjour.md
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

FRENCH = "fr-FR-DeniseNeural"
SPEAKER_VOICES = {
    "f": ["fr-FR-DeniseNeural", "fr-FR-VivienneMultilingualNeural"],
    "m": ["fr-FR-HenriNeural", "fr-FR-RemyMultilingualNeural"],
}

FRENCH_RATE = "-10%"      # slightly slower than normal speech
ECHO_RATE = "-20%"        # the French repeated right before the pause
TRANSLATION_RATE = "+0%"

TRANSLATION_GAP = 0.25    # between a French sentence and its Italian translation
SENTENCE_GAP = 0.5        # between one sentence (or French/Italian pair) and the next
FULL_STOP_GAP = 0.3       # after a full stop inside a piece of text in one language

REPEAT_FACTOR = 1.2       # pause = this × length of the French + REPEAT_EXTRA
REPEAT_EXTRA = 1.0
REPEAT_MIN = 2.0

# The languages of translation: the lesson folder, the tag of the comments
# with what the voice says instead of French, the voice, and what it says
# around the lesson text (after the French, in the same order).
TRANSLATIONS = {
    "french-italian": {
        "tag": "it",
        "voice": "it-IT-ElsaNeural",
        "drill_start": "Ascolta e ripeti.",
        "first_listen": "Primo ascolto. Ascolta senza leggere.",
        "second_listen": "Secondo ascolto, con la traduzione.",
        "read_aloud": "Ora leggi il testo ad alta voce.",
    },
    "french-english": {
        "tag": "en",
        "voice": "en-US-JennyNeural",
        "drill_start": "Listen and repeat.",
        "first_listen": "First listening. Listen without reading.",
        "second_listen": "Second listening, with the translation.",
        "read_aloud": "Now read the text aloud.",
    },
}
FRENCH_ONLY_SOURCE = "french-italian"   # the lessons the French-only version is made from

# What the voice says around the lesson text, in French.
DRILL_START = "Écoute et répète."
REPEAT = "Répète."
FIRST_LISTEN = "Première écoute. Écoute sans lire."
SECOND_LISTEN = "Deuxième écoute, avec la traduction."
READ_ALOUD = "Maintenant, lis le texte à voix haute."
ONLY_LISTEN = "Écoute sans lire."   # the single listening of the French-only version

SAMPLE_RATE = 24000

BLOCK_RE = re.compile(
    r"<!--\s*audio:(?P<mode>repeat|listen)\s+(?P<name>[\w-]+)\s*(?:\|(?P<voices>.*?))?-->"
    r"(?P<body>.*?)<!--\s*/audio\s*-->",
    re.S,
)
SAY_RE = r"(?:\s*<!--\s*(?P<tag>[a-z]{2}):\s*(?P<say>.*?)\s*-->)?"
DRILL_RE = re.compile(r"^\*\*(?P<fr>[^*]+?)\*\*\s*\(\*(?P<it>.+?)\*\)" + SAY_RE + r"(?P<rest>.*)$")
SPEAKER_RE = re.compile(r"^\*\*(?P<speaker>[^*]+?)\s*:\s*\*\*\s*(?P<line>.*)$")
TRANSLATION_RE = re.compile(r"\(\*(?P<it>.+?)\*\)" + SAY_RE)
FRENCH_QUOTE_RE = re.compile(r"\*\*[^*]+?\*\*|`[^`]+`")
SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")
COMMENT_RE = re.compile(r"<!--.*?-->")
BILINGUAL_RE = re.compile(r"<!--\s*bilingual\s*-->\n?(.*?)<!--\s*/bilingual\s*-->\n?", re.S)
FRENCH_ONLY_RE = re.compile(r"<!--\s*french-only\s*\n(.*?)-->\n?", re.S)
LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
SYMBOL_RE = re.compile("[\U0001F000-\U0001FFFF←-⇿☀-➿️]")


# ---------------------------------------------------------------- parsing

def clean(text):
    text = LINK_RE.sub(r"\1", text)
    text = COMMENT_RE.sub("", text)
    text = SYMBOL_RE.sub("", text)
    text = re.sub(r"_{2,}", "…", text)            # blanks in the exercises
    text = re.sub(r"[*`#]", "", text)
    text = " ".join(text.split()).strip(" —-–").lstrip(",;:. ")
    return re.sub(r"\s+([,.;!?])", r"\1", text)


def spoken(text):
    """True if the text has something to pronounce, not just punctuation."""
    return any(c.isalnum() for c in text)


def translation(m, tr):
    """What the voice of the translation says for a (*translation*) matched by m."""
    if m["say"]:
        if m["tag"] != tr["tag"]:
            raise ValueError(f"<!-- {m['tag']}: ... --> in a lesson translated with {tr['tag']}: {m['say']}")
        return m["say"]
    # Bold is French; so is a group of letters in code, but not a single letter.
    if any(q.startswith("**") or len(q) > 3 for q in FRENCH_QUOTE_RE.findall(m["it"])):
        raise ValueError(f"French words in a translation, add <!-- {tr['tag']}: ... --> after it: {m['it']}")
    return m["it"]


def split_languages(text, tr):
    """French text with (*translations*), each said in one voice."""
    out, pos = [], 0
    for m in TRANSLATION_RE.finditer(text):
        out += [("fr", text[pos:m.start()]), ("tr", translation(m, tr))]
        pos = m.end()
    out.append(("fr", text[pos:]))
    return out


def segments(text, tr, french_only=False):
    """Split a line of markdown into the (lang, text) pieces to say, lang
    being "fr" or "tr" (the translation).

    In the French-only version the translations are dropped, unless the line
    is all translation.
    """
    merged = []
    for lang, piece in split_languages(text, tr):
        piece = clean(piece)
        if not piece:
            continue
        if merged and merged[-1][0] == lang:
            merged[-1] = (lang, merged[-1][1] + " " + piece)
        else:
            merged.append((lang, piece))
    merged = [(lang, piece) for lang, piece in merged if spoken(piece)]
    if french_only and any(lang == "fr" for lang, _ in merged):
        merged = [s for s in merged if s[0] == "fr"]
    return merged


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
# A script is a list of steps: ("say", voice, rate, text), ("pause", seconds),
# ("gap", seconds), a pause inside one thing said, or ("repeat_pause",), a
# pause sized on what was said since the last ("pause", ...).

def say(voice, text, rate=None):
    """Steps to say a piece of text, one sentence at a time.

    The voices pause for a long time at a full stop, so each sentence is said
    on its own and followed by a shorter gap.
    """
    if rate is None:
        rate = FRENCH_RATE if voice.startswith("fr-") else TRANSLATION_RATE
    steps = []
    for sentence in SENTENCE_END_RE.split(text):
        if not spoken(sentence):
            continue
        if steps:
            steps.append(("gap", FULL_STOP_GAP))
        steps.append(("say", voice, rate, sentence))
    return steps


def read(segs, tr, french=FRENCH, gap=SENTENCE_GAP):
    steps = []
    for i, (lang, text) in enumerate(segs):
        translated = lang == "fr" and i + 1 < len(segs) and segs[i + 1][0] == "tr"
        steps += say(french if lang == "fr" else tr["voice"], text)
        steps.append(("pause", TRANSLATION_GAP if translated else gap))
    return steps


def french(segs):
    return [s for s in segs if s[0] == "fr"]


def prompt(fr, tr, key, french_only=False):
    """What the voice says around the lesson text: French, then translation."""
    return [("fr", fr)] if french_only else [("fr", fr), ("tr", tr[key])]


def repeat_script(body, tr, french_only=False):
    steps = []
    in_drill = False
    for kind, text in elements(body):
        m = DRILL_RE.match(text) if kind == "item" else None
        if not m:
            in_drill = False
            steps += read(segments(text, tr, french_only), tr) + [("pause", 0.4 if kind == "heading" else 0.1)]
            continue
        if not in_drill:
            steps += read(prompt(DRILL_START, tr, "drill_start", french_only), tr) + [("pause", 0.3)]
            in_drill = True
        fr, translated = clean(m["fr"]), clean(translation(m, tr))
        if french_only:
            steps += say(FRENCH, fr) + [("pause", SENTENCE_GAP)]
        else:
            steps += (say(FRENCH, fr) + [("pause", TRANSLATION_GAP)]
                      + say(tr["voice"], translated) + [("pause", SENTENCE_GAP)])
        steps += read(segments(m["rest"], tr, french_only), tr)
        steps += say(FRENCH, REPEAT) + [("pause", 0.3)] + say(FRENCH, fr, ECHO_RATE) + [("repeat_pause",)]
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


def listen_script(body, voices_spec, tr, french_only=False):
    voices = parse_voices(voices_spec)
    title, lines = [], []   # lines: (voice, [(lang, text), ...])
    for kind, text in elements(body):
        if kind == "heading":
            title = segments(text, tr, french_only)
            continue
        voice = FRENCH
        m = SPEAKER_RE.match(text) if kind == "item" else None
        if m:
            voice, text = voices.get(m["speaker"], FRENCH), m["line"]
        lines.append((voice, segments(text, tr)))

    steps = read(title, tr) + [("pause", 0.7)]
    if french_only:
        steps += read([("fr", ONLY_LISTEN)], tr) + [("pause", 0.7)]
    else:
        steps += read(prompt(FIRST_LISTEN, tr, "first_listen"), tr) + [("pause", 0.7)]
    for voice, segs in lines:
        steps += read(french(segs), tr, french=voice, gap=0.7)
    if french_only:
        return steps + [("pause", 1.0)] + read([("fr", READ_ALOUD)], tr) + [("pause", 1.5)]
    steps += [("pause", 1.0)] + read(prompt(SECOND_LISTEN, tr, "second_listen"), tr) + [("pause", 0.7)]
    for voice, segs in lines:
        steps += read(segs, tr, french=voice) + [("pause", 0.3)]
    steps += [("pause", 0.7)] + read(prompt(READ_ALOUD, tr, "read_aloud"), tr) + [("pause", 1.5)]
    return steps


def version(text, french_only):
    """The lesson text of one version, without the parts of the other one."""
    if french_only:
        return FRENCH_ONLY_RE.sub(r"\1", BILINGUAL_RE.sub("", text))
    return FRENCH_ONLY_RE.sub("", BILINGUAL_RE.sub(r"\1", text))


def lesson_tracks(text, tr, french_only=False):
    """{track name: steps}, in the order the tracks appear in the lesson."""
    tracks = {}
    for m in BLOCK_RE.finditer(version(text, french_only)):
        if m["mode"] == "repeat":
            steps = repeat_script(m["body"], tr, french_only)
        else:
            steps = listen_script(m["body"], m["voices"], tr, french_only)
        tracks.setdefault(m["name"], []).extend(steps)
    return tracks


def french_only_markdown(text, name):
    """The French-only version of a lesson, as markdown."""
    lines = []
    for line in version(text, french_only=True).splitlines():
        stripped = re.sub(r"\s*\(\*.+?\*\)(\s*<!--\s*[a-z]{2}:.*?-->)?|\s*\(<i>.+?</i>\)", "", line).rstrip()
        # Keep the lines that are only a translation: exercise items.
        if re.sub(r"^\s*([-*+]|\d+\.)?\s*", "", stripped):
            line = stripped
        lines.append(line)
    body = "\n".join(lines).replace(f"](../../audio/french-italian/{name}/", f"](../../audio/french-only/{name}/")
    return (f"<!-- Generated from lessons/french-italian/{name}.md by tools/make_audio.py: "
            f"edit that file, not this one. -->\n{body.rstrip()}\n")


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
                last += duration(wav)
                parts.append(wav)
            elif step[0] == "gap":
                last += step[1]
                parts.append(silence(step[1], tmp))
            elif step[0] == "pause":
                last = 0.0
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
        elif step[0] in ("pause", "gap"):
            print(f"  ... {step[1]}s")
        else:
            print("  ... (time to repeat)")


async def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("lessons", nargs="*", type=Path, help="lesson files (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="print what would be read, generate nothing")
    parser.add_argument("--only", help="generate only the track with this name")
    args = parser.parse_args()

    lessons = args.lessons or [
        path for folder in TRANSLATIONS for path in sorted((ROOT / "lessons" / folder).glob("*.md"))
    ]
    for lesson in lessons:
        lesson = lesson.resolve()
        folder = lesson.parent.name
        if folder not in TRANSLATIONS:
            sys.exit(f"{lesson}: not in one of the folders {', '.join(TRANSLATIONS)}")
        tr = TRANSLATIONS[folder]
        text = lesson.read_text(encoding="utf-8")
        versions = [(False, ROOT / "audio" / folder)]
        if folder == FRENCH_ONLY_SOURCE:
            versions.append((True, ROOT / "audio" / "french-only"))
            if not args.dry_run:
                out = ROOT / "lessons" / "french-only" / lesson.name
                out.parent.mkdir(exist_ok=True)
                out.write_text(french_only_markdown(text, lesson.stem), encoding="utf-8")
        for french_only, folder in versions:
            for name, steps in lesson_tracks(text, tr, french_only).items():
                if args.only and name != args.only:
                    continue
                out = folder / lesson.stem / f"{name}.mp3"
                if args.dry_run:
                    print_script(out.relative_to(ROOT), steps)
                    continue
                print(f"{out.relative_to(ROOT)} ...", end=" ", flush=True)
                await build_track(steps, out)
                print(f"{duration(out) / 60:.1f} min")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
