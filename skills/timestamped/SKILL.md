---
name: timestamped
description: Timestamped — keep up with any topic in depth from the last 30 days of YouTube. Give it a topic ("AI local models", "hardware for AI", "condições climáticas no Sul do Brasil") and it velocity-ranks the best videos, transcribes them, and writes a newsletter where every claim is cited to the exact second and the big claims are corroborated against an outside source. Optionally follow a standing list of channels too. Works in any language (set from the topic). Invoke as /timestamped {topic} [channels]. Wraps the yt2md CLI for transcripts; the model writes the newsletter (Markdown + HTML with a chart + PDF), following DESIGN.md. Use when the user wants to keep up with a topic, build a recurring newsletter, get a YouTube digest, or monitor channels/topics over the last N days.
---

# Timestamped

A topic-first YouTube **newsletter generator**. The reader names a topic; this
turns the last 30 days of the best videos on it into a brief they'll actually
finish and learn from — every claim cited to the second, the big ones
corroborated. Following standing channels is an optional extra source.
It wraps `~/yt2md` (CLI at `~/.local/bin/yt2md`) for transcripts and uses you,
the model, as the writer.

## Invocation

Everything after `/timestamped` is free text — channel names/handles, a topic,
or both. You parse it (see next section). Examples:

- `/timestamped AI safety` — standing channels (`config/channels.txt`) + a
  global YouTube search for "AI safety", last 30 days.
- `/timestamped @veritasium @kurzgesagt` — just those two channels, no topic.
- `/timestamped @TwoMinutePapers diffusion models` — that channel + a topic.
- `/timestamped` (nothing) — everything the standing channels posted, last 30 days.

## Parse the user's args (do this first)

Split the args into channels and a topic:

- **Channel tokens:** anything that is a YouTube URL, a `@handle`, or an obvious
  channel/show name. Convert each to a `/videos` URL:
  `@veritasium` → `https://www.youtube.com/@veritasium/videos`. For a bare name
  you're unsure about, WebSearch `"<name>" youtube channel` to get the exact
  handle before building the URL. Pass each as a separate `--channel URL`.
- **Topic:** the remaining free-text words → the positional `"{topic}"` arg
  (becomes yt2md `--search`).
- **No channel tokens given** → omit `--channel`; the script falls back to the
  standing `config/channels.txt`.
- **No channels anywhere AND no topic** → ask the user for channels or a topic.

## Prerequisites (check once, fix if missing)

- `yt2md` on PATH (`which yt2md`). If missing: `uv tool install git+https://github.com/FrancyJGLisboa/yt2md`
- A JS runtime for yt-dlp: `which deno` (or node/bun). If missing: `brew install deno`.
- `config/channels.txt` has at least one uncommented channel URL **OR** a topic
  was given. If the file is still all-comments and there's no topic, ask the
  user for channel `/videos` URLs (or a topic) before running.

## Steps

1. **Fetch.** Run from the skill's `scripts/` dir:
   ```
   python3 scripts/yt_brief.py fetch "{topic}" --lang en \
     --channel https://www.youtube.com/@veritasium/videos \
     --days 30 --out /tmp/timestamped
   ```
   Pass `""` for the topic when channels-only. Drop all `--channel` flags to use
   the standing `config/channels.txt`. It writes `digest.md` and `stats.json`.
   - **Set `--lang` from the topic's language.** A Portuguese topic ("condições
     climáticas no RS") → `--lang pt,en`; Spanish → `--lang es,en`; etc. Default
     `en`. Wrong language = captions missed = empty newsletter, so get this right.
   - **Channels** are pulled chronologically (newest N per channel).
   - **A topic is engagement pre-ranked**, not taken in raw search order: the
     script flat-searches a pool (`--rank-pool`, default 40), drops Shorts
     (`--min-duration`, default 90s) and live streams, picks the top
     `--search-limit` (default 15) candidates by view count, and transcribes
     them. After fetch it **re-ranks the survivors by velocity (views/day since
     upload)** for featuring/ordering — `--rank-by velocity` (default) vs
     `views`. Velocity is the right default in a recency product: raw views
     bury fresh videos under older ones that simply had longer to accrue.
     `stats.json` carries each video's `views` and `velocity`.
   - Each channel is capped to its **40 newest** videos (`--per-channel-limit`,
     newest-first) before the date check — this keeps runs fast. Raise it only
     for channels that post more than ~40 videos in the window.
   - Still, the first run does one metadata request per candidate video and may
     hit YouTube rate limits — yt2md retries with backoff and resumes on re-run.
     Re-running skips already-saved videos, so a second run is cheap. Tell the
     user the first run on many channels can take a few minutes.
   - **429 "Too Many Requests"** is the main failure under repeated/scale use.
     If you see failed videos with 429, pass `--cookies-from-browser chrome`
     (or safari/firefox) — authenticated requests have far higher limits — or
     wait a few minutes and re-run (it resumes). For a recurring newsletter,
     always run with cookies.

2. **Read the evidence.** Read `stats.json` (counts: total videos, per-channel,
   per-day, captions coverage) and `digest.md` (the concatenated transcripts;
   each video block has a header with Channel / Uploaded / Video URL and a
   transcript where every paragraph is `**[MM:SS](https://youtu.be/ID?t=SEC)**`
   — those timestamped links are your citations).

2b. **Corroborate the top claims (depth pass — do not skip).** A newsletter that
   only relays what YouTubers *said* is a shallow brief. Before writing, take the
   3–5 biggest claims and run **one WebSearch each** against a source outside the
   videos (release notes, model card, a benchmark, the vendor's own docs).
   Record, per claim, whether the outside source **confirms**, is **single
   source** (only the video says it — opinions/framings/anecdotes often are), or
   shows the video **overstated** it. This pass routinely *sharpens* the story —
   e.g. "beats every model" becomes "wins benchmark A, loses B, at 1/6 the cost,"
   which is exactly the depth the reader wants. No new dependency — `WebSearch`
   is enough; only reach for native arXiv/HN/GitHub feeds if it falls short.

3. **Write the newsletter.** Produce `report.html` in `--out` — written in the
   topic's language. **Follow [DESIGN.md](DESIGN.md)** — the visual contract
   (tokens, the timestamp-pill + confidence-chip signature, type scale, print
   rules, slop guards). This is a NEWSLETTER, not a report: the reader should
   want to finish it. **Built for the skim** — hook the 5-second reader, reward
   the digger below (inverted pyramid). Structure, top to bottom:
   - **Punchy headline** (one concrete line, not a clause-stuffed sentence) +
     a **one-line hero takeaway** (`.hero-take`): the single biggest "so what",
     bold, before any meta. This is the 5-second test.
   - **"In 30 seconds"** — 3–5 **one-line** bullets (≤120 chars each, the whole
     block skimmable in under 10s). Each: the takeaway, its `[MM:SS]` pill, then
     the confidence chip as a faint **end-of-line** tag (never mid-sentence).
   - **Meta line + chip legend go BELOW the bullets**, not above — value first,
     friction second.
   - **Sections by theme** (not by video). Each opens with a **bold claim lead**;
     paragraphs stay **≤3 sentences** (no walls of text); teach the idea (define
     jargon, give the number, say why it matters) with the citation. The full
     `confirmed`/`single source`/`overstated` treatment lives here, on each claim
     — uncertainty travels WITH the claim, never pooled only in "on the radar".
   - **≥1 actionable table** the reader could act on, mined from the transcripts
     + corroboration (e.g. model → quant → memory → tokens/sec → verdict). If the
     material genuinely can't support one, say so explicitly.
   - **Worth watching** — 2–4 standout videos with one line each on why + views.
   - **On the radar** — what to watch next month.
   Self-contained HTML: inline CSS, clean editorial layout, ≥1 chart from
   `stats.json` (e.g. views/velocity per video) rendered as **inline CSS bars —
   no Chart.js, no CDN, no `<script>`** (see DESIGN.md §8; a CDN canvas renders
   blank in the headless-Chrome PDF). Satisfy every success check below.

4. **Render + open.**
   ```
   python3 scripts/yt_brief.py render /tmp/timestamped/report.html
   ```
   Writes a sibling `report.pdf` and opens the HTML. Tell the user both paths.

## Success checks (the newsletter is done only when ALL hold)

1. Headline + hook + a TL;DR (3–5 takeaway bullets) at the top.
2. Organized by **theme**, each section teaching the idea in plain language
   (jargon defined, the concrete number/fact given, why-it-matters stated) —
   not a list of video summaries.
3. **Every** substantive claim cites a clickable timestamped link
   (`https://youtu.be/ID?t=SECONDS`) from the transcripts. No claim uncited.
4. At least 2 verbatim quotes woven in (quoted, attributed, linked).
5. Skimmable: bolded leads, short paragraphs, scannable in under 2 minutes.
6. **Substance over views.** Engagement is a prefilter, not the verdict. Drop
   low-substance videos (clickbait, filler, pure promo) regardless of views;
   list what you dropped in one line. Show each featured video's view count.
7. Opens as HTML with ≥1 working chart, plus a non-empty `report.pdf`.
8. Written in the topic's language (a pt topic → a Portuguese newsletter).
9. **Depth + scannability** — every headline claim carries a confidence tag
   (`confirmed`/`single source`/`overstated`), ≥1 tag is corroborated by a
   non-YouTube link, uncertainty appears in the body, there is ≥1 actionable
   table (D1–D5), AND it's built for the skim: a hero takeaway before the meta,
   one-line TL;DR bullets, no wall-of-text paragraph (S1–S3). Verify mechanically:
   ```
   python3 scripts/eval_depth.py /tmp/timestamped/report.html
   ```
   It must exit 0 (all mechanical checks pass). D6 (novelty — does a
   topic-follower learn ≥3 new things?) is your own judgement, not scriptable.
10. **Design, not slop** — the visual contract holds. Run the design gate
   (Impeccable's deterministic 44-rule detector, the visual twin of the depth
   eval; honors the documented suppressions in `.impeccable/config.json`):
   ```
   sh scripts/design_eval.sh /tmp/timestamped/report.html
   ```
   It must exit 0. Needs `npx` (Node). Keep em-dashes sparse so the editorial
   tolerance isn't abused (DESIGN.md §9).

## Report-quality rules

- Cite as markdown/HTML links `[label](url)`, never bare tuples or raw scores.
- Synthesize into prose and trends — do not dump the digest back at the user.
- If captions coverage is low (check `stats.json.with_captions`), say so — the
  picture is partial when many videos had no transcript.
- Distinguish what channels *said* from your inference. Don't invent specifics
  not in the transcripts.

## Notes

- The topic is a **global** YouTube search layered on top of your channels (it
  augments, it does not filter within channels — yt2md can't search inside a
  channel).
- Topic **candidate selection** is by view count (yt-dlp's flat search exposes
  no upload date, so velocity can't be known pre-fetch); featuring/ordering is
  then **velocity-ranked** post-fetch. A tight date window can still leave few
  survivors — if too few come back, raise `--rank-pool` (e.g. 80) or widen
  `--days`. Channels are the reliable spine; topic is the engagement layer.
- Maintain your channel list by editing `config/channels.txt` (one `/videos`
  URL per line, `#` for comments).
- `python3 scripts/yt_brief.py selfcheck` runs the parser/date self-test.
