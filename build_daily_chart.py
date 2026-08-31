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

    parts = ['<svg class="chartsvg" viewBox="0 0 1080 260" xmlns="http://www.w3.org/2000/svg">']
    parts.append(f'<line x1="{X_LEFT}" y1="{Y_BOTTOM}" x2="{X_RIGHT}" y2="{Y_BOTTOM}" stroke="#e3e5e9"/>')

    pts_s = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys_s))
    pts_o = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys_o))
    parts.append(f'<polyline points="{pts_s}" fill="none" stroke="#0891b2" stroke-width="2.4"/>')
    parts.append(f'<polyline points="{pts_o}" fill="none" stroke="#b91c1c" stroke-width="2.4"/>')

    for i in range(n):
        d = dates[i]
        md = f"{int(d[5:7])}/{int(d[8:10])}"
        parts.append(
            f'<circle cx="{xs[i]:.1f}" cy="{ys_s[i]:.1f}" r="9" fill="#0891b2" opacity="0" '
            f'data-tip="{d} セッション数：{sessions[i]:,}"/>'
            f'<circle cx="{xs[i]:.1f}" cy="{ys_s[i]:.1f}" r="3.5" fill="#0891b2"/>'
            f'<circle cx="{xs[i]:.1f}" cy="{ys_o[i]:.1f}" r="9" fill="#b91c1c" opacity="0" '
            f'data-tip="{d} EC注文数：{orders[i]}件"/>'
            f'<circle cx="{xs[i]:.1f}" cy="{ys_o[i]:.1f}" r="3.5" fill="#b91c1c"/>'
        )
        parts.append(
            f'<text x="{xs[i]:.1f}" y="246" font-size="10.5" fill="#6b7280" text-anchor="middle">{md}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def build_stat_cards(rows):
    """3日分未満はまだ折れ線として意味を持たないため、実数カードで見せる。"""
    last = rows[-1]
    sessions = int(last["sessions"])
    orders = int(last["orders"])
    cards = [
        ("セッション数", f"{sessions:,}", "#0891b2"),
        ("EC注文数（CV）", f"{orders}件", "#b91c1c"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="l">{label}（{last["date"]}）</div>'
        f'<div class="v" style="color:{color}">{value}</div></div>'
        for label, value, color in cards
    )
    return f'<div class="kpis" style="margin-bottom:0">{kpi_html}</div>'


def build_section(rows):
    n = len(rows)
    last_date = rows[-1]["date"]
    body = build_stat_cards(rows) if n < 3 else build_svg(rows)
    if n < 3:
        note = (
            f"データが{n}日分のみのため折れ線ではなく実数カードで表示しています"
            f"（2026年8月31日〜、最終更新：{last_date}）。3日分以上たまり次第、自動で折れ線グラフに切り替わります。"
        )
    else:
        note = (
            f"{n}日分のデータ（2026年8月31日〜、最終更新：{last_date}）。"
            f"各系列は表示期間内の最大値を100として正規化。点にカーソルを合わせると実数が表示されます。"
        )
    legend = (
        '<div class="legend"><div class="li"><span class="sw" style="background:#0891b2"></span>セッション数</div>'
        '<div class="li"><span class="sw" style="background:#b91c1c"></span>EC注文数（CV）</div></div>'
        if n >= 3 else ""
    )
    return (
        f'{START}\n'
        f'<h2 class="sec">日次トラッキング：セッション数とEC注文数（CV） '
        f'<span class="tag">2026年8月31日〜・毎日更新</span></h2>\n'
        f'<div class="card">\n'
        f'{legend}\n'
        f'{body}\n'
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
