---
name: last30daysYT
description: Build a newsletter-ready brief on any topic from the last 30 days of YouTube — engaging, skimmable, and genuinely educational. Give it a topic ("AI local models", "hardware for AI", "condições climáticas no Sul do Brasil") and it engagement-ranks the best videos, transcribes them, and writes a newsletter the reader will actually finish and learn from. Optionally follow a standing list of channels too. Works in any language (set from the topic). Invoke as /last30daysYT {topic} [channels]. Wraps the yt2md CLI for transcripts; the model writes the newsletter (Markdown + HTML with a chart + PDF). Use when the user wants to keep up with a topic, build a recurring newsletter, get a YouTube digest, or monitor channels/topics over the last N days.
---

# last30daysYT

A topic-first YouTube **newsletter generator**. The reader names a topic; this
turns the last 30 days of the best videos on it into a brief they'll actually
finish and learn from. Following standing channels is an optional extra source.
It wraps `~/yt2md` (CLI at `~/.local/bin/yt2md`) for transcripts and uses you,
the model, as the writer.

## Invocation

Everything after `/last30daysYT` is free text — channel names/handles, a topic,
or both. You parse it (see next section). Examples:

- `/last30daysYT AI safety` — standing channels (`config/channels.txt`) + a
  global YouTube search for "AI safety", last 30 days.
- `/last30daysYT @veritasium @kurzgesagt` — just those two channels, no topic.
- `/last30daysYT @TwoMinutePapers diffusion models` — that channel + a topic.
- `/last30daysYT` (nothing) — everything the standing channels posted, last 30 days.

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
     --days 30 --out /tmp/last30daysYT
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
   topic's language. This is a NEWSLETTER, not a report: the reader should want
   to finish it and come away having learned something. Structure:
   - **Headline** + a one-line hook (what changed this month, why care now).
   - **TL;DR** — 3–5 bullets, the takeaways someone could repeat at dinner.
   - **Sections by theme** (not by video). Each: a bolded claim, a plain-language
     explanation that actually teaches the idea (define jargon, give the number,
     say why it matters), and the citation. Lead with the point, not the source.
   - **Confidence tag on every headline claim**, inline, right where the claim
     is — `confirmed` / `single source` / `overstated` — each linking the
     outside source where one exists. Uncertainty travels WITH the claim; never
     pool all the hedging into "on the radar" at the end. Add a one-line legend.
   - **≥1 actionable table** the reader could act on, mined from the transcripts
     + corroboration (e.g. model → quant → memory → tokens/sec → verdict). If the
     material genuinely can't support one, say so explicitly.
   - **Worth watching** — 2–4 standout videos with one line each on why + views.
   - **On the radar** — what to watch next month.
   Self-contained HTML: inline CSS, clean editorial layout, ≥1 chart from
   `stats.json` (e.g. views/velocity per video). Load Chart.js **pinned with an
   SRI hash**, never a floating tag — a floating `@4` lets the CDN serve
   arbitrary unverified code into the reader's browser:
   ```html
   <script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.0/dist/chart.umd.min.js"
     integrity="sha384-XcdcwHqIPULERb2yDEM4R0XaQKU3YnDsrTmjACBZyfdVVqjh6xQ4/DCMd7XLcA6Y"
     crossorigin="anonymous"></script>
   ```
   Satisfy every success check below.

4. **Render + open.**
   ```
   python3 scripts/yt_brief.py render /tmp/last30daysYT/report.html
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
9. **Depth, not shallow** — every headline claim carries an inline confidence
   tag (`confirmed`/`single source`/`overstated`), ≥1 tag is corroborated by a
   non-YouTube link, uncertainty appears in the body (not only at the end), and
   there is ≥1 actionable table. Verify mechanically:
   ```
   python3 scripts/eval_depth.py /tmp/last30daysYT/report.html
   ```
   It must exit 0 (all mechanical checks pass). D6 (novelty — does a
   topic-follower learn ≥3 new things?) is your own judgement, not scriptable.

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
