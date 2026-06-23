#!/usr/bin/env python3
"""Depth eval for a last30daysYT newsletter — the loss function as a script.

Scores a rendered newsletter HTML against the binary "depth, not shallow"
checks. Mechanical checks gate (exit 1 on any fail); D6 (novelty) is a
human judgement, reported but not gated.

    python3 eval_depth.py path/to/report.html

D1  every theme claim (h3) carries an inline confidence marker
D2  >=1 actionable table (a decision a practitioner could act on)
D3  ranking is velocity-based (yt_brief selfcheck passes)
D4  uncertainty travels inline, not pooled only at the end
D5  >=2 source types: at least one corroborating non-YouTube link
D6  novelty: >=3 things a topic-follower didn't know  [MANUAL]
"""
import re
import subprocess
import sys
from pathlib import Path

CONF = re.compile(r'class="conf[^"]*"', re.I)  # inline confidence markers
H3 = re.compile(r"<h3\b", re.I)
TABLE_ROWS = re.compile(r"<tr\b", re.I)
HREF = re.compile(r'href="([^"]+)"', re.I)


def check(html: str, scripts_dir: Path) -> list[tuple[str, bool, str]]:
    body = html
    # split off the forward-looking "on the radar" tail so D4 can require
    # uncertainty earlier than it.
    m = re.search(r'on[\s_-]*the[\s_-]*radar', html, re.I)
    before_radar = html[: m.start()] if m else html

    n_h3 = len(H3.findall(body))
    n_conf = len(CONF.findall(body))
    d1 = n_conf >= n_h3 and n_h3 > 0

    d2 = len(TABLE_ROWS.findall(body)) >= 3

    selfcheck = subprocess.run(
        [sys.executable, str(scripts_dir / "yt_brief.py"), "selfcheck"],
        capture_output=True, text=True)
    d3 = selfcheck.returncode == 0

    d4 = bool(CONF.search(before_radar))

    ext = [h for h in HREF.findall(body)
           if "://" in h
           and "youtube.com" not in h and "youtu.be" not in h
           and "jsdelivr" not in h and "cdn." not in h]
    d5 = len(ext) >= 1

    return [
        ("D1 inline confidence on every claim", d1, f"{n_conf} markers / {n_h3} h3-claims"),
        ("D2 actionable table", d2, f"{len(TABLE_ROWS.findall(body))} table rows"),
        ("D3 velocity ranking (selfcheck)", d3, selfcheck.stdout.strip() or selfcheck.stderr.strip()),
        ("D4 uncertainty inline, not only at end", d4, "marker before 'on the radar'" if d4 else "no inline marker before tail"),
        ("D5 >=1 corroborating external link", d5, f"{len(ext)} external link(s)"),
    ]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: eval_depth.py report.html", file=sys.stderr)
        return 2
    html = Path(sys.argv[1]).read_text()
    scripts_dir = Path(__file__).resolve().parent
    rows = check(html, scripts_dir)
    print(f"depth eval — {sys.argv[1]}\n")
    for name, ok, detail in rows:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:40s} {detail}")
    print("  [MANUAL] D6 novelty (>=3 new things for a follower) — human call")
    failed = [n for n, ok, _ in rows if not ok]
    print(f"\n{'ALL MECHANICAL CHECKS PASS' if not failed else 'FAILED: ' + ', '.join(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
