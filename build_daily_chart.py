#!/usr/bin/env python3
"""日次セッション数・EC注文数（CV）チャートを shopify-dashboard.html に反映する。

使い方：
1. daily_metrics.csv に新しい日の行（date,sessions,orders）を追記する
2. python3 build_daily_chart.py を実行する
3. git add/commit/push する

DAILY_CHART_START/END のコメントで囲まれた範囲だけを毎回まるごと置き換えるので、
このスクリプトは何度実行しても安全（冪等）。
"""
import csv
import re
from pathlib import Path

BASE = Path(__file__).parent
CSV_PATH = BASE / "daily_metrics.csv"
HTML_PATH = BASE / "shopify-dashboard.html"

START = "<!-- DAILY_CHART_START -->"
END = "<!-- DAILY_CHART_END -->"

Y_TOP, Y_BOTTOM = 20.0, 230.0
X_LEFT, X_RIGHT = 52.0, 1070.0


def load_rows():
    with open(CSV_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def x_positions(n):
    if n == 1:
        return [ (X_LEFT + X_RIGHT) / 2 ]
    step = (X_RIGHT - X_LEFT) / (n - 1)
    return [X_LEFT + i * step for i in range(n)]


def y_positions(values):
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        return [ (Y_TOP + Y_BOTTOM) / 2 for _ in values ]
    return [Y_BOTTOM - (v - vmin) / (vmax - vmin) * (Y_BOTTOM - Y_TOP) for v in values]


def build_svg(rows):
    dates = [r["date"] for r in rows]
    sessions = [int(r["sessions"]) for r in rows]
    orders = [int(r["orders"]) for r in rows]
    n = len(rows)
    xs = x_positions(n)
    ys_s = y_positions(sessions)
    ys_o = y_positions(orders)

    # データ点が1つだけの場合は正規化すると2系列が同じ位置に重なって見分けが
    # つかなくなるため、左右にずらして両方をクリック・視認できるようにする。
    xs_s, xs_o = list(xs), list(xs)
    if n == 1:
        ys_s, ys_o = [80.0], [170.0]
        xs_s, xs_o = [xs[0] - 14], [xs[0] + 14]

    parts = ['<svg class="chartsvg" viewBox="0 0 1080 260" xmlns="http://www.w3.org/2000/svg">']

    if n > 1:
        pts_s = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs_s, ys_s))
        pts_o = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs_o, ys_o))
        parts.append(f'<polyline points="{pts_s}" fill="none" stroke="#0891b2" stroke-width="2.4"/>')
        parts.append(f'<polyline points="{pts_o}" fill="none" stroke="#b91c1c" stroke-width="2.4"/>')

    for i in range(n):
        d = dates[i]
        md = f"{int(d[5:7])}/{int(d[8:10])}"
        parts.append(
            f'<circle cx="{xs_s[i]:.1f}" cy="{ys_s[i]:.1f}" r="9" fill="#0891b2" opacity="0" '
            f'data-tip="{d} セッション数：{sessions[i]:,}"/>'
            f'<circle cx="{xs_s[i]:.1f}" cy="{ys_s[i]:.1f}" r="3" fill="#0891b2"/>'
            f'<circle cx="{xs_o[i]:.1f}" cy="{ys_o[i]:.1f}" r="9" fill="#b91c1c" opacity="0" '
            f'data-tip="{d} EC注文数：{orders[i]}件"/>'
            f'<circle cx="{xs_o[i]:.1f}" cy="{ys_o[i]:.1f}" r="3" fill="#b91c1c"/>'
        )
        parts.append(
            f'<text x="{xs[i]:.1f}" y="246" font-size="10.5" fill="#6b7280" text-anchor="middle">{md}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def build_section(rows):
    n = len(rows)
    last_date = rows[-1]["date"]
    svg = build_svg(rows)
    note = f"{n}日分のデータ（2026年8月31日〜、最終更新：{last_date}）。点にカーソルを合わせると実数が表示されます。"
    return (
        f'{START}\n'
        f'<h2 class="sec">日次トラッキング：セッション数とEC注文数（CV） '
        f'<span class="tag">2026年8月31日〜・毎日更新</span></h2>\n'
        f'<div class="card">\n'
        f'<div class="legend"><div class="li"><span class="sw" style="background:#0891b2"></span>セッション数</div>'
        f'<div class="li"><span class="sw" style="background:#b91c1c"></span>EC注文数（CV）</div></div>\n'
        f'{svg}\n'
        f'<div class="desc" style="margin:10px 0 0">{note}</div>\n'
        f'</div>\n'
        f'{END}'
    )


def main():
    rows = load_rows()
    section = build_section(rows)
    html = HTML_PATH.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if pattern.search(html):
        html = pattern.sub(section, html)
    else:
        anchor = '<h2 class="sec">流入経路別の購入ファネル'
        html = html.replace(anchor, section + "\n" + anchor, 1)
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"updated: {HTML_PATH} ({len(rows)} days)")


if __name__ == "__main__":
    main()
