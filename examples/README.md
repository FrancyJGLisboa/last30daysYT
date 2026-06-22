# Examples

Real, unedited output from a live `last30daysYT` run — not a mockup.

## AI local models (topic mode)

- **[ai-local-models-topic.html](ai-local-models-topic.html)** · **[ai-local-models-topic.pdf](ai-local-models-topic.pdf)**

Generated from: `/last30daysYT AI local models`

How it was produced:
- Flat-searched a 45-video candidate pool, dropped Shorts and live streams,
  ranked by view count, and transcribed the top 5 in-window videos
  (552k → 322k views) via [yt2md](https://github.com/FrancyJGLisboa/yt2md).
- The model read the transcripts and wrote the newsletter: headline + hook,
  TL;DR, theme sections that teach the idea, an engagement chart, and a
  "worth watching" / "on the radar" close.
- Every substantive claim links to the exact timestamp in the source video
  (`https://youtu.be/ID?t=SECONDS`).

> Note: the window was widened to 90 days to fill the set — ranking by raw view
> count skews toward older videos, so a strict 30-day window returns fewer.
> Engagement is a prefilter; substance was judged from the transcripts.
