import sys; sys.path.insert(0,'/tmp/claude-0/pdf')
from common import FONTS, BASE
CSS = BASE + """
@page{size:1280px 720px;margin:0}
.s{width:1280px;height:720px;position:relative;overflow:hidden;page-break-after:always;background:#fff;padding:90px 110px}
.k{font-size:14px;font-weight:800;letter-spacing:.2em;color:#06B6D4;text-transform:uppercase}
h1{font-size:76px;font-weight:900;letter-spacing:-.03em;line-height:1.05}
h2{font-size:50px;font-weight:800;letter-spacing:-.02em;margin:12px 0 50px;line-height:1.1}
.lead{font-size:26px;color:#64748B;line-height:1.5;max-width:900px}
.row{display:flex;gap:60px}.row>div{flex:1}
.n{font-size:72px;font-weight:900;letter-spacing:-.03em;line-height:1}.l{font-size:19px;color:#64748B;margin-top:12px;line-height:1.4}
.list div{font-size:26px;padding:16px 0;border-bottom:1px solid #E2E8F0;display:flex;justify-content:space-between}
.list b{font-weight:800}.list span{color:#64748B}
.ft{position:absolute;bottom:36px;left:110px;right:110px;display:flex;justify-content:space-between;font-size:14px;color:#94A3B8}
.dot{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:10px}
.note{position:absolute;bottom:80px;left:110px;font-size:16px;color:#94A3B8}
.ok{color:#10B981}.wip{color:#F59E0B}.no{color:#EF4444}
"""
S=[]
def add(b):
    n=len(S)+1; S.append(f'<section class="s">{b}<div class="ft"><span>VisionGuard ULTRA</span><span>{n:02d}</span></div></section>')
def stats(items): return '<div class="row">'+''.join(f'<div><div class="n" style="color:{c}">{v}</div><div class="l">{l}</div></div>' for v,l,c in items)+'</div>'
def lst(rows): return '<div class="list">'+''.join(f'<div><b>{a}</b><span>{b}</span></div>' for a,b in rows)+'</div>'
add('<div class="k">Alibaba AI Hackathon 2026</div><div style="margin-top:150px"><h1>VisionGuard <span style="color:#06B6D4">ULTRA</span></h1><p class="lead" style="margin-top:24px">Smart AI for normal CCTV cameras.<br>Detect → Decide → Dispatch.</p></div><div class="note" style="color:#64748B;font-size:19px">Abdul Rafay · Moiz · Areeba · Aqib</div>')
add('<div class="k">Problem</div><h2>Cameras record. Nobody watches.</h2>'+stats([("20M+","people in Karachi","#0F172A"),("~20 min","until an operator gets tired","#EF4444"),("Late","help arrives after the crime","#F59E0B")]))
add('<div class="k">Solution</div><h2>Make every camera smart</h2>'+stats([("Detect","finds danger in real time","#06B6D4"),("Decide","gives a risk score 0–100","#F59E0B"),("Dispatch","alerts 15 · 16 · 115 · 1122","#EF4444")]))
add('<div class="k">What it detects</div><h2>12 types of emergency</h2><p class="lead" style="font-size:30px;line-height:1.9;color:#0F172A">🔥 Fire &nbsp; 👊 Fight &nbsp; 🔫 Weapon &nbsp; 💰 Robbery &nbsp; 🚐 Kidnapping &nbsp; 👥 Crowd crush<br>🚗 Car accident &nbsp; 🏍️ Bike accident &nbsp; 🕴️ Loitering &nbsp; 🎒 Left bag &nbsp; 🚧 Blocked road &nbsp; 🔊 Gunshot / scream</p>')
add('<div class="k">How it works</div><h2>Camera → AI → Rules → Alert</h2>'+lst([("1. YOLOv8s","finds people, cars, bags"),("2. ByteTrack","gives each person an ID"),("3. Special models","pose · fire · weapon · violence"),("4. Event engine","12 rules, checked over time"),("5. Action","risk score · alert · sealed evidence")]))
add('<div class="k">Models</div><h2>3 models trained by our team</h2>'+lst([("Fire & Smoke","YOLOv8s · 80 epochs"),("Weapon","YOLOv8s · 60 epochs"),("Violence","YOLOv8s-cls · 50 epochs"),("Pre-trained","YOLOv8s · YOLOv8s-pose · YAMNet audio")])+'<p class="l" style="margin-top:26px">Trained on Google Colab T4 GPU using transfer learning.</p>')
add('<div class="k">Data</div><h2>~35,000 training images</h2>'+stats([("16,027","fire images (D-Fire)","#EF4444"),("7,116","weapon images","#8B5CF6"),("~12,000","violence images (RWF-2000+)","#F59E0B"),("4,304","extra weather images","#06B6D4")])+'<p class="l" style="margin-top:50px">All images scanned · 5 duplicates and 74 bad labels removed.</p>')
add('<div class="k">Results · Fire model</div><h2>2× better than our old method</h2>'+stats([("47.6%","precision<br><span style=font-size:15px>old: ~25%</span>","#06B6D4"),("25.5%","recall","#F59E0B"),("16.0%","mAP@50<br><span style=font-size:15px>old: ~8%</span>","#8B5CF6"),("7.6%","mAP@50-95","#64748B")])+'<p class="note">Measured on the D-Fire test set — a hard dataset with many tiny fires. Weapon & violence results: in progress.</p>')
add('<div class="k">Speed</div><h2>43% faster with our async design</h2>'+stats([("7 → 10","frames per second","#10B981"),("−48%","dropped frames","#06B6D4"),("4 GB","small GPU (Quadro T1000)","#0F172A")]))
add('<div class="k">Better results from real data</div><h2>3 settings tuned</h2>'+lst([("Crowd danger level","0.90 → 0.95"),("Time before alert","1.0 s → 1.5 s"),("Detection confidence","0.30 → 0.35")])+'<p class="l" style="margin-top:26px">Fewer duplicate alerts and fewer false fights in dark video.</p>')
add('<div class="k">Goals</div><h2>Goal vs. today</h2>'+lst([("12 event types",'<span class="ok">● Done</span>'),("Sealed evidence (SHA-256)",'<span class="ok">● Done</span>'),("No face recognition",'<span class="ok">● Done</span>'),("Speed 25–30 FPS",'<span class="wip">● In progress (10 FPS)</span>'),("Detection mAP@50 ≥ 70%",'<span class="no">● Not yet (16%)</span>'),("False alarms &lt; 5%",'<span class="wip">● Measuring</span>')]))
add('<div class="k">Next steps</div><h2>What we do next</h2>'+lst([("More training","bigger model, more epochs"),("Local data","real Karachi CCTV"),("Finish tests","weapon & violence reports"),("City pilot","real cameras, real helplines")]))
add('<div style="margin-top:170px"><h1 style="font-size:64px">Cameras are already there.<br><span style="color:#06B6D4">We give them a brain.</span></h1><p class="lead" style="margin-top:40px">Thank you — questions?</p></div>')
open('/tmp/claude-0/pdf/mini.html','w').write(f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>{CSS}</style></head><body>{"".join(S)}</body></html>')
