"""Build the From-Zero Guide as a PDF using headless Edge/Chrome."""
from __future__ import annotations
import html, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent / "docs" / "FROM_ZERO_GUIDE.md"
OUTPUT = Path(__file__).resolve().parent.parent / "FROM_ZERO_TO_HERO_GUIDE.pdf"

def find_browser() -> Path:
    for c in [shutil.which("msedge"), shutil.which("chrome"),
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe"]:
        if c and Path(c).exists(): return Path(c)
    raise RuntimeError("No browser found")

def il(t):
    e=html.escape(t); e=re.sub(r"`([^`]+)`",r"<code>\1</code>",e)
    e=re.sub(r"\*\*([^*]+)\*\*",r"<strong>\1</strong>",e)
    e=re.sub(r"\[([^\]]+)\]\(([^)]+)\)",r'<a href="\2">\1</a>',e); return e

def is_tbl(l): s=l.strip(); return s.startswith("|") and s.endswith("|") and s.count("|")>=2

def rtbl(lines):
    rows=[[c.strip() for c in l.strip().strip("|").split("|")] for l in lines]
    if len(rows)>=2 and all(re.fullmatch(r":?-{3,}:?",c) for c in rows[1]): h,b=rows[0],rows[2:]
    else: h,b=[],rows
    p=["<table>"]
    if h: p.append("<thead><tr>"); p.extend(f"<th>{il(c)}</th>" for c in h); p.append("</tr></thead>")
    p.append("<tbody>")
    for r in b: p.append("<tr>"); p.extend(f"<td>{il(c)}</td>" for c in r); p.append("</tr>")
    p.append("</tbody></table>"); return "\n".join(p)

def md2html(md,title):
    lines=md.splitlines(); out=[]; ic=False; iul=False; iol=False; it=False; cl=[]; tl=[]
    def cll():
        nonlocal iul,iol
        if iul: out.append("</ul>"); iul=False
        if iol: out.append("</ol>"); iol=False
    def ct():
        nonlocal it,tl
        if not it: return
        out.append(rtbl(tl)); tl=[]; it=False
    for raw in lines:
        line=raw.rstrip()
        if line.startswith("```"):
            ct(); cll()
            if ic: out.append("<pre><code>"+html.escape("\n".join(cl))+"</code></pre>"); cl=[]; ic=False
            else: ic=True
            continue
        if ic: cl.append(raw); continue
        if is_tbl(line): cll(); it=True; tl.append(line); continue
        ct()
        if not line.strip(): cll(); continue
        if re.fullmatch(r"-{3,}",line.strip()): cll(); out.append("<hr>"); continue
        h=re.match(r"^(#{1,6})\s+(.*)$",line)
        if h: cll(); lvl=len(h.group(1)); out.append(f"<h{lvl}>{il(h.group(2))}</h{lvl}>"); continue
        u=re.match(r"^[-*]\s+(.*)$",line)
        if u:
            if iol: out.append("</ol>"); iol=False
            if not iul: out.append("<ul>"); iul=True
            out.append(f"<li>{il(u.group(1))}</li>"); continue
        o=re.match(r"^\d+\.\s+(.*)$",line)
        if o:
            if iul: out.append("</ul>"); iul=False
            if not iol: out.append("<ol>"); iol=True
            out.append(f"<li>{il(o.group(1))}</li>"); continue
        cll(); out.append(f"<p>{il(line)}</p>")
    if ic: out.append("<pre><code>"+html.escape("\n".join(cl))+"</code></pre>")
    ct(); cll()
    body="\n".join(out)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{html.escape(title)}</title><style>
@page{{margin:20mm 17mm}}body{{color:#18212f;font-family:'Segoe UI',Arial,sans-serif;font-size:10.5pt;line-height:1.6}}
h1,h2,h3,h4{{color:#0f1a2e;line-height:1.2;margin:1em 0 .3em;page-break-after:avoid}}
h1{{font-size:26pt;border-bottom:3px solid #1a73e8;padding-bottom:8px;color:#1a73e8}}
h2{{font-size:17pt;border-bottom:1.5px solid #e0e5f0;padding-bottom:5px;color:#1a56a8;margin-top:1.4em}}
h3{{font-size:13pt;color:#2d5f9e}}h4{{font-size:11pt;color:#3a6fb0}}
p{{margin:.4em 0}}a{{color:#1a73e8;text-decoration:none}}
code{{background:#f0f4fa;border:1px solid #d8e2f0;border-radius:3px;font-family:Consolas,'Courier New',monospace;font-size:9pt;padding:1px 4px}}
pre{{background:#f8faff;border:1px solid #d0daea;border-radius:6px;overflow-wrap:anywhere;padding:10px 12px;white-space:pre-wrap;font-size:9pt;line-height:1.45;page-break-inside:avoid}}
pre code{{background:transparent;border:0;padding:0}}
table{{border-collapse:collapse;margin:.6em 0;width:100%;font-size:9.5pt;page-break-inside:avoid}}
th,td{{border:1px solid #d0daea;padding:5px 8px;text-align:left;vertical-align:top}}
th{{background:#e8eef8;font-weight:700;color:#1a3a6e}}tr:nth-child(even) td{{background:#f8faff}}
hr{{border:none;border-top:2px solid #e0e5f0;margin:1.5em 0}}ul,ol{{padding-left:1.3em}}li{{margin:.25em 0}}
strong{{color:#0f1a2e}}
</style></head><body>{body}</body></html>"""

def main():
    if not SOURCE.exists(): print(f"Missing: {SOURCE}",file=sys.stderr); return 1
    browser=find_browser(); print(f"Browser: {browser}")
    rendered=md2html(SOURCE.read_text(encoding="utf-8"),"Buffer Overflow — From Zero to Hero Guide")
    fd,hp=tempfile.mkstemp(suffix=".html"); os.close(fd); hf=Path(hp)
    hf.write_text(rendered,encoding="utf-8")
    print(f"Building PDF: {OUTPUT}")
    r=subprocess.run([str(browser),"--headless=new","--disable-gpu","--no-sandbox",f"--print-to-pdf={OUTPUT}",hf.as_uri()],text=True,capture_output=True)
    hf.unlink(missing_ok=True)
    if r.returncode!=0: print(f"Error: {r.stderr.strip()}",file=sys.stderr); return 1
    print(f"Done! {OUTPUT} ({OUTPUT.stat().st_size/1024:.0f} KB)"); return 0

if __name__=="__main__": raise SystemExit(main())
