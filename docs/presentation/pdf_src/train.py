import sys,re; sys.path.insert(0,'/tmp/claude-0/pdf')
import markdown
from common import FONTS, BASE
CSS = BASE + """
@page{size:A4;margin:16mm 15mm 18mm 15mm}
body{font-size:10.5pt;line-height:1.55;background:#fff}
.cover{height:262mm;background:radial-gradient(900px 500px at 90% 0%,#0E3A4D 0%,#0B1220 60%);color:#fff;border-radius:14px;padding:22mm 18mm;position:relative;page-break-after:always}
.cover .kick{color:#06B6D4;font-weight:800;letter-spacing:.2em;font-size:10pt}
.cover h1{font-size:40pt;font-weight:900;line-height:1.05;margin-top:40mm;letter-spacing:-.02em}
.cover .sub{font-size:15pt;color:#B6C2D6;margin-top:6mm}
.cover .meta{position:absolute;bottom:20mm;left:18mm;right:18mm;display:grid;grid-template-columns:repeat(3,1fr);gap:8mm;font-size:9.5pt;color:#B6C2D6}
.cover .meta b{display:block;color:#fff;font-size:12pt}
h1.sec{font-size:22pt;font-weight:900;letter-spacing:-.01em;margin:0 0 4mm;padding-top:2mm;page-break-before:always;border-bottom:3px solid #06B6D4;padding-bottom:3mm}
h1.sec small{display:block;font-size:9pt;color:#06B6D4;letter-spacing:.2em;text-transform:uppercase;font-weight:800}
h2{font-size:14.5pt;font-weight:800;margin:7mm 0 3mm;color:#0B1220}
h3{font-size:12pt;font-weight:800;margin:5mm 0 2mm}
p{margin:0 0 2.5mm}ul,ol{margin:0 0 3mm 6mm}li{margin:1mm 0}
table{width:100%;border-collapse:collapse;margin:2mm 0 5mm;font-size:9.5pt;page-break-inside:auto}
tr{page-break-inside:avoid}
th{background:#0B1220;color:#fff;text-align:left;padding:2.2mm 3mm;font-weight:700;font-size:9pt}
td{padding:2.2mm 3mm;border-bottom:1px solid #E2E8F0;vertical-align:top}tr:nth-child(even) td{background:#F8FAFC}
blockquote{border-left:4px solid #06B6D4;background:#ECFEFF;padding:3mm 4mm;margin:2mm 0 4mm;border-radius:0 8px 8px 0;page-break-inside:avoid}
pre{background:#0B1220;color:#E2E8F0;padding:4mm;border-radius:8px;font-family:'JetBrains Mono',monospace;font-size:8.6pt;line-height:1.5;white-space:pre-wrap;margin:2mm 0 4mm;page-break-inside:avoid}
pre code{background:none;padding:0;color:inherit}
hr{display:none}
.box{border-radius:10px;padding:4mm 5mm;margin:3mm 0 5mm;page-break-inside:avoid}
.tip{background:#ECFDF5;border:1px solid #A7F3D0}.warn{background:#FEF2F2;border:1px solid #FECACA}.info{background:#EFF6FF;border:1px solid #BFDBFE}
.box b.t{display:block;font-size:10pt;letter-spacing:.06em;text-transform:uppercase;margin-bottom:1.5mm}
.slide{display:grid;grid-template-columns:20mm 1fr;gap:4mm;border:1px solid #E2E8F0;border-radius:10px;padding:4mm;margin-bottom:3.5mm;page-break-inside:avoid}
.slide .no{background:#0B1220;color:#fff;border-radius:8px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-weight:900;font-size:16pt}
.slide .no small{font-size:7.5pt;font-weight:600;color:#06B6D4}
.slide h4{font-size:11pt;margin-bottom:1mm}.slide .say{background:#F1F5F9;border-radius:6px;padding:2.5mm 3mm;margin:1.5mm 0;font-style:italic}
.who{display:inline-block;background:#06B6D4;color:#fff;font-size:8pt;font-weight:800;padding:.5mm 2.5mm;border-radius:99px;margin-left:2mm;vertical-align:middle}
.chk{list-style:none;margin-left:0}.chk li:before{content:"☐  ";font-size:12pt;color:#0891B2}
.score td:nth-child(n+2){text-align:center;width:13mm;color:#94A3B8}
.toc li{font-size:11pt;margin:2mm 0}
"""
UR = re.compile(r'([؀-ۿ][؀-ۿ\s‌]*[؀-ۿ]|[؀-ۿ])')
def urdu(h): return UR.sub(r'<span class="ur">\1</span>', h)
def md(t): return markdown.markdown(t, extensions=['tables','fenced_code'])
def sec(no, title, body): return f'<h1 class="sec"><small>Part {no}</small>{title}</h1>{body}'
def box(kind, t, body): return f'<div class="box {kind}"><b class="t">{t}</b>{body}</div>'
def slide(n, t, time, say, tips, who=''):
    w = f'<span class="who">{who}</span>' if who else ''
    return f'<div class="slide"><div class="no">{n:02d}<small>{time}</small></div><div><h4>{t}{w}</h4><div class="say">“{say}”</div><div style="font-size:9.5pt;color:#475569">{tips}</div></div></div>'
def cover(kick, title, sub, meta):
    m=''.join(f'<div>{a}<b>{b}</b></div>' for a,b in meta)
    return f'<div class="cover"><div class="kick">{kick}</div><div style="font-size:44pt;margin-top:30mm">🛡️</div><h1 style="margin-top:4mm">{title}</h1><div class="sub">{sub}</div><div class="meta">{m}</div></div>'
def page(body): return f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>{CSS}</style></head><body>{urdu(body)}</body></html>'
def mdfile(p, drop_title=True):
    t=open(p).read()
    if drop_title: t=t.split('\n',2)[2]
    t=re.sub(r'^## ', '### ', t, flags=re.M)  # demote
    return md(t)
RUBRIC = '<table class="score"><tr><th>Skill (1 = weak, 5 = strong)</th><th>Run 1</th><th>Run 2</th><th>Run 3</th><th>Run 4</th></tr>' + ''.join(f'<tr><td>{x}</td><td>__</td><td>__</td><td>__</td><td>__</td></tr>' for x in [
 'Hook is strong and slow (تیز نہیں)','Problem is clear in 40 seconds','Demo: says where to look','Explains “how it works” simply','Says real numbers correctly (no fake numbers)','Answers in under 30 seconds','Eye contact (آنکھوں سے رابطہ) with judges','Finished on time','Calm when something breaks']) + '</table>'
