# last30daysYT

A topic-first **YouTube newsletter generator** for Claude Code. Name a topic and
it engagement-ranks the best videos from the last 30 days, transcribes them, and
writes a newsletter-ready brief you'll actually finish and learn from — Markdown,
HTML (with a chart), and PDF. Optionally follow a standing list of channels too.

A YouTube-only sibling of the `last30days` skill. It does **not** reimplement a
search pipeline — it wraps [yt2md](https://github.com/FrancyJGLisboa/yt2md) for
transcripts and uses the model as the writer.

## Install

**Requirements:** [yt2md](https://github.com/FrancyJGLisboa/yt2md) on PATH, a JS
runtime for yt-dlp (`deno`/node/bun), and Chrome/Chromium (or wkhtmltopdf) for the
PDF step. Only the Claude Code path is verified locally; the others follow each
platform's published format.

### Claude Code

```
/plugin marketplace add FrancyJGLisboa/last30daysYT
/plugin install last30daysYT@last30daysYT
```
Restart, then run `/last30daysYT <topic>` (e.g. `/last30daysYT AI local models`,
`/last30daysYT @veritasium @kurzgesagt`, `/last30daysYT condições climáticas no Sul do Brasil`).

### GitHub Copilot CLI

```
copilot plugin marketplace add FrancyJGLisboa/last30daysYT
copilot plugin install last30daysYT@last30daysYT
```

### Codex

```
npx skills add FrancyJGLisboa/last30daysYT -g
```
(or any [Agent Skills](https://agentskills.io) host)

### Pi agent harness

```
pi install git:github.com/FrancyJGLisboa/last30daysYT
```

## How it works

1. **Fetch** (`scripts/yt_brief.py fetch`) — for a topic, flat-searches a pool,
   drops Shorts and live streams, sorts by view count, and transcribes the top N
   via yt2md (`--since` = last 30 days). For channels, pulls each channel's newest
   videos in the window. Writes `digest.md` (transcripts) + `stats.json` (counts,
   view counts).
2. **Write** — the model reads the digest and writes `report.html`: headline,
   TL;DR, theme sections that teach the idea, timestamped citations, ≥1 chart.
3. **Render** (`scripts/yt_brief.py render`) — HTML → sibling PDF, then opens it.

## Requirements

- [yt2md](https://github.com/FrancyJGLisboa/yt2md) on PATH
  (`uv tool install git+https://github.com/FrancyJGLisboa/yt2md`)
- A JS runtime for yt-dlp: `deno` (or node/bun) — `brew install deno`
- Google Chrome / Chromium (or wkhtmltopdf / weasyprint) for the PDF step

## Usage (as a Claude Code skill)

```
/last30daysYT AI local models
/last30daysYT @veritasium @kurzgesagt
/last30daysYT condições climáticas no Sul do Brasil     # any language
/last30daysYT                                            # standing channels only
```

Maintain your standing channels in `skills/last30daysYT/config/channels.txt` (one
`/videos` URL per line). See `skills/last30daysYT/SKILL.md` for the full contract.

## Direct CLI

```bash
cd skills/last30daysYT
python3 scripts/yt_brief.py fetch "hardware for AI models" --lang en \
  --days 30 --out ./out --cookies-from-browser chrome
python3 scripts/yt_brief.py render ./out/report.html
python3 scripts/yt_brief.py selfcheck
```

## Known limits (read these)

- A topic is a **global** YouTube search layered on channels — it can't search
  *inside* a channel.
- Ranking is by **view count**, which skews toward older videos; a tight window
  can return few. Raise `--rank-pool` or `--days`.
- **HTTP 429** is the main failure under repeat/scale use. Run with
  `--cookies-from-browser chrome` (authenticated = higher limits), or wait and
  re-run (it resumes — already-fetched videos are skipped).
- Engagement is a prefilter, not a verdict. Substance filtering is the model's
  job: it drops clickbait/filler from the newsletter and says what it dropped.
