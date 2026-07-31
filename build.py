#!/usr/bin/env python3
"""Render today's stock brief into reports/<date>.html and index.html.

Usage: python3 build.py data/2026-07-30.json
"""
import json
import sys
import glob
import os
import re
from datetime import date as _date
from jinja2 import Environment, FileSystemLoader

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def add_dday_to_earnings_dates(data):
    """Append a computed (D-N)/(D-DAY)/(D+N) suffix to any '다음 실적발표일' row
    value, based on the report's own date. Daily data JSON only needs the plain
    date string; the rendered site always shows an accurate day-count."""
    report_date = _date.fromisoformat(data["date"])
    for t in data.get("tickers", []):
        for tab in t.get("tabs", []):
            for row in tab.get("rows", []):
                if row.get("label") != "다음 실적발표일":
                    continue
                m = _DATE_RE.match(row.get("value", ""))
                if not m:
                    continue
                target = _date.fromisoformat(m.group(1))
                delta = (target - report_date).days
                if delta > 0:
                    dday = f"D-{delta}"
                elif delta == 0:
                    dday = "D-DAY"
                else:
                    dday = f"D+{abs(delta)}"
                row["value"] = f"{row['value']} ({dday})"
    return data


def build_history():
    """Return sorted (desc) list of date strings for all existing reports/*.html files."""
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

    data = add_dday_to_earnings_dates(data)

    date = data["date"]  # e.g. "2026-07-30"

    env = Environment(loader=FileSystemLoader(REPO_ROOT), autoescape=False, trim_blocks=True, lstrip_blocks=True)
    tmpl = env.get_template("template.html.j2")

    # Ensure today's own report file exists in the history list too (it's written
    # in this same run, so glob won't see it yet -> add manually then dedupe).
    all_dates = sorted(set(build_history() + [date]), reverse=True)

    common = dict(
        date=date,
        date_kr=data["date_kr"],
        indices=data["indices"],
        tickers=data["tickers"],
        crypto_meta=data.get("crypto_meta"),
        news_pool_json=json.dumps(data["news_pool"], ensure_ascii=False),
    )

    # --- Render reports/<date>.html (nested one level under reports/) ---
    # sibling files inside reports/, and the current day's own file just points to itself (fine)
    report_history = [{"label": d, "url": f"{d}.html"} for d in all_dates]
    report_html = tmpl.render(
        history=report_history,
        history_json=json.dumps(report_history, ensure_ascii=False),
        **common,
    )
    os.makedirs(os.path.join(REPO_ROOT, "reports"), exist_ok=True)
    report_path = os.path.join(REPO_ROOT, "reports", f"{date}.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_html)
    print(f"wrote {report_path}")

    # --- Render index.html (root) ---
    index_history = [{"label": d, "url": f"reports/{d}.html"} for d in all_dates]
    index_html = tmpl.render(
        history=index_history,
        history_json=json.dumps(index_history, ensure_ascii=False),
        **common,
    )
    index_path = os.path.join(REPO_ROOT, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"wrote {index_path}")


if __name__ == "__main__":
    main()
