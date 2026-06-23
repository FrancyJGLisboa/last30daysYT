#!/usr/bin/env sh
# Design eval — the visual twin of eval_depth.py.
#
# Runs Impeccable's deterministic, no-LLM 44-rule slop detector against the
# generated newsletter and exits non-zero on any finding (exit codes for the
# build). Exit 0 = clean.
#
# Impeccable resolves .impeccable/config.json from the CURRENT directory, not
# the target file — so this wrapper cd's to the plugin root that holds the
# config before running, making the gate work no matter where it's invoked from
# (real runs put the report in /tmp). The config carries the Timestamped
# suppressions documented in DESIGN.md §9.
#
# Usage: design_eval.sh [report.html]   (default: /tmp/timestamped/report.html)
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$script_dir/../../.." && pwd)   # repo/plugin root holds .impeccable

report=${1:-/tmp/timestamped/report.html}
case "$report" in
  /*) ;;                                                # already absolute
  *)  report=$(CDPATH= cd -- "$(dirname -- "$report")" && pwd)/$(basename -- "$report") ;;
esac

cd "$root" || exit 1
exec npx impeccable detect "$report"
