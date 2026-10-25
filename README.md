# Learning French

A French course for Italian and English speakers, to learn to speak and write French from scratch.

## Lessons

| # | French only | With Italian translation | With English translation | Topics |
|---|---|---|---|---|
| 1 | [Bonjour !](lessons/french-only/01-bonjour.md) | [Bonjour !](lessons/french-italian/01-bonjour.md) | [Bonjour !](lessons/french-english/01-bonjour.md) | greetings, *tu* and *vous*, introducing yourself, nationalities, the verb *être* |
| 2 | [Qu'est-ce que c'est ?](lessons/french-only/02-qu-est-ce-que-c-est.md) | [Qu'est-ce que c'est ?](lessons/french-italian/02-qu-est-ce-que-c-est.md) | [Qu'est-ce que c'est ?](lessons/french-english/02-qu-est-ce-que-c-est.md) | numbers 0–20, nasal vowels, articles and gender, *c'est* and *il y a*, the verb *avoir*, age |
| 3 | [Ma famille](lessons/french-only/03-ma-famille.md) | [Ma famille](lessons/french-italian/03-ma-famille.md) | [Ma famille](lessons/french-english/03-ma-famille.md) | family, possessives, *-er* verbs and *aimer*, negation, questions with *est-ce que* and *si* |
| 4 | [Ma journée](lessons/french-only/04-ma-journee.md) | [Ma journée](lessons/french-italian/04-ma-journee.md) | [Ma journée](lessons/french-english/04-ma-journee.md) | numbers 21–69, telling the time, days of the week, reflexive verbs, the verb *faire* |
| 5 | [En ville](lessons/french-only/05-en-ville.md) | [En ville](lessons/french-italian/05-en-ville.md) | [En ville](lessons/french-english/05-en-ville.md) | numbers 70–100, places in town, the verb *aller*, *au* / *à la*, the near future, asking the way |

## Stories

Longer stories to read and listen to after lesson 5, one for each genre. They are told in the
present, with the words and grammar of lessons 1–5; the few new words are listed at the start.
Each story has four chapters, each with its track and questions, and a writing exercise at the end.

| Genre | French only | With Italian translation | With English translation |
|---|---|---|---|
| Fantasy | [La clé d'argent](lessons/french-only/histoire-fantastique-la-cle-d-argent.md) | [La clé d'argent](lessons/french-italian/histoire-fantastique-la-cle-d-argent.md) | [La clé d'argent](lessons/french-english/histoire-fantastique-la-cle-d-argent.md) |
| Mystery | [La Dame en bleu](lessons/french-only/histoire-policiere-la-dame-en-bleu.md) | [La Dame en bleu](lessons/french-italian/histoire-policiere-la-dame-en-bleu.md) | [La Dame en bleu](lessons/french-english/histoire-policiere-la-dame-en-bleu.md) |
| Sci-fi | [Ada sait tout](lessons/french-only/histoire-science-fiction-ada-sait-tout.md) | [Ada sait tout](lessons/french-italian/histoire-science-fiction-ada-sait-tout.md) | [Ada sait tout](lessons/french-english/histoire-science-fiction-ada-sait-tout.md) |
| Romance | [Le café de huit heures](lessons/french-only/histoire-amour-le-cafe-de-huit-heures.md) | [Le café de huit heures](lessons/french-italian/histoire-amour-le-cafe-de-huit-heures.md) | [Le café de huit heures](lessons/french-english/histoire-amour-le-cafe-de-huit-heures.md) |

A story is a lesson file named `histoire-<genre>-<title>.md` (genres: `fantastique`, `policiere`,
`science-fiction`, `amour`), written like the lessons and with audio made the same way. The website
lists the stories after lesson 5, grouped by genre (`GENRES` and `STORIES_AFTER` in
`tools/build_site.py`). In the stories, the narration has its own voice: `Narration=m` (or `f`)
in the voices of a `listen` block is the voice of the lines without a speaker.

## Support

If the course helps you, you can [buy me a coffee on Ko-fi](https://ko-fi.com/qwark992) ☕

## Reading and listening on a phone

The lessons are also published as a website, with an audio player in the text
of each section: <https://gianmarcorasi.github.io/learning-French/>. On the phone,
use *Add to Home Screen* (Safari's share menu, or Chrome's ⋮ menu) to open it like
an app. The **▶ Tout** button at the top plays all the audio of the lesson, one track
after the other, and the **1×** button changes the speed of the audio.

*Tout* keeps playing with the screen off, and can be paused, resumed or moved to the
previous or next track from the lock screen. If it is interrupted (a call, or the
browser closing the page), the button becomes **▶ Reprendre** and goes on from where
it stopped, a few seconds earlier; the position is remembered for each lesson, also
after closing the page. **⏮ Début** starts again from the first track.

The site is built by [`tools/build_site.py`](tools/build_site.py) and published by
[`.github/workflows/pages.yml`](.github/workflows/pages.yml) on every push to `main`.
To build it locally:

```sh
pip install -r requirements.txt
python tools/build_site.py      # writes _site/
```

## How each lesson works

Every lesson is a markdown file in [`lessons/french-italian/`](lessons/french-italian),
for Italian speakers, and in [`lessons/french-english/`](lessons/french-english), for English
speakers. It has two parts:

1. **Apprenons (Impariamo, Let's learn)** — new words, concepts and rules. The voice reads every
   word or sentence in French, then in the translation, asks you to repeat, says the French
   again and leaves a pause for you to repeat aloud. The part ends with pen-and-paper
   exercises, including a writing exercise.
2. **Lire et écouter (Leggere e ascoltare, Read and listen)** — dialogues, stories and sentences.
   Listen first without reading (the track plays the French only), then listen again
   line by line with the translation, then read the text and answer the questions.

Solutions are at the end of each part, folded inside a *Solutions* box.

Conventions used in the text:

- Everything is written in French — explanations and instructions included — and each
  sentence is followed by its Italian (or English) translation in *(italic between parentheses)*.
- New words are in **bold**.
- Headings are translated too.
- The whole lesson has audio, except the solutions and the summary tables.

### English version

The English version is the same lesson, block for block, with the same tracks, but it is
not a word-for-word copy: where the Italian lesson compares French with Italian (genders,
*son* / *sa* and the possessives, *au* and *al*…), the English one compares it with English.
When you change a lesson, change both versions.

### French-only version

Each lesson also comes in a French-only version, with its own audio, in
[`lessons/french-only/`](lessons/french-only): the same lesson without the Italian
translations, to go through it again once you have listened to it a couple of times.
Drills go French → "Répète" → French → pause, and dialogues are played once, in French.
Only the Italian sentences of the translation exercise are kept.

The French-only version is generated from the Italian lesson file: never edit it by hand.
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

The tracks live in [`audio/french-italian/`](audio/french-italian) and
[`audio/french-english/`](audio/french-english), one folder per lesson, and in
[`audio/french-only/`](audio/french-only) for the French-only version. They are generated from the
lesson text by [`tools/make_audio.py`](tools/make_audio.py) with Microsoft's neural voices
(through [edge-tts](https://github.com/rany2/edge-tts)), so they follow the lesson whenever it changes.
Behind a proxy with its own certificate (as in the Claude cloud sessions), set `SSL_CERT_FILE` to it.

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

- Text is read in French, *(italic in parentheses)* in Italian or English. The voice of
  the translation never says French words: when a translation quotes French (in **bold**,
  or a group of letters in `code`), it is followed by a comment with what to say instead,
  which refers to the French without saying it. The comment is tagged `it:` in the Italian
  lessons and `en:` in the English ones, and is invisible on the page:

  ```markdown
  On utilise **vous**. (*Si usa **vous**.*)<!-- it: Si dà del voi. -->
  On utilise **vous**. (*You use **vous**.*)<!-- en: You use the formal word. -->
  ```

  `make_audio.py` stops with an error if a translation quotes French and has no such
  comment. A single letter in `code` needs none: the voice says the letter. The voices of
  each language are in `TRANSLATIONS`, at the top of `tools/make_audio.py`.
- Each sentence is synthesized on its own and followed by a short gap, because the
  voices pause too long at a full stop. The pause sizes are constants at the top of
  `tools/make_audio.py`.
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
python tools/make_audio.py lessons/french-english/01-bonjour.md        # one lesson, English version
python tools/make_audio.py --only 08-au-cafe            # one track
python tools/make_audio.py --dry-run lessons/french-italian/01-bonjour.md   # show what would be read
```

The same command writes the French-only lesson files (from the Italian lessons). Generated clips are cached in
`.audio-cache/`, so re-running after a small edit only synthesizes the sentences that changed.
