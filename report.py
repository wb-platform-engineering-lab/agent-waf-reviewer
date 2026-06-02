"""
Converts the agent's text review into a styled HTML report.
"""

import os
import re
from datetime import datetime


def _badge(text: str) -> str:
    text = text.strip()
    if "FAIL" in text:
        return f'<span class="badge fail">{text}</span>'
    if "WARN" in text:
        return f'<span class="badge warn">{text}</span>'
    if "PASS" in text:
        return f'<span class="badge pass">{text}</span>'
    return f'<span class="badge info">{text}</span>'


def _render_line(line: str) -> str:
    """Convert a single text line to HTML."""
    stripped = line.strip()

    # Section header (═══)
    if re.match(r"^[═─]{10,}", stripped):
        return ""

    # Pillar header line
    m = re.match(r"^Pillar (\d) — (.+?)\s+([❌⚠️✅ FAILWARNPASS]+)\s+(\d+/\d+)", stripped)
    if m:
        icon = "✅" if "PASS" in m.group(3) else ("❌" if "FAIL" in m.group(3) else "⚠️")
        cls = "pass" if "PASS" in m.group(3) else ("fail" if "FAIL" in m.group(3) else "warn")
        return (
            f'<div class="pillar-header {cls}">'
            f'<span class="pillar-title">Pillar {m.group(1)} — {m.group(2)}</span>'
            f'<span class="pillar-meta">{icon} {m.group(3).strip()}  {m.group(4)} checks passing</span>'
            f'</div>'
        )

    # Check line:  ❌ FAIL  [P1-001] Name
    m = re.match(r"^\s*(❌|⚠️|✅|ℹ️)\s*(FAIL|WARN|PASS|INFO)\s+\[([A-Z0-9\-]+)\]\s+(.+)", stripped)
    if m:
        icon, status, check_id, name = m.group(1), m.group(2), m.group(3), m.group(4)
        cls = {"FAIL": "fail", "WARN": "warn", "PASS": "pass", "INFO": "info"}.get(status, "info")
        return (
            f'<div class="check-row">'
            f'<span class="check-status {cls}">{icon} {status}</span>'
            f'<span class="check-id">[{check_id}]</span>'
            f'<span class="check-name">{name}</span>'
            f'</div>'
        )

    # Arrow recommendation line
    if stripped.startswith("→") or stripped.startswith("→"):
        msg = stripped.lstrip("→").strip()
        return f'<div class="check-recommendation">→ {msg}</div>'

    # Overall score line
    m = re.match(r"^Overall:\s*(\d+/\d+)", stripped)
    if m:
        return f'<div class="overall-score">Overall: <strong>{m.group(1)}</strong> checks passing</div>'

    # Scan header
    if re.match(r"^Automated pillar checks", stripped):
        return f'<p class="scan-header">{stripped}</p>'

    # Numbered list item (1. 2. etc)
    m = re.match(r"^(\d+)\.\s+(.+)", stripped)
    if m:
        return f'<div class="action-item"><span class="action-num">{m.group(1)}</span><span>{m.group(2)}</span></div>'

    # Bullet
    if stripped.startswith("- ") or stripped.startswith("• "):
        return f'<li>{stripped[2:]}</li>'

    # Heading-like lines (all caps or starts with ##)
    if stripped.startswith("##"):
        return f'<h3>{stripped.lstrip("#").strip()}</h3>'
    if stripped.isupper() and len(stripped) > 4:
        return f'<h3>{stripped}</h3>'

    # Bold pattern **text**
    stripped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
    # Inline code `text`
    stripped = re.sub(r"`([^`]+)`", r"<code>\1</code>", stripped)

    if stripped:
        return f'<p>{stripped}</p>'
    return '<div class="spacer"></div>'


def generate_html(report_text: str, target_path: str) -> str:
    """Convert the plain-text agent report to a full HTML page."""

    lines_html = "\n".join(_render_line(line) for line in report_text.split("\n"))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    target_abs = os.path.abspath(target_path)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>WAF Review — {os.path.basename(target_abs)}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --text: #1a1a1a; --muted: #555; --border: #e0e0e0;
      --pass: #16a34a; --pass-bg: #f0fdf4; --pass-border: #86efac;
      --fail: #dc2626; --fail-bg: #fef2f2; --fail-border: #fca5a5;
      --warn: #d97706; --warn-bg: #fffbeb; --warn-border: #fde68a;
      --info: #2563eb; --info-bg: #eff6ff; --info-border: #93c5fd;
      --accent: #2563eb;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      color: var(--text); line-height: 1.7; background: #f8f9fa;
      padding: 2rem 1rem 6rem;
    }}
    .container {{ max-width: 860px; margin: 0 auto; }}

    /* Header */
    .report-header {{
      background: #1a1a2e; color: #fff;
      border-radius: 12px; padding: 2rem 2.5rem; margin-bottom: 2rem;
    }}
    .report-header h1 {{ font-size: 1.6rem; font-weight: 800; margin-bottom: 0.4rem; }}
    .report-header .meta {{ font-size: 0.85rem; color: #94a3b8; }}
    .report-header .target {{ font-family: monospace; color: #7dd3fc; font-size: 0.9rem; margin-top: 0.5rem; }}

    /* Content card */
    .card {{
      background: #fff; border-radius: 10px;
      border: 1px solid var(--border);
      padding: 2rem; margin-bottom: 1.5rem;
    }}

    /* Pillar header */
    .pillar-header {{
      display: flex; justify-content: space-between; align-items: center;
      padding: 0.9rem 1.2rem; border-radius: 8px; margin: 1.5rem 0 0.5rem;
      border-left: 4px solid;
    }}
    .pillar-header.pass {{ background: var(--pass-bg); border-color: var(--pass); }}
    .pillar-header.fail {{ background: var(--fail-bg); border-color: var(--fail); }}
    .pillar-header.warn {{ background: var(--warn-bg); border-color: var(--warn); }}
    .pillar-title {{ font-weight: 700; font-size: 1rem; }}
    .pillar-meta {{ font-size: 0.82rem; color: var(--muted); }}

    /* Check rows */
    .check-row {{
      display: flex; align-items: baseline; gap: 0.6rem;
      padding: 0.35rem 0.5rem; border-bottom: 1px solid #f0f0f0;
      font-size: 0.88rem;
    }}
    .check-row:last-child {{ border-bottom: none; }}
    .check-status {{
      font-weight: 700; font-size: 0.75rem; min-width: 70px;
      padding: 0.15rem 0.5rem; border-radius: 99px; text-align: center;
    }}
    .check-status.pass {{ background: var(--pass-bg); color: var(--pass); }}
    .check-status.fail {{ background: var(--fail-bg); color: var(--fail); }}
    .check-status.warn {{ background: var(--warn-bg); color: var(--warn); }}
    .check-status.info {{ background: var(--info-bg); color: var(--info); }}
    .check-id {{ font-family: monospace; font-size: 0.78rem; color: #999; min-width: 70px; }}
    .check-name {{ color: var(--text); }}
    .check-recommendation {{
      font-size: 0.84rem; color: var(--muted);
      padding: 0.2rem 0.5rem 0.2rem 1.5rem; margin-bottom: 0.3rem;
    }}

    /* Score */
    .overall-score {{
      font-size: 1.1rem; font-weight: 700;
      padding: 1rem 1.2rem; background: #f8f9fa;
      border-radius: 8px; border: 1px solid var(--border);
      margin: 1.5rem 0;
    }}

    /* Action items */
    .action-item {{
      display: flex; gap: 0.75rem; align-items: flex-start;
      padding: 0.6rem 0; border-bottom: 1px solid var(--border);
      font-size: 0.9rem;
    }}
    .action-item:last-child {{ border-bottom: none; }}
    .action-num {{
      flex-shrink: 0; width: 24px; height: 24px;
      background: var(--accent); color: #fff;
      border-radius: 50%; display: flex; align-items: center;
      justify-content: center; font-size: 0.75rem; font-weight: 700;
    }}

    /* Typography */
    h3 {{ font-size: 1.05rem; font-weight: 700; margin: 1.5rem 0 0.75rem; }}
    p {{ margin-bottom: 0.75rem; font-size: 0.92rem; }}
    li {{ margin-left: 1.5rem; font-size: 0.9rem; margin-bottom: 0.3rem; }}
    code {{
      font-family: monospace; font-size: 0.85em;
      background: #f4f4f5; padding: 0.1em 0.35em; border-radius: 4px;
    }}
    .scan-header {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 0.5rem; }}
    .spacer {{ height: 0.5rem; }}

    /* Badge */
    .badge {{
      display: inline-block; font-size: 0.72rem; font-weight: 600;
      padding: 0.2rem 0.6rem; border-radius: 99px;
    }}
    .badge.pass {{ background: var(--pass-bg); color: var(--pass); }}
    .badge.fail {{ background: var(--fail-bg); color: var(--fail); }}
    .badge.warn {{ background: var(--warn-bg); color: var(--warn); }}

    /* Footer */
    .report-footer {{
      text-align: center; font-size: 0.8rem; color: #999; margin-top: 3rem;
    }}
  </style>
</head>
<body>
<div class="container">

  <div class="report-header">
    <h1>Well-Architected Framework Review</h1>
    <div class="target">{target_abs}</div>
    <div class="meta">Generated {timestamp} · claude-sonnet-4-6 · agent-waf-reviewer</div>
  </div>

  <div class="card">
    {lines_html}
  </div>

  <div class="report-footer">
    agent-waf-reviewer · <a href="https://github.com/wb-platform-engineering-lab/agent-waf-reviewer">github.com/wb-platform-engineering-lab/agent-waf-reviewer</a>
  </div>

</div>
</body>
</html>"""


def save_report(report_text: str, target_path: str, output_dir: str = ".") -> str:
    """Save the HTML report to a file and return the file path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_name = os.path.basename(os.path.abspath(target_path))
    filename = f"waf_review_{target_name}_{timestamp}.html"
    output_path = os.path.join(output_dir, filename)

    html = generate_html(report_text, target_path)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
