#!/usr/bin/env python3
"""
报告仪表盘生成器 — 美股版
扫描 output/ 目录中所有已生成的个股研究HTML报告，
生成一个漂亮的索引页（仪表盘），一键打开即可浏览所有历史分析。

用法：
  python3 report_dashboard.py          # 生成并打开仪表盘
  python3 report_dashboard.py --no-open # 仅生成，不自动打开
"""

import os
import re
import sys
import glob
import subprocess
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = SCRIPT_DIR / "output"
DASHBOARD_FILE = OUTPUT_DIR / "报告仪表盘.html"

# 判断是 A股版 还是 美股版
IS_US = "us-stock" in str(SCRIPT_DIR).lower() or "us_stock" in str(SCRIPT_DIR).lower()
MARKET_LABEL = "美股" if IS_US else "A股"
UP_COLOR = "#28c75b" if IS_US else "#f55656"
DOWN_COLOR = "#f55656" if IS_US else "#28c75b"


def extract_report_info(filepath: str) -> dict:
    """从 HTML 报告中提取关键信息"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            html = f.read()
    except Exception:
        return None

    info = {
        "filepath": filepath,
        "filename": os.path.basename(filepath),
        "filesize": os.path.getsize(filepath),
        "mtime": os.path.getmtime(filepath),
    }

    # 公司名
    m = re.search(r'class="stock-name"[^>]*>([^<]+)', html)
    info["company"] = m.group(1).strip() if m else Path(filepath).stem.replace("个股研究-", "")

    # 股票代码
    m = re.search(r'class="stock-code"[^>]*>([^<]+)', html)
    info["code"] = m.group(1).strip() if m else "—"

    # 价格
    m = re.search(r'class="hero-price"[^>]*>([^<]+)', html)
    info["price"] = m.group(1).strip() if m else "—"

    # 涨跌幅
    m = re.search(r'class="hero-change[^"]*"[^>]*>([^<]+)', html)
    info["change"] = m.group(1).strip() if m else "—"

    # 判断涨跌
    info["is_up"] = "+" in info["change"] or (info["change"] not in ["—", ""] and not info["change"].startswith("-"))

    # 核心结论
    m = re.search(r'class="big-verdict"[^>]*>([^<]+)', html)
    raw = m.group(1).strip() if m else ""
    # 去掉 emoji
    info["verdict"] = re.sub(r'[^一-鿿\w\s·$%\-\+\.]+', '', raw).strip() if raw else "—"

    # 评分 — 从 hero-tag 或 judgment 中提取
    m = re.search(r'(\d{2,3}/100\s*[A-S][+\-]?)', html)
    info["score"] = m.group(1).strip() if m else "—"

    # 目标价 — 从 verdict-detail 中提取
    m = re.search(r'[中期目标|目标]\s*\$?([\d,]+(?:\.\d+)?(?:\s*[-–]\s*\$?[\d,]+(?:\.\d+)?)?)', html)
    if m:
        info["target"] = "$" + m.group(1).strip()
    else:
        # A股版 — 找 ¥ 或纯数字目标价
        m2 = re.search(r'目标[价]?\s*[¥￥]?([\d,]+(?:\.\d+)?)', html)
        info["target"] = ("¥" if not IS_US else "$") + m2.group(1).strip() if m2 else "—"

    # 报告日期 — 从 stock-code 行提取
    m = re.search(r'(\d{4}-\d{2}-\d{2})', info["code"])
    info["date"] = m.group(1) if m else datetime.fromtimestamp(info["mtime"]).strftime("%Y-%m-%d")

    # hero-tag 标签
    tags = re.findall(r'class="hero-tag"[^>]*>([^<]+)', html)
    info["tags"] = tags[:4] if tags else []

    return info


def generate_dashboard(reports: list) -> str:
    """生成仪表盘 HTML"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    count = len(reports)

    # 按修改时间倒序
    reports.sort(key=lambda r: r["mtime"], reverse=True)

    # 生成卡片
    cards_html = ""
    for r in reports:
        change_class = "up" if r["is_up"] else "down"
        change_bg = f"rgba(40,199,91,0.15)" if r["is_up"] else f"rgba(245,86,86,0.15)"
        change_color = UP_COLOR if r["is_up"] else DOWN_COLOR

        tags_html = "".join(f'<span class="d-tag">{t}</span>' for t in r["tags"])

        mtime_str = datetime.fromtimestamp(r["mtime"]).strftime("%Y-%m-%d %H:%M")
        size_kb = r["filesize"] / 1024

        cards_html += f"""
    <a href="{r['filename']}" class="report-card" target="_blank">
      <div class="rc-header">
        <div class="rc-company">{r['company']}</div>
        <div class="rc-price" style="color:{change_color}">{r['price']}</div>
      </div>
      <div class="rc-code">{r['code']}</div>
      <div class="rc-row">
        <span class="rc-change" style="background:{change_bg};color:{change_color}">{r['change']}</span>
        <span class="rc-score">{r['score']}</span>
      </div>
      <div class="rc-verdict">{r['verdict']}</div>
      <div class="rc-target">目标价：{r['target']}</div>
      <div class="rc-tags">{tags_html}</div>
      <div class="rc-meta">分析日期：{r['date']} · {size_kb:.0f}KB</div>
    </a>
"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{MARKET_LABEL}研究报告仪表盘</title>
<style>
:root{{
--bg:#0c0f15;--card-bg:#1a1c24;--card-bg-alt:#1e2029;--border:#2a2d3a;
--text-primary:#e8e9ec;--text-secondary:#b0b3be;--text-muted:#7a7d8a;
--green-up:{UP_COLOR};--red-down:{DOWN_COLOR};--gold:#d4a853;--gold-light:#e3c26d;
--blue-accent:#4a90d9;--orange-warn:#e8923a;
--shadow:0 4px 20px rgba(0,0,0,0.3);--radius:10px;
--font-sans:"PingFang SC","Microsoft YaHei",-apple-system,sans-serif;
--font-mono:"JetBrains Mono","SF Mono","Consolas",monospace;
}}
body.light-mode{{
--bg:#fdf8f0;--card-bg:#fffbf5;--card-bg-alt:#fef5e7;--border:#e2cfa2;
--text-primary:#2a1f12;--text-secondary:#6b5634;--text-muted:#9c8b6e;
--green-up:{"#16a34a" if IS_US else "#dc2626"};--red-down:{"#dc2626" if IS_US else "#16a34a"};
--gold:#b38a3c;--gold-light:#d4a853;--blue-accent:#2563eb;--orange-warn:#c2410c;
--shadow:0 4px 20px rgba(162,125,57,0.08)
}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--text-primary);font-family:var(--font-sans);
line-height:1.7;font-size:14px;min-height:100vh;
background-image:radial-gradient(circle at 15% 10%,rgba(212,168,83,0.03) 0%,transparent 35%),
radial-gradient(circle at 85% 70%,rgba(212,168,83,0.03) 0%,transparent 35%);background-attachment:fixed}}

/* 顶栏 */
.top-bar{{position:sticky;top:0;z-index:100;background:rgba(10,12,18,0.92);backdrop-filter:blur(12px);
border-bottom:2px solid var(--gold-light);padding:14px 28px;display:flex;align-items:center;
justify-content:space-between;flex-wrap:wrap;gap:12px}}
.top-bar .title{{font-size:22px;font-weight:800;color:#fff;letter-spacing:1px}}
.top-bar .title span{{color:var(--gold)}}
.top-bar .meta{{font-size:12px;color:var(--text-muted)}}
.theme-toggle{{background:rgba(255,255,255,0.08);border:1px solid var(--gold-light);color:var(--gold-light);
padding:5px 14px;border-radius:16px;font-size:12px;cursor:pointer}}
.theme-toggle:hover{{background:rgba(255,255,255,0.15)}}
body.light-mode .top-bar{{background:rgba(255,251,245,0.92);border-bottom-color:var(--gold)}}

/* 统计栏 */
.stats{{max-width:1300px;margin:24px auto 0;padding:0 20px;display:flex;gap:16px;flex-wrap:wrap}}
.stat-card{{background:var(--card-bg);border:1px solid var(--border);border-radius:var(--radius);
padding:16px 24px;flex:1;min-width:160px;text-align:center;box-shadow:var(--shadow)}}
.stat-card .val{{font-size:28px;font-weight:800;color:var(--gold);font-family:var(--font-mono)}}
.stat-card .label{{font-size:12px;color:var(--text-muted);margin-top:4px}}

/* 卡片网格 */
.container{{max-width:1300px;margin:20px auto;padding:0 20px 40px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:20px;margin-top:20px}}

/* 报告卡片 */
.report-card{{display:block;background:var(--card-bg);border:1px solid var(--border);border-radius:var(--radius);
padding:20px 24px;box-shadow:var(--shadow);transition:all 0.25s ease;text-decoration:none;color:inherit;
position:relative;overflow:hidden}}
.report-card:hover{{transform:translateY(-4px);box-shadow:0 12px 40px rgba(0,0,0,0.5);border-color:var(--gold)}}
.report-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;
background:linear-gradient(90deg,var(--gold),var(--gold-light),transparent);opacity:0;transition:opacity 0.25s}}
.report-card:hover::before{{opacity:1}}

.rc-header{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px}}
.rc-company{{font-size:18px;font-weight:700;color:#fff}}
body.light-mode .rc-company{{color:var(--text-primary)}}
.rc-price{{font-size:20px;font-weight:800;font-family:var(--font-mono)}}
.rc-code{{font-size:11px;color:var(--text-muted);font-family:var(--font-mono);margin-bottom:10px}}
.rc-row{{display:flex;align-items:center;gap:10px;margin-bottom:10px}}
.rc-change{{padding:3px 10px;border-radius:12px;font-size:12px;font-weight:700;font-family:var(--font-mono)}}
.rc-score{{font-size:13px;font-weight:700;color:var(--gold);
background:rgba(212,168,83,0.15);padding:3px 10px;border-radius:12px;border:1px solid var(--gold)}}
.rc-verdict{{font-size:13px;color:var(--text-secondary);margin-bottom:8px;line-height:1.5;
display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.rc-target{{font-size:13px;font-weight:600;color:var(--green-up);margin-bottom:10px}}
.rc-tags{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}}
.d-tag{{font-size:10px;padding:2px 8px;border-radius:10px;background:rgba(255,255,255,0.06);
border:1px solid rgba(255,215,0,0.2);color:var(--gold-light)}}
.rc-meta{{font-size:11px;color:var(--text-muted)}}

/* 空状态 */
.empty{{text-align:center;padding:80px 20px;color:var(--text-muted)}}
.empty .icon{{font-size:48px;margin-bottom:16px}}
.empty .msg{{font-size:16px}}

/* 页脚 */
footer{{text-align:center;padding:24px 16px;font-size:12px;color:var(--text-muted);
border-top:1px solid var(--border);margin-top:24px;max-width:1300px;margin-left:auto;margin-right:auto}}

@media(max-width:750px){{.grid{{grid-template-columns:1fr}}.stats{{flex-direction:column}}}}
</style>
</head>
<body>

<div class="top-bar">
  <div>
    <div class="title">📊 <span>{MARKET_LABEL}</span>研究报告仪表盘</div>
    <div class="meta">共 {count} 份报告 · 更新于 {now}</div>
  </div>
  <button class="theme-toggle" id="themeToggle">☀️ 浅色模式</button>
</div>

<div class="stats">
  <div class="stat-card"><div class="val">{count}</div><div class="label">已分析个股</div></div>
  <div class="stat-card"><div class="val">{sum(1 for r in reports if r['is_up'])}</div><div class="label">收盘上涨</div></div>
  <div class="stat-card"><div class="val">{sum(1 for r in reports if not r['is_up'])}</div><div class="label">收盘下跌</div></div>
  <div class="stat-card"><div class="val">{reports[0]['date'] if reports else '—'}</div><div class="label">最新分析</div></div>
</div>

<div class="container">
  <div class="grid">
{cards_html if cards_html else '<div class="empty"><div class="icon">📭</div><div class="msg">暂无报告，使用 "分析 AAPL" 开始第一份研究</div></div>'}
  </div>
</div>

<footer>
  <div>{MARKET_LABEL}深度研究系统 · 报告仪表盘 · Powered by AI Stock Analysis Skill</div>
  <div style="margin-top:4px">点击任意卡片即可打开完整报告</div>
</footer>

<script>
const toggleBtn = document.getElementById('themeToggle');
toggleBtn.addEventListener('click', () => {{
  document.body.classList.toggle('light-mode');
  toggleBtn.textContent = document.body.classList.contains('light-mode') ? '🌙 深色模式' : '☀️ 浅色模式';
}});
</script>
</body>
</html>"""
    return html


def main():
    no_open = "--no-open" in sys.argv

    # 扫描所有报告
    pattern = str(OUTPUT_DIR / "个股研究-*.html")
    html_files = glob.glob(pattern)

    # 排除仪表盘自身
    html_files = [f for f in html_files if "仪表盘" not in f]

    reports = []
    for f in html_files:
        info = extract_report_info(f)
        if info:
            reports.append(info)

    print(f"[仪表盘] 扫描到 {len(reports)} 份{MARKET_LABEL}研究报告")
    for r in sorted(reports, key=lambda x: x["mtime"], reverse=True):
        print(f"  · {r['company']} ({r['code']}) — {r['score']} — {r['price']}")

    # 生成 HTML
    dashboard_html = generate_dashboard(reports)
    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        f.write(dashboard_html)
    print(f"[仪表盘] 已生成：{DASHBOARD_FILE}")
    print(f"[仪表盘] 大小：{os.path.getsize(DASHBOARD_FILE) / 1024:.1f} KB")

    # 自动打开
    if not no_open:
        subprocess.run(["open", str(DASHBOARD_FILE)])
        print(f"[仪表盘] 已在浏览器中打开")


if __name__ == "__main__":
    main()
