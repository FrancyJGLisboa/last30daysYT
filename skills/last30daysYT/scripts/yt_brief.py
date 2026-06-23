#!/usr/bin/env python3
"""last30daysYT orchestrator — thin wrapper around the yt2md CLI.

Two subcommands:
  fetch   pull last-N-days transcripts for a channel list (+ optional topic),
          write digest.md + stats.json for the model to synthesize a report.
  render  turn a model-written report.html into a sibling PDF and open both.

The model does the report writing; this script only does the mechanical parts.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

# digest size guard: cap each transcript only if the combined digest would blow
# past the model's context. ponytail: blunt char cap, upgrade to relevance-ranked
# chunking only if it ever truncates material that mattered.
DIGEST_BUDGET = 150_000
PER_VIDEO_CAP = 12_000


def _yt2md() -> str:
    """Path to the installed yt2md CLI."""
    return shutil.which("yt2md") or os.path.expanduser("~/.local/bin/yt2md")


def _ytdlp_python() -> str:
    """The Python inside yt2md's venv — the one that has yt-dlp installed.
    Read from the yt2md launcher's shebang so we don't hardcode the uv path."""
    try:
        first = Path(_yt2md()).read_text(errors="ignore").splitlines()[0]
        if first.startswith("#!") and os.path.exists(cand := first[2:].strip()):
            return cand
    except Exception:
        pass
    return sys.executable


def rank_topic(topic: str, pool: int, want: int, min_dur: int,
               cookies: str | None = None) -> list[tuple[str, int, str]]:
    """Cheap engagement pre-rank: flat-search a big pool, drop Shorts and live
    streams, sort by view count, return the top `want` as (video_id, views, title).
    Flat search exposes view_count/duration/live_status without a per-video fetch.
    Returns [] on any failure so the caller can fall back to yt2md --search."""
    cmd = [_ytdlp_python(), "-m", "yt_dlp", "--flat-playlist", "-j", "--no-warnings"]
    if cookies:
        cmd += ["--cookies-from-browser", cookies]
    cmd += [f"ytsearch{pool}:{topic}"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except Exception:
        return []
    cands: list[tuple[int, str, str]] = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (e.get("live_status") or "") in ("is_live", "is_upcoming"):
            continue
        dur = e.get("duration") or 0
        if dur and dur < min_dur:  # skip Shorts / clips
            continue
        vid = e.get("id") or ""
        if not re.fullmatch(r"[\w-]{11}", vid):
            continue
        cands.append((e.get("view_count") or 0, vid, e.get("title") or ""))
    cands.sort(key=lambda c: -c[0])
    return [(vid, vc, title) for vc, vid, title in cands[:want]]


def _velocity(views: int | None, uploaded: str) -> float:
    """views per day since upload — engagement that accounts for how long a
    video has had to accrue it. 0.0 when views or the date are unknown."""
    if not views:
        return 0.0
    try:
        age = (date.today() - date.fromisoformat(uploaded)).days
    except ValueError:
        return 0.0
    return views / max(age, 1)


def _read_channels(path: Path) -> list[str]:
    """Channel/playlist URLs from a channels.txt (# = comment, blanks ignored)."""
    if not path.is_file():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


_HDR = {
    "video": re.compile(r"\*\*Video:\*\*\s*<?(\S+?)>?\s*$", re.M),
    "channel": re.compile(r"\*\*Channel:\*\*\s*(?:\[([^\]]+)\]\([^)]*\)|(.+?))\s*$", re.M),
    "uploaded": re.compile(r"\*\*Uploaded:\*\*\s*(\S+)", re.M),
    "captions": re.compile(r"\*\*Captions:\*\*\s*(.+)", re.M),
}


def parse_header(text: str) -> dict:
    """Pull metadata out of a yt2md transcript file's header block."""
    title_m = re.match(r"#\s*(.+)", text)
    url = (_HDR["video"].search(text) or [None, ""])[1] if _HDR["video"].search(text) else ""
    vid_m = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", url)
    ch_m = _HDR["channel"].search(text)
    channel = (ch_m.group(1) or ch_m.group(2)).strip() if ch_m else "unknown"
    up_m = _HDR["uploaded"].search(text)
    cap_m = _HDR["captions"].search(text)
    captions = bool(cap_m) and "none found" not in cap_m.group(1).lower()
    return {
        "title": title_m.group(1).strip() if title_m else "untitled",
        "url": url,
        "video_id": vid_m.group(1) if vid_m else "",
        "channel": channel,
        "uploaded": up_m.group(1).strip() if up_m else "unknown",
        "captions": captions,
    }


def cmd_fetch(args) -> int:
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    since = (date.today() - timedelta(days=args.days)).isoformat()

    # inline --channel URLs (passed by the skill from the user's args) take the
    # place of channels.txt when given; the file is the standing default.
    inline = [c.strip() for c in (args.channel or []) if c.strip()]
    channels = inline or _read_channels(Path(args.channels).expanduser())
    topic = (args.topic or "").strip()
    if not channels and not topic:
        print("nothing to fetch: empty channels.txt and no topic given", file=sys.stderr)
        return 2

    cmd = [_yt2md(), "--since", since, "--lang", args.lang,
           "--out-dir", str(out), "--sleep", str(args.sleep)]
    if args.cookies_from_browser:
        cmd += ["--cookies-from-browser", args.cookies_from_browser]

    # Topic: engagement pre-rank (Shorts/live dropped, top by views), transcribe
    # exactly those as watch URLs. Fall back to yt2md's own --search if the
    # pre-rank yields nothing (e.g. yt-dlp hiccup).
    views_by_id: dict[str, int] = {}
    topic_urls: list[str] = []
    if topic:
        ranked = rank_topic(topic, args.rank_pool, args.search_limit,
                            args.min_duration, args.cookies_from_browser)
        if ranked:
            views_by_id = {vid: vc for vid, vc, _ in ranked}
            topic_urls = [f"https://www.youtube.com/watch?v={vid}" for vid, _, _ in ranked]
            print(f"topic '{topic}': pre-ranked {len(ranked)} by views "
                  f"(top {ranked[0][1]:,})", file=sys.stderr)
        else:
            cmd += ["--search", topic, "--search-limit", str(args.search_limit)]

    if channels:
        # Channel /videos listings are newest-first and return the FULL history;
        # --limit caps each to its N newest before the (slow, per-video) date
        # check. ponytail: N newest covers any normal 30-day window; a channel
        # posting >N in the window loses the oldest — raise --per-channel-limit.
        cmd += ["--limit", str(args.per_channel_limit)]

    # positional URLs (inline channels + pre-ranked topic videos) must trail flags
    if inline:
        cmd += inline
    elif channels:
        cmd += ["--from-file", str(Path(args.channels).expanduser())]
    cmd += topic_urls
    print(f"$ {' '.join(cmd)}\n", file=sys.stderr)
    # yt2md exits 1 if any single video failed — that's not fatal for us.
    subprocess.run(cmd, check=False)

    md_files = sorted(p for p in out.rglob("*.md")
                      if p.name not in ("digest.md",) and not p.name.startswith("_"))
    videos, by_channel, by_day = [], {}, {}
    for p in md_files:
        meta = parse_header(p.read_text())
        meta["file"] = str(p)
        meta["views"] = views_by_id.get(meta["video_id"])  # known for topic videos
        videos.append(meta)
        by_channel[meta["channel"]] = by_channel.get(meta["channel"], 0) + 1
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta["uploaded"]):
            by_day[meta["uploaded"]] = by_day.get(meta["uploaded"], 0) + 1

    # Rank for featuring/ordering. velocity (views per day since upload) by
    # default: a fresh video shouldn't sit below an older one that simply had
    # more time to accrue views — the bug raw-view ranking causes in a recency
    # product (it also forced the example's 30d window out to 90d).
    # ponytail: the candidate POOL upstream is still view-only — yt-dlp's flat
    # search exposes no upload date, so velocity is unknowable before fetch.
    # Upgrade path: a per-video date probe (one fetch per candidate) would let
    # the pool itself be velocity-ranked; not worth the 429 risk for the
    # featured-set win this re-rank already gives.
    for v in videos:
        v["velocity"] = _velocity(v["views"], v["uploaded"])
    if args.rank_by == "velocity":
        videos.sort(key=lambda v: (v["views"] is None, -v["velocity"]))
    else:
        videos.sort(key=lambda v: (v["views"] is None, -(v["views"] or 0)))

    stats = {
        "since": since, "until": date.today().isoformat(), "days": args.days,
        "topic": topic, "total_videos": len(videos),
        "with_captions": sum(1 for v in videos if v["captions"]),
        "by_channel": dict(sorted(by_channel.items(), key=lambda kv: -kv[1])),
        "by_day": dict(sorted(by_day.items())),
        "videos": videos,
    }
    (out / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False))

    cap = PER_VIDEO_CAP if sum(p.stat().st_size for p in md_files) > DIGEST_BUDGET else None
    parts = []
    for p in md_files:
        body = p.read_text()
        if cap and len(body) > cap:
            body = body[:cap] + "\n\n_[transcript truncated for length]_\n"
        parts.append(body)
    (out / "digest.md").write_text("\n\n---\n\n".join(parts))

    print(f"\nfetched {len(videos)} videos from {len(by_channel)} channels "
          f"({since}..{stats['until']}), {stats['with_captions']} with captions")
    print(f"digest: {out / 'digest.md'}")
    print(f"stats:  {out / 'stats.json'}")

    # Degraded-run gate: a newsletter can't be written from zero transcripts, so
    # don't exit 0 and let the writer ship a hollow page. Mirrors yt2md's own
    # empty-run contract (exit 2).
    if not videos or stats["with_captions"] == 0:
        why = ("no videos matched" if not videos
               else f"{len(videos)} videos but 0 had captions")
        print(f"\nWARNING: degraded fetch — {why}. Not enough to write a "
              f"newsletter; check --lang matches the topic's language, widen "
              f"--days, or raise --rank-pool.", file=sys.stderr)
        return 2
    return 0


_CHROME_PATHS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)


def _find_chrome():
    """A Chrome/Chromium-family binary for headless PDF, or None."""
    for n in ("google-chrome", "chromium", "chromium-browser", "brave-browser", "microsoft-edge"):
        if (p := shutil.which(n)):
            return p
    return next((p for p in _CHROME_PATHS if os.path.exists(p)), None)


def _html_to_pdf(html_path):
    """HTML file -> sibling PDF. Chrome headless, then wkhtmltopdf, then weasyprint.
    Best-effort: a missing engine returns None, never crashes the run.
    Ported from agro-pulse-br/skills/agro-pulse-br/scripts/agro_brief.py."""
    import signal
    import tempfile
    import time
    pdf = os.path.splitext(html_path)[0] + ".pdf"
    src = "file://" + os.path.abspath(html_path)
    # Remove any stale PDF first: the Chrome poll loop below detects "done" by
    # size-stability, and a leftover file makes it read as stable instantly —
    # returning success while the OLD pdf survives unchanged.
    try:
        os.remove(pdf)
    except OSError:
        pass
    try:
        if (chrome := _find_chrome()):
            # Chrome writes the PDF then frequently does NOT exit, so launch
            # detached, poll until the file size stabilizes, then kill the group.
            proc = subprocess.Popen(
                [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
                 "--no-first-run", "--no-default-browser-check",
                 f"--user-data-dir={tempfile.mkdtemp()}",
                 "--no-pdf-header-footer", f"--print-to-pdf={pdf}", src],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True)
            last, stable = -1, 0
            for _ in range(75):  # up to ~30s
                if proc.poll() is not None:
                    break
                if os.path.exists(pdf):
                    sz = os.path.getsize(pdf)
                    stable = stable + 1 if sz == last and sz > 0 else 0
                    last = sz
                    if stable >= 2:
                        break
                time.sleep(0.4)
            if proc.poll() is None:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except Exception:
                    proc.terminate()
        elif (wk := shutil.which("wkhtmltopdf")):
            subprocess.run([wk, "-q", "--enable-local-file-access", html_path, pdf],
                           check=True, capture_output=True, timeout=90)
        else:
            import weasyprint  # optional; only if installed
            weasyprint.HTML(html_path).write_pdf(pdf)
        return pdf if os.path.exists(pdf) and os.path.getsize(pdf) > 0 else None
    except ImportError:
        print("PDF skipped: no HTML->PDF engine (install Google Chrome or wkhtmltopdf).",
              file=sys.stderr)
    except Exception as e:
        print(f"PDF skipped: {type(e).__name__}", file=sys.stderr)
    return None


def _open_file(path):
    """Open in the OS default app — best-effort, never raises."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        elif sys.platform.startswith("win"):
            os.startfile(path)  # noqa
        elif (xdg := shutil.which("xdg-open")):
            subprocess.run([xdg, path], check=False)
    except Exception:
        pass


def cmd_render(args) -> int:
    html = Path(args.html_path).expanduser()
    if not html.is_file():
        print(f"no such file: {html}", file=sys.stderr)
        return 2
    print(str(html))
    if (pdf := _html_to_pdf(str(html))):
        print(pdf)
    if not args.no_open:
        _open_file(str(html))
    return 0


def cmd_selfcheck(_args) -> int:
    sample = (
        "# Soy Outlook Q2\n\n"
        "- **Video:** <https://www.youtube.com/watch?v=abcdefghijk>\n"
        "- **Channel:** [AgriTalk](https://youtube.com/@agritalk)\n"
        "- **Uploaded:** 2026-06-15\n"
        "- **Duration:** 12:30\n"
        "- **Captions:** en (auto-generated)\n\n---\n\n## Transcript\n"
    )
    m = parse_header(sample)
    assert m["video_id"] == "abcdefghijk", m
    assert m["channel"] == "AgriTalk", m
    assert m["uploaded"] == "2026-06-15", m
    assert m["captions"] is True, m

    plain = sample.replace("[AgriTalk](https://youtube.com/@agritalk)", "AgriTalk")
    plain = plain.replace("en (auto-generated)", "none found")
    m2 = parse_header(plain)
    assert m2["channel"] == "AgriTalk", m2
    assert m2["captions"] is False, m2

    since = (date.today() - timedelta(days=30)).isoformat()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", since), since

    # velocity: a fresh modest-view video must outrank an old high-view one.
    old = date.fromisoformat(since)  # 30 days ago
    fresh = (date.today() - timedelta(days=2)).isoformat()
    assert _velocity(100_000, old.isoformat()) < _velocity(20_000, fresh), "velocity ranking broken"
    assert _velocity(None, fresh) == 0.0 and _velocity(500, "garbage") == 0.0, "velocity guards broken"
    print("selfcheck ok")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="yt_brief")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="pull transcripts -> digest.md + stats.json")
    f.add_argument("topic", nargs="?", default="", help="optional YouTube search topic")
    here = Path(__file__).resolve().parent.parent
    f.add_argument("--channels", default=str(here / "config" / "channels.txt"),
                   help="path to standing channel list (used when no --channel given)")
    f.add_argument("--channel", action="append", metavar="URL",
                   help="inline channel/playlist URL (repeatable); overrides the file")
    f.add_argument("--days", type=int, default=30)
    f.add_argument("--search-limit", type=int, default=15,
                   help="topic: how many top-engagement videos to transcribe (default: 15)")
    f.add_argument("--rank-pool", type=int, default=40,
                   help="topic: candidate pool size to rank by views (default: 40)")
    f.add_argument("--min-duration", type=int, default=90,
                   help="topic: drop videos shorter than N seconds, i.e. Shorts (default: 90)")
    f.add_argument("--rank-by", choices=("velocity", "views"), default="velocity",
                   help="featured-video ordering: velocity=views/day (default), or raw views")
    f.add_argument("--per-channel-limit", type=int, default=40,
                   help="cap each channel to its N newest videos (default: 40)")
    f.add_argument("--lang", default="en")
    f.add_argument("--sleep", type=float, default=3.0)
    f.add_argument("--cookies-from-browser", default=None, metavar="BROWSER",
                   help="load cookies (chrome/safari/firefox) to dodge 429 rate limits")
    f.add_argument("--out", default="/tmp/last30daysYT")
    f.set_defaults(func=cmd_fetch)

    r = sub.add_parser("render", help="report.html -> sibling PDF, then open")
    r.add_argument("html_path")
    r.add_argument("--no-open", action="store_true")
    r.set_defaults(func=cmd_render)

    sub.add_parser("selfcheck", help="assert header parsing + date math").set_defaults(
        func=cmd_selfcheck)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
