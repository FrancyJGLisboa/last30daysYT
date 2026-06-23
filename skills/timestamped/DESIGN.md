# Timestamped — Design System

The visual contract every generated newsletter follows. The writer step in
`SKILL.md` must produce HTML that satisfies this; `scripts/eval_depth.py` and
(later) the Impeccable slop detector enforce it. When in doubt, the rule here
wins over improvisation — a regenerated artifact must look like the same product
every time, across every topic and language.

## 1. Brand

- **Name:** Timestamped
- **Subtitle:** *the last 30 days of any topic on YouTube*
- **Essence:** verification you can click. Every claim cited to the exact second;
  the big claims corroborated against an outside source.
- **Voice:** editorial, sober, citation-first. Lead with the point, attribute the
  source, never hype. Honest hedging over confident hand-waving.

## 2. The signature — what makes it recognizably *Timestamped*

Two elements ARE the brand. Neither is optional:

1. **Timestamp pill** — every substantive claim ends in a **monospace `[MM:SS]`
   pill** linking `https://youtu.be/ID?t=SEC`. This is the namesake element.
2. **Confidence chip** — `confirmed` / `single source` / `overstated`, inline at
   each headline claim, linking the outside source where one exists.

If a draft has claims without pills, or headline claims without chips, it is
off-brand — fix it before shipping.

## 3. Color tokens

```
--ink:    #15191e   /* body text */
--muted:  #6b7280   /* meta, captions */
--line:   #e6e8eb   /* rules, borders */
--accent: #0a7d4d   /* kicker, headings, brand — deep green; the ONLY accent */
--bg:     #fbfcfb
--link:   #0b50a0
```

Component colors (do not introduce others):

| Element | Background | Text |
|---|---|---|
| chip · confirmed | `#e3f3ea` | `#0a7d4d` |
| chip · single source | `#fef1df` | `#9a5b06` |
| chip · overstated | `#fde7e7` | `#b42318` |
| timestamp pill | `#eef2f7` | `#0b50a0` |

## 4. Typography

- **Body:** Georgia / "Times New Roman", serif, `17px / 1.65`. Column max **760px**.
- **Labels** (kicker, meta, chips, table head): `-apple-system, Segoe UI`, sans.
- **Timestamps + numeric table cells:** `ui-monospace, SFMono-Regular, Menlo`,
  mono — the signature register. Tabular numerals.
- **Scale (use these sizes only):** H1 `2.05rem/1.16` · hook `1.16rem` italic ·
  H2 `13px` caps tracked accent · H3 `1.22rem` · chip `9.5px` · pill `12.5px`.

## 5. Components

Built for the skim (inverted pyramid): hook the 5-second reader at the top,
reward the digger below.

- **Masthead:** kicker `TIMESTAMPED · topic brief` → **punchy one-line H1** →
  **hero takeaway** (`.hero-take`, the single biggest "so what", bold, one line).
  No clause-stuffed hook, no meta yet.
- **"In 30 seconds" card:** 3–5 **one-line** bullets (≤120 chars), each = takeaway
  + `[MM:SS]` pill + confidence chip as a faint **end-of-line** tag (`.conf.end`),
  never mid-sentence. The whole block skims in under 10 seconds.
- **Meta line + chip legend** sit **below** the card — value first, friction second.
- **Theme section:** H2 theme label → H3 claim (+ chip) → plain-language teach →
  blockquote (verbatim, attributed, pill) → `why it matters` line.
- **Runs table** (`table.runs`): the actionable decision table; numeric cells mono.
- **Engagement chart:** one inline-CSS horizontal bar chart (§8), accent fill,
  velocity/views. Never decorative; one per newsletter.
- **Worth watching / On the radar / Footer:** sans, muted, compact.

## 6. Layout & rhythm

760px column, generous whitespace, short paragraphs. Section air: ~2.4rem above
H2, ~1.4rem above H3. Cards and tables: `1px var(--line)` border, no shadows.

## 7. Print (PDF) — first-class, not an afterthought

- `print-color-adjust: exact` so chips and pills keep their backgrounds in PDF.
- `break-inside: avoid` on the TL;DR card, tables, and blockquotes.
- Timestamps stay pills (not raw blue underlines); source links stay subtle.

## 8. Chart

**Inline CSS bars, no JavaScript, no CDN.** One engagement chart per newsletter —
horizontal bars built from plain HTML/CSS (`.bars`/`.bar` in the sample), widths
as a percentage of the max. This renders identically in HTML and PDF and needs
no network — a Chart.js-from-CDN canvas renders blank in headless-Chrome PDF
(captured before the script loads), and dropping the external script also
removes the supply-chain surface entirely (no pin/SRI to maintain). Accent fill,
tabular-numeric value labels, one chart only, never decorative.

## 9. Slop guards (pre-figures the Impeccable detector — never do these)

- a substantive claim with no timestamp pill
- a headline claim with no confidence chip
- uncertainty pooled only at the end instead of inline with the claim
- blue-underline link soup — timestamps are pills, sources are subtle
- more than one accent color · gradients · drop shadows · emoji
- system-default sans body (serif body is the register)
- font sizes off the scale in §4
- **em-dash overuse** — keep em-dashes sparse; in long passages prefer commas,
  colons, periods, or parentheses. A pile of em-dashes is an AI-cadence tell.

## 10. Automated enforcement

Two deterministic gates run on every generated newsletter (the verify step):

- **Content depth + scannability** — `scripts/eval_depth.py report.html`: the
  D1–D6 depth checks plus S1–S3 (hero takeaway before the meta, one-line TL;DR
  bullets ≤120 chars, no paragraph over 420 chars).
- **Design slop** — `scripts/design_eval.sh report.html`, which runs
  [Impeccable](https://impeccable.style)'s no-LLM 44-rule detector
  (`npx impeccable detect`). Exit 0 = clean.

The detector is tuned for short React/SaaS UIs, so `.impeccable/config.json`
suppresses four rules that fight this product's deliberate, long-form editorial
identity (each is a considered decision, not silencing a real defect):

| Suppressed rule | Why |
|---|---|
| `hero-eyebrow-chip` | The masthead kicker is an intentional newspaper kicker (§5) |
| `numbered-section-markers` | False positive: the minute digits of `[MM:SS]` pills (§2) |
| `all-caps-body` | Uppercase is confined to labels/headings — kicker, h2, chips (§4) |
| `em-dash-overuse` | Threshold is for short SaaS copy; this is long-form editorial (guarded above) |
