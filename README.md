# Learning French

A French course for Italian speakers, to learn to speak and write French from scratch.

## Lessons

| # | Lesson | Topics |
|---|---|---|
| 1 | [Bonjour !](lessons/01-bonjour.md) | greetings, *tu* and *vous*, introducing yourself, nationalities, the verb *être* |

## How each lesson works

Every lesson is a markdown file in [`lessons/`](lessons) with two parts:

1. **Apprenons (Impariamo)** — new words, concepts and rules. Each section has an
   audio track: the voice reads every word or sentence in French, then in Italian,
   asks you to repeat, says the French again and leaves a pause for you to repeat
   aloud. The part ends with pen-and-paper exercises, including a writing exercise.
2. **Lire et écouter (Leggere e ascoltare)** — dialogues, stories and sentences.
   Listen first without reading (the track plays the French only), then listen again
   line by line with the Italian translation, then read the text and answer the questions.

Solutions are at the end of each part, folded inside a *Soluzioni* box.

Conventions used in the text:

- French is in **bold**, the Italian translation follows in *(italic between parentheses)*.
- Explanations are in Italian.

## Audio

The tracks live in [`audio/`](audio), one folder per lesson. They are generated from the
lesson text by [`tools/make_audio.py`](tools/make_audio.py) with Microsoft's neural voices
(through [edge-tts](https://github.com/rany2/edge-tts)), so they follow the lesson whenever it changes.

The parts to read aloud are marked in the markdown with HTML comments, invisible when
the page is rendered:

```markdown
<!-- audio:repeat 01-salutations -->
- **Bonjour.** (*Buongiorno.*)
<!-- /audio -->

<!-- audio:listen 06-au-cafe | Léa=f; Tom=m -->
- Léa: **Salut, Tom !** (*Ciao, Tom!*)
<!-- /audio -->
```

- `repeat` blocks: drill items (`**French** (*Italiano*)` list items) get the
  French → Italian → "Ripeti" → French → pause pattern; other text is read through.
- `listen` blocks: played once in French only, then line by line with the translation.
  Speakers get a female (`f`) or male (`m`) voice.

To regenerate the audio (needs Python 3, `ffmpeg` and internet access):

```sh
pip install -r requirements.txt
python tools/make_audio.py                              # all lessons
python tools/make_audio.py lessons/01-bonjour.md        # one lesson
python tools/make_audio.py --only 06-au-cafe            # one track
python tools/make_audio.py --dry-run lessons/01-bonjour.md   # show what would be read
```

Generated clips are cached in `.audio-cache/`, so re-running after a small edit only
synthesizes the sentences that changed.
