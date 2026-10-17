# Learning French

A French course for Italian speakers, to learn to speak and write French from scratch.

## Lessons

| # | Lesson | Topics |
|---|---|---|
| 1 | [Bonjour !](lessons/01-bonjour.md) | greetings, *tu* and *vous*, introducing yourself, nationalities, the verb *être* |

## How each lesson works

Every lesson is a markdown file in [`lessons/`](lessons) with two parts:

1. **Apprenons (Impariamo)** — new words, concepts and rules. The voice reads every
   word or sentence in French, then in Italian, asks you to repeat, says the French
   again and leaves a pause for you to repeat aloud. The part ends with pen-and-paper
   exercises, including a writing exercise.
2. **Lire et écouter (Leggere e ascoltare)** — dialogues, stories and sentences.
   Listen first without reading (the track plays the French only), then listen again
   line by line with the Italian translation, then read the text and answer the questions.

Solutions are at the end of each part, folded inside a *Solutions* box.

Conventions used in the text:

- Everything is written in French — explanations and instructions included — and each
  sentence is followed by its Italian translation in *(italic between parentheses)*.
- New words are in **bold**.
- Headings are in French only, without translation.
- The whole lesson has audio, except the solutions and the summary tables.

## Audio

The tracks live in [`audio/`](audio), one folder per lesson. They are generated from the
lesson text by [`tools/make_audio.py`](tools/make_audio.py) with Microsoft's neural voices
(through [edge-tts](https://github.com/rany2/edge-tts)), so they follow the lesson whenever it changes.

The parts to read aloud are marked in the markdown with HTML comments, invisible when
the page is rendered:

```markdown
<!-- audio:repeat 01-salutations -->
### 1. Les salutations

On salue de façon différente selon la personne. (*Si saluta in modo diverso secondo la persona.*)

- **Bonjour.** (*Buongiorno.*) — On le dit toute la journée. (*Si dice per tutto il giorno.*)
<!-- /audio -->

<!-- audio:listen 08-au-cafe | Léa=f; Tom=m -->
- **Léa :** Salut, Tom ! (*Ciao, Tom!*)
<!-- /audio -->
```

- Text is read in French, *(italic in parentheses)* entirely in Italian.
- `repeat` blocks: drill items (list items starting with `**French** (*Italiano*)`)
  get the French → Italian → notes → "Répète" → French → pause pattern; everything
  else is read through.
- `listen` blocks: played once in French only, then line by line with the translation.
  Speakers get a female (`f`) or male (`m`) voice.
- Blocks with the same name go into one track (for example a dialogue and its questions).

To regenerate the audio (needs Python 3, `ffmpeg` and internet access):

```sh
pip install -r requirements.txt
python tools/make_audio.py                              # all lessons
python tools/make_audio.py lessons/01-bonjour.md        # one lesson
python tools/make_audio.py --only 08-au-cafe            # one track
python tools/make_audio.py --dry-run lessons/01-bonjour.md   # show what would be read
```

Generated clips are cached in `.audio-cache/`, so re-running after a small edit only
synthesizes the sentences that changed.
