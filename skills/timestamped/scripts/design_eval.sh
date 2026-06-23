#!/usr/bin/env sh
# Design eval — the visual twin of eval_depth.py.
#
# Runs Impeccable's deterministic, no-LLM 44-rule slop detector against the
# generated newsletter and exits non-zero on any finding (exit codes for the
# build). It honors .impeccable/config.json at the repo root — the Timestamped
# suppressions (deliberate kicker, the [MM:SS]-pill false positive, label-only
# all-caps, editorial em-dash tolerance) documented in DESIGN.md §9.
#
# Usage: design_eval.sh [report.html]   (default: /tmp/timestamped/report.html)
exec npx impeccable detect "${1:-/tmp/timestamped/report.html}"
