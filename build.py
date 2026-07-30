#!/usr/bin/env python3
"""Render today's stock brief into reports/<date>.html and index.html.

Usage: python3 build.py data/2026-07-30.json
"""
import json
import sys
import glob
import os
from jinja2 import Environment, FileSystemLoader

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def build_history(exclude_date=None):
    """Return sorted (desc) list of {date, label} for all existing reports/*.html files."""
    files = glob.glob(os.path.join(REPO_ROOT, "reports", "*.html"))
    dates = sorted(
        (os.path.splitext(os.path.basename(f))[0] for f in files),
        reverse=True,
    )
    return dates


def main():
    if len(sys.argv) != 2:
        print("usage: build.py data/<date>.json", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)

    date = data["date"]  # e.g. "2026-07-30"

    env = Environment(loader=FileSystemLoader(REPO_ROOT), autoescape=False, trim_blocks=True, lstrip_blocks=True)
    tmpl = env.get_template("template.html.j2")

    # Ensure today's own report file exists in the history list too (it's written
    # in this same run, so glob won't see it yet -> add manually then dedupe).
    all_dates = sorted(set(build_history() + [date]), reverse=True)

    # --- Render reports/<date>.html (nested one level under reports/) ---
    # sibling files inside reports/, and the current day's own file just points to itself (fine)
    report_history = [{"label": d, "url": f"{d}.html"} for d in all_dates]
    report_html = tmpl.render(
        date_kr=data["date_kr"],
        headlines=data["headlines"],
        tickers=data["tickers"],
        history=report_history,
        home_url="../index.html",
    )
    os.makedirs(os.path.join(REPO_ROOT, "reports"), exist_ok=True)
    report_path = os.path.join(REPO_ROOT, "reports", f"{date}.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_html)
    print(f"wrote {report_path}")

    # --- Render index.html (root) ---
    index_history = [{"label": d, "url": f"reports/{d}.html"} for d in all_dates]
    index_html = tmpl.render(
        date_kr=data["date_kr"],
        headlines=data["headlines"],
        tickers=data["tickers"],
        history=index_history,
        home_url="index.html",
    )
    index_path = os.path.join(REPO_ROOT, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"wrote {index_path}")


if __name__ == "__main__":
    main()
