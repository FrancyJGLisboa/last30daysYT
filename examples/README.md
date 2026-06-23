# Examples

Real, unedited output from a live `last30daysYT` run — not a mockup.

## AI local models (topic mode)

- **[ai-local-models-topic.html](ai-local-models-topic.html)** · **[ai-local-models-topic.pdf](ai-local-models-topic.pdf)**

Generated from: `/last30daysYT AI local models`

How it was produced:
- Flat-searched a candidate pool, dropped Shorts and live streams, transcribed
  the top in-window videos via [yt2md](https://github.com/FrancyJGLisboa/yt2md),
  then **velocity-ranked** them (views/day) so fresh videos aren't buried under
  older ones that simply had longer to accrue views.
- The model read the transcripts and wrote the newsletter: headline + hook,
  TL;DR, theme sections that teach the idea, an engagement chart, and a
  "worth watching" / "on the radar" close.
- **Corroboration pass:** each headline claim was checked against a source
  outside the videos and tagged inline `confirmed` / `single source` /
  `overstated` — which is why the GLM 5.2 "beats everything" claim is corrected
  to "wins SWE-bench Pro, trails Terminal-Bench, at 1/6 the cost."
- Every substantive claim links to the exact timestamp in the source video
  (`https://youtu.be/ID?t=SECONDS`); corroborated ones also link the outside source.
- Scored against the depth checks with
  [`scripts/eval_depth.py`](../skills/last30daysYT/scripts/eval_depth.py) — all pass.

> Note: the window was widened to 90 days to fill the set — even with velocity
> ranking, a strict 30-day window on this niche returned too few survivors.
> Engagement is a prefilter; substance was judged from the transcripts.
