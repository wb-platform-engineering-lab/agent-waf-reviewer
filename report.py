"""
Converts the agent's text review into a professional HTML report.
"""

import os
import re
from datetime import datetime


# ─────────────────────────────────────────────
# Parser — extracts structured data from text
# ─────────────────────────────────────────────

def parse_report(text: str) -> dict:
    """Parse the agent's free-form text report into structured data."""

    pillar_names = {
        "1": "Governance & Control",
        "2": "Security",
        "3": "Reliability",
        "4": "Cost Optimization",
        "5": "Observability",
        "6": "Performance & Context",
    }

    pillars = []
    checks_by_pillar = {}
    overall_score = None
    action_items = []
    summary_lines = []

    current_pillar = None
    in_actions = False

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        # Overall score
        m = re.search(r"Overall[:\s]+(\d+)/(\d+)", stripped)
        if m:
            overall_score = (int(m.group(1)), int(m.group(2)))
            continue

        # Pillar header
        m = re.match(r"Pillar (\d) — (.+?)\s+([\u2714\u2718\u26a0\u274c\u2705\u26a0\ufe0f]+.*?)\s+(\d+)/(\d+)", stripped)
        if not m:
            m = re.match(r"Pillar (\d)[^\d]", stripped)
        if m and len(m.groups()) >= 1:
            num = m.group(1)
            status_str = stripped
            if "FAIL" in stripped or "❌" in stripped:
                status = "fail"
            elif "WARN" in stripped or "⚠" in stripped:
                status = "warn"
            else:
                status = "pass"

            # Try to extract pass/total
            score_m = re.search(r"(\d+)/(\d+)", stripped)
            pass_count = int(score_m.group(1)) if score_m else 0
            total_count = int(score_m.group(2)) if score_m else 0

            pillar = {
                "num": num,
                "name": pillar_names.get(num, f"Pillar {num}"),
                "status": status,
                "pass": pass_count,
                "total": total_count,
                "checks": [],
            }
            pillars.append(pillar)
            checks_by_pillar[num] = pillar
            current_pillar = pillar
            in_actions = False
            continue

        # Check row
        m = re.match(r"(❌|⚠️|✅|ℹ️)\s*(FAIL|WARN|PASS|INFO)\s+\[([A-Z0-9\-]+)\]\s+(.+)", stripped)
        if m and current_pillar is not None:
            icon, status, check_id, name = m.group(1), m.group(2), m.group(3), m.group(4)
            check = {
                "icon": icon,
                "status": status.lower(),
                "id": check_id,
                "name": name,
                "recommendation": None,
            }
            current_pillar["checks"].append(check)
            continue

        # Recommendation line
        if (stripped.startswith("→") or stripped.startswith("→")) and current_pillar and current_pillar["checks"]:
            msg = stripped.lstrip("→").strip()
            current_pillar["checks"][-1]["recommendation"] = msg
            continue

        # Action items section
        if re.search(r"(TOP|PRIORITY|ACTION|PRIORIT)", stripped.upper()) and re.search(r"\d", stripped):
            in_actions = True
            continue
        if in_actions:
            m = re.match(r"(\d+)[.)]\s+(.+)", stripped)
            if m:
                action_items.append(m.group(2))
                continue

        # Collect summary text (before first pillar)
        if not pillars and not re.match(r"^[═─]{5,}", stripped):
            if not re.match(r"^Automated pillar", stripped):
                summary_lines.append(stripped)

    # Fallback score
    if not overall_score and pillars:
        total_pass = sum(p["pass"] for p in pillars)
        total_checks = sum(p["total"] for p in pillars)
        if total_checks:
            overall_score = (total_pass, total_checks)

    return {
        "pillars": pillars,
        "overall_score": overall_score,
        "action_items": action_items,
        "summary": " ".join(summary_lines[:3]) if summary_lines else "",
        "raw": text,
    }


# ─────────────────────────────────────────────
# HTML renderer
# ─────────────────────────────────────────────

PILLAR_ICONS = {
    "1": "⚙️", "2": "🔒", "3": "🛡️",
    "4": "💰", "5": "👁️", "6": "⚡",
}

PILLAR_COLORS = {
    "1": "#2563eb", "2": "#dc2626", "3": "#16a34a",
    "4": "#d97706", "5": "#9333ea", "6": "#0891b2",
}


def _score_color(pct: float) -> str:
    if pct >= 0.8:
        return "#16a34a"
    if pct >= 0.5:
        return "#d97706"
    return "#dc2626"


def _pillar_cards(pillars: list) -> str:
    if not pillars:
        return ""
    cards = []
    for p in pillars:
        color = PILLAR_COLORS.get(p["num"], "#2563eb")
        pct = (p["pass"] / p["total"] * 100) if p["total"] else 0
        sc = _score_color(pct / 100)
        status_label = p["status"].upper()
        status_cls = p["status"]
        icon = PILLAR_ICONS.get(p["num"], "●")
        cards.append(f"""
        <div class="pillar-card" style="--pillar-color:{color}">
          <div class="pc-top">
            <span class="pc-icon">{icon}</span>
            <span class="pc-num">Pillar {p["num"]}</span>
            <span class="pc-badge {status_cls}">{status_label}</span>
          </div>
          <div class="pc-name">{p["name"]}</div>
          <div class="pc-score" style="color:{sc}">{p["pass"]}<span>/{p["total"]}</span></div>
          <div class="pc-bar-bg">
            <div class="pc-bar-fill" style="width:{pct:.0f}%;background:{sc}"></div>
          </div>
        </div>""")
    return "\n".join(cards)


def _pillar_sections(pillars: list) -> str:
    if not pillars:
        return "<p>No pillar data found.</p>"
    sections = []
    for p in pillars:
        color = PILLAR_COLORS.get(p["num"], "#2563eb")
        icon = PILLAR_ICONS.get(p["num"], "●")
        pct = (p["pass"] / p["total"] * 100) if p["total"] else 0
        sc = _score_color(pct / 100)

        checks_html = ""
        for c in p["checks"]:
            cls = c["status"]
            label = c["status"].upper()
            rec = ""
            if c["recommendation"]:
                rec = f'<div class="rec">→ {c["recommendation"]}</div>'
            checks_html += f"""
            <div class="check-item {cls}">
              <div class="ci-top">
                <span class="ci-badge {cls}">{label}</span>
                <span class="ci-id">{c["id"]}</span>
                <span class="ci-name">{c["name"]}</span>
              </div>
              {rec}
            </div>"""

        if not checks_html:
            checks_html = "<p class='no-checks'>No individual checks recorded.</p>"

        sections.append(f"""
        <div class="pillar-section" id="pillar-{p["num"]}">
          <div class="ps-header" style="border-left-color:{color}">
            <div class="ps-title">
              <span class="ps-icon">{icon}</span>
              <span>Pillar {p["num"]} — {p["name"]}</span>
            </div>
            <div class="ps-meta">
              <div class="ps-bar-bg">
                <div class="ps-bar-fill" style="width:{pct:.0f}%;background:{sc}"></div>
              </div>
              <span class="ps-score" style="color:{sc}">{p["pass"]}/{p["total"]}</span>
            </div>
          </div>
          <div class="checks-list">
            {checks_html}
          </div>
        </div>""")
    return "\n".join(sections)


def _action_items_html(items: list) -> str:
    if not items:
        return ""
    rows = ""
    for i, item in enumerate(items[:5], 1):
        urgency = "High" if i == 1 else ("Medium" if i == 2 else "Low")
        urg_cls = "high" if i == 1 else ("medium" if i == 2 else "low")
        rows += f"""
        <div class="action-row">
          <div class="ar-num">{i}</div>
          <div class="ar-body">
            <div class="ar-text">{item}</div>
            <span class="ar-urgency {urg_cls}">{urgency} priority</span>
          </div>
        </div>"""
    return rows


def generate_html(report_text: str, target_path: str) -> str:
    data = parse_report(report_text)
    timestamp = datetime.now().strftime("%B %d, %Y · %H:%M")
    target_abs = os.path.abspath(target_path)
    target_name = os.path.basename(target_abs)

    score = data["overall_score"]
    if score:
        score_pct = int(score[0] / score[1] * 100) if score[1] else 0
        score_color = _score_color(score_pct / 100)
        score_display = f"{score[0]}/{score[1]}"
        grade = "PASS" if score_pct >= 70 else ("AT RISK" if score_pct >= 40 else "FAIL")
        grade_cls = "pass" if score_pct >= 70 else ("warn" if score_pct >= 40 else "fail")
    else:
        score_pct, score_color, score_display = 0, "#dc2626", "—"
        grade, grade_cls = "UNKNOWN", "warn"

    pillar_cards = _pillar_cards(data["pillars"])
    pillar_sections = _pillar_sections(data["pillars"])
    action_rows = _action_items_html(data["action_items"])

    # Sidebar nav
    nav_items = ""
    for p in data["pillars"]:
        color = PILLAR_COLORS.get(p["num"], "#2563eb")
        icon = PILLAR_ICONS.get(p["num"], "●")
        cls = p["status"]
        dot = "✅" if cls == "pass" else ("❌" if cls == "fail" else "⚠️")
        nav_items += f'<a href="#pillar-{p["num"]}" class="nav-link">{dot} {icon} Pillar {p["num"]} — {p["name"]}</a>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>WAF Review — {target_name}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --bg: #f1f5f9;
      --surface: #ffffff;
      --border: #e2e8f0;
      --text: #0f172a;
      --muted: #64748b;
      --pass: #16a34a; --pass-bg: #f0fdf4; --pass-light: #dcfce7;
      --fail: #dc2626; --fail-bg: #fef2f2; --fail-light: #fee2e2;
      --warn: #d97706; --warn-bg: #fffbeb; --warn-light: #fef3c7;
      --info: #2563eb; --info-bg: #eff6ff;
      --sidebar-w: 280px;
      --radius: 12px;
    }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      display: flex;
      min-height: 100vh;
    }}

    /* ── Sidebar ───────────────────────────────── */
    .sidebar {{
      position: fixed; top: 0; left: 0;
      width: var(--sidebar-w); height: 100vh;
      background: #0f172a;
      padding: 2rem 1.5rem;
      overflow-y: auto;
      display: flex; flex-direction: column; gap: 0.25rem;
    }}
    .sidebar-logo {{
      font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.12em; color: #475569;
      margin-bottom: 0.5rem; padding-bottom: 1rem;
      border-bottom: 1px solid #1e293b;
    }}
    .sidebar-title {{
      font-size: 0.95rem; font-weight: 700; color: #f1f5f9;
      margin-bottom: 0.25rem;
    }}
    .sidebar-target {{
      font-size: 0.75rem; color: #7dd3fc; font-family: monospace;
      margin-bottom: 1.5rem; word-break: break-all;
    }}
    .sidebar-section {{
      font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.1em; color: #475569;
      margin: 1rem 0 0.4rem;
    }}
    .nav-link {{
      display: block; font-size: 0.8rem; color: #94a3b8;
      padding: 0.35rem 0.6rem; border-radius: 6px;
      text-decoration: none; transition: background 0.15s, color 0.15s;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }}
    .nav-link:hover {{ background: #1e293b; color: #f1f5f9; }}

    /* ── Main ──────────────────────────────────── */
    .main {{
      margin-left: var(--sidebar-w);
      padding: 2.5rem 2rem 6rem;
      width: 100%;
      max-width: calc(var(--sidebar-w) + 900px);
    }}

    /* ── Hero header ───────────────────────────── */
    .hero {{
      background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
      border-radius: var(--radius);
      padding: 2.5rem 3rem;
      margin-bottom: 2rem;
      display: flex; align-items: center; justify-content: space-between;
      gap: 2rem;
    }}
    .hero-left h1 {{
      font-size: 1.6rem; font-weight: 800; color: #f8fafc;
      margin-bottom: 0.4rem; line-height: 1.2;
    }}
    .hero-left .hero-sub {{
      font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.6rem;
    }}
    .hero-left .hero-target {{
      font-family: monospace; font-size: 0.82rem;
      color: #7dd3fc; background: rgba(125,211,252,0.1);
      padding: 0.3rem 0.8rem; border-radius: 6px; display: inline-block;
    }}
    .hero-score {{
      flex-shrink: 0; text-align: center;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: var(--radius);
      padding: 1.5rem 2rem;
    }}
    .hero-score .hs-num {{
      font-size: 3rem; font-weight: 900; line-height: 1;
      color: {score_color};
    }}
    .hero-score .hs-label {{
      font-size: 0.75rem; color: #94a3b8; margin-top: 0.3rem; text-transform: uppercase; letter-spacing: 0.08em;
    }}
    .hero-score .hs-grade {{
      display: inline-block; font-size: 0.75rem; font-weight: 700;
      padding: 0.25rem 0.8rem; border-radius: 99px; margin-top: 0.5rem;
    }}
    .hs-grade.pass {{ background: var(--pass-light); color: var(--pass); }}
    .hs-grade.warn {{ background: var(--warn-light); color: var(--warn); }}
    .hs-grade.fail {{ background: var(--fail-light); color: var(--fail); }}

    /* ── Section titles ────────────────────────── */
    .section-title {{
      font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.1em; color: var(--muted);
      margin: 2.5rem 0 1rem;
    }}

    /* ── Pillar cards grid ─────────────────────── */
    .pillar-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
      margin-bottom: 0.5rem;
    }}
    .pillar-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-top: 3px solid var(--pillar-color);
      border-radius: var(--radius);
      padding: 1.25rem;
      cursor: default;
      transition: box-shadow 0.15s;
    }}
    .pillar-card:hover {{ box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
    .pc-top {{
      display: flex; align-items: center; gap: 0.5rem;
      margin-bottom: 0.6rem;
    }}
    .pc-icon {{ font-size: 1.1rem; }}
    .pc-num {{
      font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.08em; color: var(--muted); flex: 1;
    }}
    .pc-badge {{
      font-size: 0.65rem; font-weight: 700;
      padding: 0.15rem 0.5rem; border-radius: 99px;
    }}
    .pc-badge.pass {{ background: var(--pass-light); color: var(--pass); }}
    .pc-badge.fail {{ background: var(--fail-light); color: var(--fail); }}
    .pc-badge.warn {{ background: var(--warn-light); color: var(--warn); }}
    .pc-name {{
      font-size: 0.88rem; font-weight: 700; color: var(--text);
      margin-bottom: 0.75rem; line-height: 1.3;
    }}
    .pc-score {{
      font-size: 1.6rem; font-weight: 900; line-height: 1; margin-bottom: 0.5rem;
    }}
    .pc-score span {{ font-size: 1rem; font-weight: 500; color: var(--muted); }}
    .pc-bar-bg {{
      height: 4px; background: var(--border); border-radius: 99px; overflow: hidden;
    }}
    .pc-bar-fill {{ height: 100%; border-radius: 99px; transition: width 0.6s; }}

    /* ── Pillar detail sections ────────────────── */
    .pillar-section {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      margin-bottom: 1.25rem;
      overflow: hidden;
    }}
    .ps-header {{
      display: flex; align-items: center; justify-content: space-between;
      padding: 1.1rem 1.5rem;
      border-left: 4px solid;
      background: #fafbfc;
      border-bottom: 1px solid var(--border);
    }}
    .ps-title {{
      display: flex; align-items: center; gap: 0.6rem;
      font-size: 0.95rem; font-weight: 700;
    }}
    .ps-icon {{ font-size: 1.1rem; }}
    .ps-meta {{
      display: flex; align-items: center; gap: 0.75rem;
    }}
    .ps-bar-bg {{
      width: 80px; height: 6px; background: var(--border);
      border-radius: 99px; overflow: hidden;
    }}
    .ps-bar-fill {{ height: 100%; border-radius: 99px; }}
    .ps-score {{
      font-size: 0.85rem; font-weight: 700; min-width: 32px; text-align: right;
    }}
    .checks-list {{ padding: 0.75rem 1.5rem 1rem; }}

    /* ── Check items ───────────────────────────── */
    .check-item {{
      padding: 0.6rem 0;
      border-bottom: 1px solid #f1f5f9;
    }}
    .check-item:last-child {{ border-bottom: none; }}
    .ci-top {{
      display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap;
    }}
    .ci-badge {{
      font-size: 0.65rem; font-weight: 700;
      padding: 0.15rem 0.5rem; border-radius: 99px; min-width: 44px; text-align: center;
    }}
    .ci-badge.pass {{ background: var(--pass-light); color: var(--pass); }}
    .ci-badge.fail {{ background: var(--fail-light); color: var(--fail); }}
    .ci-badge.warn {{ background: var(--warn-light); color: var(--warn); }}
    .ci-badge.info {{ background: var(--info-bg); color: var(--info); }}
    .ci-id {{
      font-family: monospace; font-size: 0.75rem; color: #94a3b8; min-width: 56px;
    }}
    .ci-name {{ font-size: 0.875rem; color: var(--text); }}
    .rec {{
      font-size: 0.82rem; color: var(--muted);
      padding: 0.3rem 0 0 calc(44px + 56px + 1.2rem);
      line-height: 1.5;
    }}
    .rec::before {{ content: "→ "; color: var(--fail); font-weight: 600; }}
    .no-checks {{ font-size: 0.85rem; color: var(--muted); padding: 0.5rem 0; }}

    /* ── Action items ──────────────────────────── */
    .actions-card {{
      background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--radius); overflow: hidden;
      margin-bottom: 2rem;
    }}
    .actions-header {{
      background: #0f172a; padding: 1rem 1.5rem;
      font-size: 0.9rem; font-weight: 700; color: #f8fafc;
      display: flex; align-items: center; gap: 0.5rem;
    }}
    .action-row {{
      display: flex; align-items: flex-start; gap: 1rem;
      padding: 1rem 1.5rem;
      border-bottom: 1px solid var(--border);
    }}
    .action-row:last-child {{ border-bottom: none; }}
    .ar-num {{
      flex-shrink: 0; width: 28px; height: 28px;
      background: #0f172a; color: #fff;
      border-radius: 50%; display: flex; align-items: center;
      justify-content: center; font-size: 0.8rem; font-weight: 700;
      margin-top: 0.1rem;
    }}
    .ar-body {{ flex: 1; }}
    .ar-text {{ font-size: 0.9rem; margin-bottom: 0.3rem; }}
    .ar-urgency {{
      font-size: 0.68rem; font-weight: 700;
      padding: 0.15rem 0.5rem; border-radius: 99px;
    }}
    .ar-urgency.high  {{ background: var(--fail-light);  color: var(--fail); }}
    .ar-urgency.medium{{ background: var(--warn-light);  color: var(--warn); }}
    .ar-urgency.low   {{ background: var(--pass-light);  color: var(--pass); }}

    /* ── Raw report fallback ───────────────────── */
    .raw-card {{
      background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 1.5rem; margin-top: 2rem;
    }}
    .raw-card details summary {{
      cursor: pointer; font-size: 0.85rem; font-weight: 700; color: var(--muted);
      user-select: none;
    }}
    .raw-card pre {{
      background: #0f172a; color: #e2e8f0;
      padding: 1.25rem; border-radius: 8px;
      font-size: 0.78rem; line-height: 1.6;
      overflow-x: auto; margin-top: 1rem;
      white-space: pre-wrap; word-break: break-word;
    }}

    /* ── Footer ────────────────────────────────── */
    .footer {{
      text-align: center; font-size: 0.78rem; color: var(--muted);
      margin-top: 3rem; padding-top: 1.5rem;
      border-top: 1px solid var(--border);
    }}
    .footer a {{ color: var(--info); text-decoration: none; }}

    /* ── Responsive ────────────────────────────── */
    @media (max-width: 900px) {{
      .pillar-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    @media (max-width: 700px) {{
      .sidebar {{ display: none; }}
      .main {{ margin-left: 0; padding: 1rem 0.75rem 4rem; }}
      .pillar-grid {{ grid-template-columns: 1fr; }}
      .hero {{ flex-direction: column; }}
    }}
  </style>
</head>
<body>

<!-- ── Sidebar ───────────────────────────────────────────── -->
<aside class="sidebar">
  <div class="sidebar-logo">agent-waf-reviewer</div>
  <div class="sidebar-title">WAF Review Report</div>
  <div class="sidebar-target">{target_abs}</div>

  <div class="sidebar-section">Navigation</div>
  <a href="#summary" class="nav-link">📊 Executive Summary</a>
  <a href="#actions" class="nav-link">🎯 Priority Actions</a>

  <div class="sidebar-section">Pillars</div>
  {nav_items}

  <div class="sidebar-section">Details</div>
  <a href="#raw" class="nav-link">📄 Full Report</a>
</aside>

<!-- ── Main ──────────────────────────────────────────────── -->
<main class="main">

  <!-- Hero -->
  <div class="hero" id="summary">
    <div class="hero-left">
      <h1>Well-Architected<br>Framework Review</h1>
      <div class="hero-sub">{timestamp}</div>
      <div class="hero-target">{target_abs}</div>
    </div>
    <div class="hero-score">
      <div class="hs-num" style="color:{score_color}">{score_pct}%</div>
      <div class="hs-label">{score_display} checks passing</div>
      <div class="hs-grade {grade_cls}">{grade}</div>
    </div>
  </div>

  <!-- Pillar summary cards -->
  <div class="section-title">Pillar Overview</div>
  <div class="pillar-grid">
    {pillar_cards}
  </div>

  <!-- Priority actions -->
  {'<div class="section-title" id="actions">Priority Actions</div>' if action_rows else ''}
  {'<div class="actions-card"><div class="actions-header">🎯 Top Actions to Fix First</div>' + action_rows + '</div>' if action_rows else ''}

  <!-- Pillar details -->
  <div class="section-title">Detailed Findings</div>
  {pillar_sections}

  <!-- Raw report collapsible -->
  <div class="raw-card" id="raw">
    <details>
      <summary>Full Agent Report (raw text)</summary>
      <pre>{report_text.replace("<", "&lt;").replace(">", "&gt;")}</pre>
    </details>
  </div>

  <div class="footer">
    Generated by <a href="https://github.com/wb-platform-engineering-lab/agent-waf-reviewer">agent-waf-reviewer</a>
    · claude-sonnet-4-6 · {timestamp}
  </div>

</main>

<script>
  // Highlight active sidebar link on scroll
  const sections = document.querySelectorAll('[id^="pillar-"], #summary, #actions, #raw');
  const links = document.querySelectorAll('.nav-link');
  const obs = new IntersectionObserver(entries => {{
    entries.forEach(e => {{
      if (e.isIntersecting) {{
        links.forEach(l => l.style.background = '');
        links.forEach(l => l.style.color = '');
        const a = document.querySelector(`.nav-link[href="#${{e.target.id}}"]`);
        if (a) {{ a.style.background = '#1e293b'; a.style.color = '#f1f5f9'; }}
      }}
    }});
  }}, {{ rootMargin: '-20% 0px -70% 0px' }});
  sections.forEach(s => obs.observe(s));
</script>

</body>
</html>"""


def save_report(report_text: str, target_path: str, output_dir: str = ".") -> str:
    """Save the HTML report and return the file path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_name = os.path.basename(os.path.abspath(target_path))
    filename = f"waf_review_{target_name}_{timestamp}.html"
    output_path = os.path.join(output_dir, filename)

    html = generate_html(report_text, target_path)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
