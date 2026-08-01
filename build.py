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


def render_report(env, tmpl, data, all_dates):
    """Render a single date's data into reports/<date>.html, using the full,
    current all_dates list for its calendar (so every report -- old or new --
    always shows every known date, not just the ones that existed when that
    particular file happened to be written)."""
    data = add_dday_to_earnings_dates(data)
    date = data["date"]

    common = dict(
        date=date,
        date_kr=data["date_kr"],
        indices=data["indices"],
        tickers=data["tickers"],
        crypto_meta=data.get("crypto_meta"),
        news_pool_json=json.dumps(data["news_pool"], ensure_ascii=False),
    )

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
    return common


def main():
    if len(sys.argv) != 2:
        print("usage: build.py data/<date>.json", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        new_data = json.load(f)
    new_date = new_data["date"]

    env = Environment(loader=FileSystemLoader(REPO_ROOT), autoescape=False, trim_blocks=True, lstrip_blocks=True)
    tmpl = env.get_template("template.html.j2")

    # Ensure today's own report file is in the history list too (it may not be
    # written to reports/ yet, so glob won't see it -> add manually then dedupe).
    all_dates = sorted(set(build_history() + [new_date]), reverse=True)

    # Re-render EVERY known date's reports/<date>.html, not just the one passed
    # in, so every report's calendar always reflects the full, current list of
    # dates. Otherwise a report built before today's date existed stays frozen
    # showing only the dates that existed at the time it was built, with no way
    # to navigate forward to newer reports (incl. "today") from it.
    data_dir = os.path.join(REPO_ROOT, "data")
    latest_common = None
    for d in all_dates:
        if d == new_date:
            common = render_report(env, tmpl, new_data, all_dates)
        else:
            data_path = os.path.join(data_dir, f"{d}.json")
            if not os.path.isfile(data_path):
                print(f"warning: no data/{d}.json found, skipping re-render of reports/{d}.html", file=sys.stderr)
                continue
            with open(data_path, encoding="utf-8") as f:
                old_data = json.load(f)
            common = render_report(env, tmpl, old_data, all_dates)
        if d == all_dates[0]:  # most recent date -> what index.html should show
            latest_common = common

    # --- Render index.html (root) as the most recent date ---
    index_history = [{"label": d, "url": f"reports/{d}.html"} for d in all_dates]
    index_html = tmpl.render(
        history=index_history,
        history_json=json.dumps(index_history, ensure_ascii=False),
        **latest_common,
    )
    index_path = os.path.join(REPO_ROOT, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"wrote {index_path}")


if __name__ == "__main__":
    main()
