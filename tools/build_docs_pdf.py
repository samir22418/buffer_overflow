"""Build PDF documentation from curated Markdown files.

The script intentionally uses only the Python standard library and a locally
installed browser. It converts Markdown to simple HTML, then asks Edge or Chrome
to print that HTML to PDF.
"""

from __future__ import annotations

import argparse
import html
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "docs" / "pdf"

DOCUMENTS = [
    (ROOT / "README.md", "project-readme.pdf", "Project README"),
    (ROOT / "docs" / "project_documentation.md", "full-project-documentation.pdf", "Full Project Documentation"),
    (ROOT / "buffer_lab" / "README.md", "buffer-lab-readme.pdf", "Buffer Lab README"),
    (ROOT / "examples" / "README.md", "examples-readme.pdf", "Examples README"),
    (ROOT / "tests" / "README.md", "tests-readme.pdf", "Tests README"),
    (ROOT / "tools" / "README.md", "tools-readme.pdf", "Tools README"),
    (ROOT / "docs" / "README.md", "docs-readme.pdf", "Docs README"),
    (ROOT / "docs" / "implementation_validation.md", "implementation-validation.pdf", "Implementation Validation"),
    (ROOT / "college-pentest-lab" / "README.md", "college-pentest-lab-readme.pdf", "College Pentest Lab README"),
    (ROOT / "college-pentest-lab" / "attacker" / "README.md", "college-pentest-lab-attacker-readme.pdf", "Attacker README"),
    (ROOT / "college-pentest-lab" / "victim" / "README.md", "college-pentest-lab-victim-readme.pdf", "Victim README"),
    (ROOT / "college-pentest-lab" / "docs" / "README.md", "college-pentest-lab-docs-readme.pdf", "College Lab Docs README"),
    (ROOT / "college-pentest-lab" / "docs" / "student-guide.md", "student-guide.pdf", "Student Guide"),
    (ROOT / "college-pentest-lab" / "docs" / "instructor-notes.md", "instructor-notes.pdf", "Instructor Notes"),
    (ROOT / "college-pentest-lab" / "docs" / "report-template.md", "report-template.pdf", "Report Template"),
]


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
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    raise RuntimeError("No supported browser found. Install Edge or Chrome to build PDFs.")


def markdown_to_html(markdown: str, title: str) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    in_code = False
    in_list = False
    in_ordered_list = False
    in_table = False
    code_lines: list[str] = []
    table_lines: list[str] = []

    def close_lists() -> None:
        nonlocal in_list, in_ordered_list
        if in_list:
            output.append("</ul>")
            in_list = False
        if in_ordered_list:
            output.append("</ol>")
            in_ordered_list = False

    def close_table() -> None:
        nonlocal in_table, table_lines
        if not in_table:
            return
        output.append(render_table(table_lines))
        table_lines = []
        in_table = False

    for raw_line in lines:
        line = raw_line.rstrip()

        if line.startswith("```"):
            close_table()
            close_lists()
            if in_code:
                output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(raw_line)
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

        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            close_lists()
            level = len(heading.group(1))
            output.append(f"<h{level}>{inline_markup(heading.group(2))}</h{level}>")
            continue

        unordered = re.match(r"^-\s+(.*)$", line)
        if unordered:
            if in_ordered_list:
                output.append("</ol>")
                in_ordered_list = False
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{inline_markup(unordered.group(1))}</li>")
            continue

        ordered = re.match(r"^\d+\.\s+(.*)$", line)
        if ordered:
            if in_list:
                output.append("</ul>")
                in_list = False
            if not in_ordered_list:
                output.append("<ol>")
                in_ordered_list = True
            output.append(f"<li>{inline_markup(ordered.group(1))}</li>")
            continue

        close_lists()
        output.append(f"<p>{inline_markup(line)}</p>")

    if in_code:
        output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    close_table()
    close_lists()

    body = "\n".join(output)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    @page {{ margin: 18mm 16mm; }}
    body {{
      color: #18212f;
      font-family: Arial, Helvetica, sans-serif;
      font-size: 11pt;
      line-height: 1.5;
    }}
    h1, h2, h3, h4, h5, h6 {{
      color: #102030;
      line-height: 1.2;
      margin: 1.1em 0 0.35em;
      page-break-after: avoid;
    }}
    h1 {{ font-size: 24pt; border-bottom: 2px solid #d8dee8; padding-bottom: 8px; }}
    h2 {{ font-size: 17pt; border-bottom: 1px solid #e5e9f0; padding-bottom: 5px; }}
    h3 {{ font-size: 13.5pt; }}
    p {{ margin: 0.45em 0; }}
    code {{
      background: #f2f4f7;
      border: 1px solid #e0e5ec;
      border-radius: 3px;
      font-family: Consolas, 'Courier New', monospace;
      font-size: 9.5pt;
      padding: 1px 3px;
    }}
    pre {{
      background: #f8fafc;
      border: 1px solid #d8dee8;
      border-radius: 6px;
      overflow-wrap: anywhere;
      padding: 10px;
      white-space: pre-wrap;
    }}
    pre code {{ background: transparent; border: 0; padding: 0; }}
    table {{
      border-collapse: collapse;
      margin: 0.7em 0;
      width: 100%;
    }}
    th, td {{
      border: 1px solid #d8dee8;
      padding: 5px 7px;
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: #f2f4f7; }}
    blockquote {{
      border-left: 4px solid #ccd5e1;
      color: #4b5563;
      margin: 0.8em 0;
      padding: 0.1em 0 0.1em 0.9em;
    }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def render_table(lines: list[str]) -> str:
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    if len(rows) >= 2 and all(re.fullmatch(r":?-{3,}:?", cell) for cell in rows[1]):
        header = rows[0]
        body_rows = rows[2:]
    else:
        header = []
        body_rows = rows

    parts = ["<table>"]
    if header:
        parts.append("<thead><tr>")
        parts.extend(f"<th>{inline_markup(cell)}</th>" for cell in header)
        parts.append("</tr></thead>")
    parts.append("<tbody>")
    for row in body_rows:
        parts.append("<tr>")
        parts.extend(f"<td>{inline_markup(cell)}</td>" for cell in row)
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "\n".join(parts)


def inline_markup(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


def file_url(path: Path) -> str:
    return path.resolve().as_uri()


def build_pdf(browser: Path, source: Path, target: Path, title: str, keep_html: bool) -> None:
    markdown = source.read_text(encoding="utf-8")
    rendered = markdown_to_html(markdown, title)
    if keep_html:
        html_target = target.with_suffix(".html")
    else:
        fd, html_path = tempfile.mkstemp(suffix=".html")
        os.close(fd)
        html_target = Path(html_path)
    html_target.write_text(rendered, encoding="utf-8")

    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--print-to-pdf={target}",
        file_url(html_target),
    ]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if not keep_html:
        html_target.unlink(missing_ok=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"PDF build failed for {source}: {completed.stderr.strip() or completed.stdout.strip()}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build project documentation PDFs")
    parser.add_argument("--keep-html", action="store_true", help="keep generated HTML next to the PDFs")
    args = parser.parse_args()

    browser = find_browser()
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    built = 0
    for source, pdf_name, title in DOCUMENTS:
        if not source.exists():
            print(f"skip missing: {source.relative_to(ROOT)}", file=sys.stderr)
            continue
        target = PDF_DIR / pdf_name
        build_pdf(browser, source, target, title, args.keep_html)
        print(f"built {target.relative_to(ROOT)}")
        built += 1

    print(f"built {built} PDF files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
