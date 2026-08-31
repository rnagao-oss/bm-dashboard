#!/usr/bin/env python3
"""セッション数とEC注文数（CV）を月次／週次／日次タブで切り替えられるセクションを
shopify-dashboard.html に反映する。

使い方：
1. 日次は daily_metrics.csv に新しい日の行（date,sessions,orders）を追記する
   月次／週次は月末・週末に monthly_metrics.csv / weekly_metrics.csv に行を追記する
   （いずれもShopify管理画面 ストア分析 > レポート で ShopifyQL を実行して手動転記）
2. python3 build_tracking_tabs.py を実行する
3. git add/commit/push する

TRACKING_TABS_START/END のコメントで囲まれた範囲だけを毎回まるごと置き換えるので、
このスクリプトは何度実行しても安全（冪等）。
"""
import csv
import re
from pathlib import Path

BASE = Path(__file__).parent
HTML_PATH = BASE / "shopify-dashboard.html"

START = "<!-- TRACKING_TABS_START -->"
END = "<!-- TRACKING_TABS_END -->"
# 初回移行用：まだ TRACKING_TABS マーカーが無い場合はこの範囲を置き換える
LEGACY_START = '<h2 class="sec">訪問者は倍増、注文は減少'
LEGACY_END = "<!-- DAILY_CHART_END -->"

Y_TOP, Y_BOTTOM = 20.0, 230.0
X_LEFT, X_RIGHT = 52.0, 1070.0


def load_rows(name):
    with open(BASE / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def x_positions(n):
    if n == 1:
        return [(X_LEFT + X_RIGHT) / 2]
    step = (X_RIGHT - X_LEFT) / (n - 1)
    return [X_LEFT + i * step for i in range(n)]


def y_positions(values):
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        return [(Y_TOP + Y_BOTTOM) / 2 for _ in values]
    return [Y_BOTTOM - (v - vmin) / (vmax - vmin) * (Y_BOTTOM - Y_TOP) for v in values]


def build_line_svg(labels, sessions, orders, label_fmt, max_labels=8):
    n = len(labels)
    xs = x_positions(n)
    ys_s = y_positions(sessions)
    ys_o = y_positions(orders)

    parts = ['<svg class="chartsvg" viewBox="0 0 1080 260" xmlns="http://www.w3.org/2000/svg">']
    parts.append(f'<line x1="{X_LEFT}" y1="{Y_BOTTOM}" x2="{X_RIGHT}" y2="{Y_BOTTOM}" stroke="#e3e5e9"/>')

    pts_s = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys_s))
    pts_o = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys_o))
    parts.append(f'<polyline points="{pts_s}" fill="none" stroke="#0891b2" stroke-width="2.2"/>')
    parts.append(f'<polyline points="{pts_o}" fill="none" stroke="#b91c1c" stroke-width="2.2"/>')

    step = max(1, round(n / max_labels))
    for i in range(n):
        d = labels[i]
        parts.append(
            f'<circle cx="{xs[i]:.1f}" cy="{ys_s[i]:.1f}" r="7" fill="#0891b2" opacity="0" '
            f'data-tip="{d} セッション数：{sessions[i]:,}"/>'
            f'<circle cx="{xs[i]:.1f}" cy="{ys_s[i]:.1f}" r="2.6" fill="#0891b2"/>'
            f'<circle cx="{xs[i]:.1f}" cy="{ys_o[i]:.1f}" r="7" fill="#b91c1c" opacity="0" '
            f'data-tip="{d} EC注文数：{orders[i]}件"/>'
            f'<circle cx="{xs[i]:.1f}" cy="{ys_o[i]:.1f}" r="2.6" fill="#b91c1c"/>'
        )
        if i % step == 0 or i == n - 1:
            parts.append(
                f'<text x="{xs[i]:.1f}" y="246" font-size="10" fill="#6b7280" '
                f'text-anchor="middle">{label_fmt(d)}</text>'
            )

    parts.append("</svg>")
    return "".join(parts)


def build_stat_cards(rows, date_key):
    last = rows[-1]
    sessions = int(last["sessions"])
    orders = int(last["orders"])
    cards = [
        ("セッション数", f"{sessions:,}", "#0891b2"),
        ("EC注文数（CV）", f"{orders}件", "#b91c1c"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="l">{label}（{last[date_key]}）</div>'
        f'<div class="v" style="color:{color}">{value}</div></div>'
        for label, value, color in cards
    )
    return f'<div class="kpis" style="margin-bottom:0">{kpi_html}</div>'


def month_label(m):
    y, mo = m.split("-")
    return f"{y[2:]}-{mo}"


def week_label(w):
    y, mo, d = w.split("-")
    return f"{mo}/{d}"


def day_label(d):
    y, mo, dd = d.split("-")
    return f"{int(mo)}/{int(dd)}"


def build_panel(panel_id, rows, date_key, label_fmt, active, min_points_for_chart=3):
    n = len(rows)
    dates = [r[date_key] for r in rows]
    sessions = [int(r["sessions"]) for r in rows]
    orders = [int(r["orders"]) for r in rows]
    last_date = dates[-1]

    if n < min_points_for_chart:
        body = build_stat_cards(rows, date_key)
        legend = ""
        note = (
            f"データが{n}件のみのため折れ線ではなく実数カードで表示しています"
            f"（最終更新：{last_date}）。{min_points_for_chart}件以上たまり次第、自動で折れ線グラフに切り替わります。"
        )
    else:
        body = build_line_svg(dates, sessions, orders, label_fmt)
        legend = (
            '<div class="legend"><div class="li"><span class="sw" style="background:#0891b2"></span>セッション数</div>'
            '<div class="li"><span class="sw" style="background:#b91c1c"></span>EC注文数（CV）</div></div>'
        )
        note = (
            f"{n}件のデータ（最終更新：{last_date}）。各系列は表示期間内の最大値を100として正規化。"
            f"点にカーソルを合わせると実数が表示されます。"
        )

    display = "block" if active else "none"
    return (
        f'<div class="trk-panel" id="trk-{panel_id}" style="display:{display}">\n'
        f'{legend}\n{body}\n'
        f'<div class="desc" style="margin:10px 0 0">{note}</div>\n'
        f'</div>'
    )


def build_section():
    monthly = load_rows("monthly_metrics.csv")
    weekly = load_rows("weekly_metrics.csv")
    daily = load_rows("daily_metrics.csv")

    panel_month = build_panel("month", monthly, "month", month_label, active=True)
    panel_week = build_panel("week", weekly, "week", week_label, active=False)
    panel_day = build_panel("day", daily, "date", day_label, active=False)

    tabs = (
        '<div class="trk-tabs">'
        '<button class="trk-tab active" onclick="trkSwitch(\'month\',this)">月次</button>'
        '<button class="trk-tab" onclick="trkSwitch(\'week\',this)">週次</button>'
        '<button class="trk-tab" onclick="trkSwitch(\'day\',this)">日次</button>'
        '</div>'
    )

    script = (
        "<script>function trkSwitch(id,btn){"
        "document.querySelectorAll('.trk-panel').forEach(function(p){p.style.display='none';});"
        "document.getElementById('trk-'+id).style.display='block';"
        "document.querySelectorAll('.trk-tab').forEach(function(b){b.classList.remove('active');});"
        "btn.classList.add('active');"
        "}</script>"
    )

    style = (
        "<style>"
        ".trk-tabs{display:flex;gap:8px;margin-bottom:14px}"
        ".trk-tab{font:inherit;font-weight:700;font-size:14px;padding:7px 16px;border-radius:20px;"
        "border:1px solid var(--line);background:#fff;color:var(--muted);cursor:pointer}"
        ".trk-tab.active{background:#111827;color:#fff;border-color:#111827}"
        "</style>"
    )

    return (
        f'{START}\n'
        f'{style}\n'
        f'<h2 class="sec">セッション数とEC注文数（CV）トラッキング '
        f'<span class="tag">2025年1月〜（月次・週次）／2026年8月20日〜（日次）</span></h2>\n'
        f'<div class="card">\n'
        f'{tabs}\n'
        f'{panel_month}\n{panel_week}\n{panel_day}\n'
        f'</div>\n'
        f'{script}\n'
        f'{END}'
    )


def main():
    section = build_section()
    html = HTML_PATH.read_text(encoding="utf-8")

    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if pattern.search(html):
        html = pattern.sub(section, html)
    else:
        legacy_pattern = re.compile(re.escape(LEGACY_START) + r".*?" + re.escape(LEGACY_END), re.DOTALL)
        if not legacy_pattern.search(html):
            raise SystemExit("挿入位置が見つかりませんでした（LEGACY_START/END, TRACKING_TABS_START/END とも不一致）")
        html = legacy_pattern.sub(section, html)

    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"updated: {HTML_PATH}")


if __name__ == "__main__":
    main()
