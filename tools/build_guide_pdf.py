"""Build the comprehensive project guide as a PDF.

Uses Edge or Chrome in headless mode to print styled HTML to PDF.
No third-party Python packages required.
"""

from __future__ import annotations

import html
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


SOURCE = Path(__file__).resolve().parent.parent / "docs" / "COMPREHENSIVE_PROJECT_GUIDE.md"
OUTPUT = Path(__file__).resolve().parent.parent / "COMPREHENSIVE_PROJECT_GUIDE.pdf"


def find_browser() -> Path:
    candidates = [
        shutil.which("msedge"),
        shutil.which("chrome"),
        shutil.which("chromium"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return Path(c)
    raise RuntimeError("No supported browser found (Edge or Chrome required).")


def inline_markup(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


def is_table_line(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2


def render_table(lines: list[str]) -> str:
    rows = [[cell.strip() for cell in l.strip().strip("|").split("|")] for l in lines]
    if len(rows) >= 2 and all(re.fullmatch(r":?-{3,}:?", c) for c in rows[1]):
        header, body_rows = rows[0], rows[2:]
    else:
        header, body_rows = [], rows

    parts = ["<table>"]
    if header:
        parts.append("<thead><tr>")
        parts.extend(f"<th>{inline_markup(c)}</th>" for c in header)
        parts.append("</tr></thead>")
    parts.append("<tbody>")
    for row in body_rows:
        parts.append("<tr>")
        parts.extend(f"<td>{inline_markup(c)}</td>" for c in row)
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "\n".join(parts)


def markdown_to_html(md: str, title: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    in_code = False
    in_list = False
    in_ol = False
    in_table = False
    code_lines: list[str] = []
    table_lines: list[str] = []

    def close_lists():
        nonlocal in_list, in_ol
        if in_list:
            out.append("</ul>")
            in_list = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    def close_table():
        nonlocal in_table, table_lines
        if not in_table:
            return
        out.append(render_table(table_lines))
        table_lines = []
        in_table = False

    for raw in lines:
        line = raw.rstrip()

        if line.startswith("```"):
            close_table()
            close_lists()
            if in_code:
                out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(raw)
            continue

        if is_table_line(line):
            close_lists()
            in_table = True
            table_lines.append(line)
            continue
        close_table()

        if not line.strip():
            close_lists()
            continue

        # Horizontal rule
        if re.fullmatch(r"-{3,}", line.strip()):
            close_lists()
            out.append("<hr>")
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            close_lists()
            lvl = len(heading.group(1))
            out.append(f"<h{lvl}>{inline_markup(heading.group(2))}</h{lvl}>")
            continue

        ul = re.match(r"^[-*]\s+(.*)$", line)
        if ul:
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline_markup(ul.group(1))}</li>")
            continue

        ol = re.match(r"^\d+\.\s+(.*)$", line)
        if ol:
            if in_list:
                out.append("</ul>")
                in_list = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{inline_markup(ol.group(1))}</li>")
            continue

        close_lists()
        out.append(f"<p>{inline_markup(line)}</p>")

    if in_code:
        out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    close_table()
    close_lists()

    body = "\n".join(out)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    @page {{
      margin: 18mm 16mm;
      @bottom-center {{
        content: counter(page);
        font-size: 9pt;
        color: #888;
      }}
    }}
    body {{
      color: #18212f;
      font-family: 'Segoe UI', Arial, Helvetica, sans-serif;
      font-size: 10.5pt;
      line-height: 1.55;
    }}
    h1, h2, h3, h4, h5, h6 {{
      color: #0f1a2e;
      line-height: 1.2;
      margin: 1em 0 0.3em;
      page-break-after: avoid;
    }}
    h1 {{
      font-size: 26pt;
      border-bottom: 3px solid #1a73e8;
      padding-bottom: 8px;
      color: #1a73e8;
    }}
    h2 {{
      font-size: 17pt;
      border-bottom: 1.5px solid #e0e5f0;
      padding-bottom: 5px;
      color: #1a56a8;
      margin-top: 1.4em;
    }}
    h3 {{
      font-size: 13pt;
      color: #2d5f9e;
    }}
    h4 {{
      font-size: 11pt;
      color: #3a6fb0;
    }}
    p {{
      margin: 0.4em 0;
    }}
    a {{
      color: #1a73e8;
      text-decoration: none;
    }}
    code {{
      background: #f0f4fa;
      border: 1px solid #d8e2f0;
      border-radius: 3px;
      font-family: Consolas, 'Courier New', monospace;
      font-size: 9pt;
      padding: 1px 4px;
    }}
    pre {{
      background: #f8faff;
      border: 1px solid #d0daea;
      border-radius: 6px;
      overflow-wrap: anywhere;
      padding: 10px 12px;
      white-space: pre-wrap;
      font-size: 9pt;
      line-height: 1.45;
      page-break-inside: avoid;
    }}
    pre code {{
      background: transparent;
      border: 0;
      padding: 0;
    }}
    table {{
      border-collapse: collapse;
      margin: 0.6em 0;
      width: 100%;
      font-size: 9.5pt;
      page-break-inside: avoid;
    }}
    th, td {{
      border: 1px solid #d0daea;
      padding: 5px 8px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #e8eef8;
      font-weight: 700;
      color: #1a3a6e;
    }}
    tr:nth-child(even) td {{
      background: #f8faff;
    }}
    hr {{
      border: none;
      border-top: 2px solid #e0e5f0;
      margin: 1.5em 0;
    }}
    ul, ol {{
      padding-left: 1.3em;
    }}
    li {{
      margin: 0.25em 0;
    }}
    strong {{
      color: #0f1a2e;
    }}
    blockquote {{
      border-left: 4px solid #1a73e8;
      color: #4b5a70;
      margin: 0.8em 0;
      padding: 0.1em 0 0.1em 1em;
      background: #f0f4fa;
      border-radius: 0 6px 6px 0;
    }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def main() -> int:
    if not SOURCE.exists():
        print(f"Source not found: {SOURCE}", file=sys.stderr)
        return 1

    browser = find_browser()
    print(f"Using browser: {browser}")

    md = SOURCE.read_text(encoding="utf-8")
    rendered = markdown_to_html(md, "Buffer Overflow Security Project — Comprehensive Guide")

    fd, html_path = tempfile.mkstemp(suffix=".html")
    os.close(fd)
    html_file = Path(html_path)
    html_file.write_text(rendered, encoding="utf-8")

    command = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--print-to-pdf={OUTPUT}",
        html_file.as_uri(),
    ]

    print(f"Building PDF: {OUTPUT}")
    result = subprocess.run(command, text=True, capture_output=True)
    html_file.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"Error: {result.stderr.strip() or result.stdout.strip()}", file=sys.stderr)
        return 1

    size_kb = OUTPUT.stat().st_size / 1024
    print(f"Done! PDF saved: {OUTPUT} ({size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
