# Learning French

A French course for Italian speakers, to learn to speak and write French from scratch.

## Lessons

| # | Lesson | French only | Topics |
|---|---|---|---|
| 1 | [Bonjour !](lessons/french-italian/01-bonjour.md) | [Bonjour !](lessons/french-only/01-bonjour.md) | greetings, *tu* and *vous*, introducing yourself, nationalities, the verb *être* |
| 2 | [Qu'est-ce que c'est ?](lessons/french-italian/02-qu-est-ce-que-c-est.md) | [Qu'est-ce que c'est ?](lessons/french-only/02-qu-est-ce-que-c-est.md) | numbers 0–20, nasal vowels, articles and gender, *c'est* and *il y a*, the verb *avoir*, age |
| 3 | [Ma famille](lessons/french-italian/03-ma-famille.md) | [Ma famille](lessons/french-only/03-ma-famille.md) | family, possessives, *-er* verbs and *aimer*, negation, questions with *est-ce que* and *si* |

## How each lesson works

Every lesson is a markdown file in [`lessons/french-italian/`](lessons/french-italian) with two parts:

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
- Headings are translated too.
- The whole lesson has audio, except the solutions and the summary tables.

### French-only version

Each lesson also comes in a French-only version, with its own audio, in
[`lessons/french-only/`](lessons/french-only): the same lesson without the Italian
translations, to go through it again once you have listened to it a couple of times.
Drills go French → "Répète" → French → pause, and dialogues are played once, in French.
Only the Italian sentences of the translation exercise are kept.

The French-only version is generated from the main lesson file: never edit it by hand.
Text that only makes sense in one version is marked in the main file:

```markdown
<!-- bilingual -->
Only in the version with translations.
<!-- /bilingual -->
<!-- french-only
Only in the French-only version.
-->
```

## Audio

The tracks live in [`audio/french-italian/`](audio/french-italian), one folder per lesson, and in
[`audio/french-only/`](audio/french-only) for the French-only version. They are generated from the
lesson text by [`tools/make_audio.py`](tools/make_audio.py) with Microsoft's neural voices
(through [edge-tts](https://github.com/rany2/edge-tts)), so they follow the lesson whenever it changes.

The parts to read aloud are marked in the markdown with HTML comments, invisible when
the page is rendered:

```markdown
<!-- audio:repeat 01-salutations -->
### 1. Les salutations (*I saluti*)

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
python tools/make_audio.py lessons/french-italian/01-bonjour.md        # one lesson
python tools/make_audio.py --only 08-au-cafe            # one track
python tools/make_audio.py --dry-run lessons/french-italian/01-bonjour.md   # show what would be read
```

The same command writes the French-only lesson files. Generated clips are cached in
`.audio-cache/`, so re-running after a small edit only synthesizes the sentences that changed.
