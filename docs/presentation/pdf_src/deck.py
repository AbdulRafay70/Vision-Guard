import sys; sys.path.insert(0,'/tmp/claude-0/pdf')
from common import FONTS, BASE
CSS = BASE + """
@page{size:1280px 720px;margin:0}
.s{width:1280px;height:720px;position:relative;overflow:hidden;page-break-after:always;background:#fff;padding:64px 80px}
.s.dark{background:radial-gradient(1200px 600px at 85% 10%,#0E3A4D 0%,var(--navy) 55%);color:#fff}
.s .kick{font-size:15px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--cyan)}
.s h1{font-size:64px;font-weight:900;line-height:1.05;letter-spacing:-.02em}
.s h2{font-size:44px;font-weight:800;letter-spacing:-.015em;margin:10px 0 28px;line-height:1.1}
.s p.lead{font-size:24px;color:var(--muted);line-height:1.45;max-width:900px}
.dark p.lead{color:#B6C2D6}
.foot{position:absolute;left:80px;right:80px;bottom:28px;display:flex;justify-content:space-between;font-size:13px;color:#94A3B8}
.badge{position:absolute;top:40px;right:80px;background:var(--navy);color:#fff;border-radius:999px;padding:8px 18px;font-size:14px;font-weight:700}
.badge b{color:var(--cyan)}
.grid{display:grid;gap:22px}.g2{grid-template-columns:1fr 1fr}.g3{grid-template-columns:repeat(3,1fr)}.g4{grid-template-columns:repeat(4,1fr)}
.card{border:1px solid var(--line);border-radius:18px;padding:24px 26px;background:#fff}
.card h3{font-size:22px;font-weight:800;margin-bottom:8px}.card p{font-size:17px;color:#475569;line-height:1.45}
.dark .card{background:rgba(255,255,255,.05);border-color:rgba(255,255,255,.12)}.dark .card p{color:#B6C2D6}
.ic{width:44px;height:44px;border-radius:12px;display:grid;place-items:center;font-size:24px;margin-bottom:14px}
.stat .n{font-size:58px;font-weight:900;letter-spacing:-.03em;line-height:1}.stat .l{font-size:16px;color:var(--muted);margin-top:8px;line-height:1.35}
.flow{display:flex;align-items:stretch;gap:10px}
.flow .st{flex:1;border-radius:14px;padding:22px 16px;min-height:150px;background:#F1F5F9;border-top:5px solid var(--cyan)}
.flow .st b{display:block;font-size:19px;margin-bottom:6px}.flow .st span{font-size:15px;color:#475569;line-height:1.35;display:block}
.arrow{align-self:center;color:#94A3B8;font-size:22px}
table{border-collapse:collapse;width:100%;font-size:17px}th{text-align:left;font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);padding:10px 14px;border-bottom:2px solid var(--line)}
td{padding:11px 14px;border-bottom:1px solid var(--line)}td.num{font-weight:800}
.pill{display:inline-block;padding:3px 12px;border-radius:999px;font-size:13px;font-weight:700}
.bar{height:16px;border-radius:8px;background:#E2E8F0;overflow:hidden}.bar i{display:block;height:100%;border-radius:8px}
ul.clean{list-style:none}ul.clean li{font-size:21px;line-height:1.45;padding:9px 0 9px 34px;position:relative}
ul.clean li:before{content:"";position:absolute;left:4px;top:19px;width:12px;height:12px;border-radius:3px;background:var(--cyan)}
.quote{font-size:40px;font-weight:800;line-height:1.2;letter-spacing:-.01em}
.hl{color:var(--cyan)}
.three{display:flex;gap:18px;margin-top:40px}.three div{flex:1;border-radius:18px;padding:26px;font-size:34px;font-weight:900}
"""
def foot(n, title): return f'<div class="foot"><span>VisionGuard ULTRA · {title}</span><span>{n:02d}</span></div>'

def build(team=False):
    title = "Team Presentation" if team else "Presented by Abdul Rafay"
    def B(who): return f'<div class="badge">🎤 <b>{who}</b></div>' if team else ''
    S=[]
    S.append(f'''<section class="s dark">
<div class="kick">Alibaba AI Hackathon 2026</div>
<div style="margin-top:120px"><div style="font-size:84px">🛡️</div><h1 style="font-size:88px;margin-top:10px">VisionGuard <span class="hl">ULTRA</span></h1>
<p class="lead" style="font-size:30px;margin-top:18px">Turning passive CCTV into an AI City Brain.<br><b style="color:#fff">Detect → Decide → Dispatch.</b></p></div>
<div style="position:absolute;bottom:60px;left:80px;font-size:19px;color:#B6C2D6">{"Abdul Rafay · Moiz · Areeba · Aqib" if team else "Abdul Rafay — Team Lead & AI Systems Architect<br><span style='font-size:16px;color:#7C8BA3'>with Moiz · Areeba · Aqib</span>"}</div></section>''')
    if team:
        S.append(f'''<section class="s">{B("All · Rafay leads")}<div class="kick">The team</div><h2>Four people, one system</h2>
<div class="grid g4">{"".join(f'<div class="card"><div class="ic" style="background:{c}22">{i}</div><h3>{n}</h3><p><b>{r}</b><br>{d}</p></div>' for i,c,n,r,d in [
("🧭","#06B6D4","Abdul Rafay","Team Lead","AI pipeline, event engine, voice, backend"),
("🧠","#8B5CF6","Moiz","ML Engineer","Fire, weapon & violence models"),
("📊","#10B981","Areeba","Data Scientist","Data cleaning, augmentation, evaluation"),
("🖥️","#F59E0B","Aqib","Frontend & UX","React command center")])}</div>{foot(2,title)}</section>''')
    S.append(f'''<section class="s">{B("Abdul Rafay")}<div class="kick">The problem</div><h2>Cameras record. Nobody watches.</h2>
<div class="grid g3" style="margin-top:30px">
<div class="card stat"><div class="n">20M+</div><div class="l">people in Karachi, with thousands of CCTV cameras</div></div>
<div class="card stat"><div class="n" style="color:var(--red)">~20 min</div><div class="l">before a screen operator's attention drops</div></div>
<div class="card stat"><div class="n" style="color:var(--amber)">After</div><div class="l">CCTV gives evidence after the crime — not help during it</div></div></div>
<ul class="clean" style="margin-top:30px"><li>One operator cannot watch 50 screens at once</li><li>Help is late: someone must notice, then call 15 / 16 / 1122</li><li>Many threat types: fights, weapons, fire, crowds, accidents, abandoned bags</li></ul>{foot(len(S)+1,title)}</section>''')
    S.append(f'''<section class="s dark">{B("Abdul Rafay")}<div class="kick">Our solution</div><h2>An AI City Brain on existing cameras</h2>
<p class="lead">VisionGuard watches every feed at the same time, finds emergencies in real time, scores the risk, saves tamper-proof evidence and routes the alert to the right department.</p>
<div class="three"><div style="background:#06B6D433">🔍 Detect</div><div style="background:#F59E0B33">⚖️ Decide</div><div style="background:#EF444433">🚨 Dispatch</div></div>{foot(len(S)+1,title)}</section>''')
    S.append(f'''<section class="s">{B("Abdul Rafay")}<div class="kick">Coverage</div><h2>12 event detectors</h2>
<div class="grid g4">{"".join(f'<div class="card" style="padding:18px 20px"><div style="font-size:28px">{i}</div><h3 style="font-size:19px;margin-top:6px">{n}</h3><p style="font-size:14px">{d}</p></div>' for i,n,d in [
("🔥","Fire & smoke","Growing flames, smoke plumes"),("👊","Fight","Pose + violence model"),("🔫","Weapon threat","Weapon near a person"),("💰","Robbery","Stop + fast rush"),
("🚐","Kidnapping","Approach + struggle"),("👥","Crowd crush","Density vs capacity"),("🚗","Car accident","Overlap + sudden stop"),("🏍️","Bike accident","Rider lean + stop"),
("🕴️","Loitering","Same spot 5+ min"),("🎒","Abandoned object","Bag alone 60 s"),("🚧","Vehicle obstruction","Stopped 10+ s"),("🔊","Audio emergency","Gunshot, scream, blast")])}</div>{foot(len(S)+1,title)}</section>''')
    S.append(f'''<section class="s">{B("Aqib · demo")}<div class="kick">Live demo</div><h2>What you are about to see</h2>
<div class="grid g2"><div>{"".join(f'<div style="display:flex;gap:16px;align-items:flex-start;margin-bottom:16px"><div style="min-width:40px;height:40px;border-radius:50%;background:var(--navy);color:#fff;display:grid;place-items:center;font-weight:800">{k}</div><div><b style="font-size:20px">{a}</b><div style="font-size:16px;color:#475569">{b}</div></div></div>' for k,a,b in [
(1,"Command center","All cameras analysed live"),(2,"Fire video","Fire & smoke → Fire Brigade 16"),(3,"Fight / weapon video","Pose skeletons + second check → Police 15"),(4,"Risk score","0–100, most dangerous first"),(5,"Evidence locker","Clip + SHA-256 fingerprint")])}</div>
<div class="card" style="background:var(--navy);color:#fff;border:none"><div class="kick">Risk levels</div>{"".join(f'<div style="display:flex;justify-content:space-between;align-items:center;padding:14px 0;border-bottom:1px solid #ffffff1a"><span class="pill" style="background:{c};color:#fff">{l}</span><span style="font-size:18px">{r}</span><span style="font-size:15px;color:#94A3B8">{a}</span></div>' for l,c,r,a in [("CRITICAL","#EF4444","85–100","Dispatch suggested"),("HIGH","#F59E0B","50–84","Team review"),("MEDIUM","#0891B2","25–49","Warning"),("LOW","#64748B","0–24","Ignored")])}</div></div>{foot(len(S)+1,title)}</section>''')
    S.append(f'''<section class="s">{B("Abdul Rafay")}<div class="kick">How it works</div><h2>From one frame to one alert</h2>
<div class="flow">{'<div class="arrow">›</div>'.join(f'<div class="st" style="border-color:{c}"><b>{a}</b><span>{b}</span></div>' for a,b,c in [
("Camera","Webcam, RTSP, video file","#64748B"),("YOLOv8s","People, vehicles, bags","#06B6D4"),("ByteTrack","Stable ID per object","#06B6D4"),("Specialists","Pose · Fire · Weapon · Violence","#8B5CF6"),("Audio","YAMNet sounds","#8B5CF6"),("Event engine","12 rules over time","#F59E0B"),("Action","Risk · route · evidence","#EF4444")])}</div>
<div class="grid g3" style="margin-top:34px">
<div class="card"><h3>⏱️ Time, not one frame</h3><p>Events must last 1.5 s (weapons 0.5 s). A grace period ignores one-frame flicker.</p></div>
<div class="card"><h3>✅ Two-stage check</h3><p>Fast pose signal first, then the violence classifier confirms on the person crop.</p></div>
<div class="card"><h3>🧵 Async pipeline</h3><p>Display and heavy models run on separate threads, so the video never freezes.</p></div></div>{foot(len(S)+1,title)}</section>''')
    S.append(f'''<section class="s">{B("Moiz")}<div class="kick">Models</div><h2>Transfer learning on our own data</h2>
<table><tr><th>Model</th><th>Type</th><th>Data</th><th>Input</th><th>Epochs</th></tr>
<tr><td><b>Fire / Smoke v2</b></td><td>YOLOv8s detection</td><td>D-Fire + Roboflow (~16k images)</td><td>640</td><td class="num">80</td></tr>
<tr><td><b>Weapon</b></td><td>YOLOv8s detection</td><td>CCTV weapon, knife, pistol (~7.1k)</td><td>640</td><td class="num">60</td></tr>
<tr><td><b>Violence</b></td><td>YOLOv8s-cls</td><td>RWF-2000 + violence sets (~12k)</td><td>224</td><td class="num">50</td></tr>
<tr><td><b>Pose · Detection · Audio</b></td><td>Pre-trained</td><td>YOLOv8s-pose · YOLOv8s (COCO) · YAMNet</td><td>—</td><td>—</td></tr></table>
<div class="grid g2" style="margin-top:28px"><div class="card"><h3>Why YOLOv8?</h3><p>Real-time on a 4 GB GPU. One framework for detection, pose and classification.</p></div>
<div class="card"><h3>Fire v1 → v2</h3><p>v1 used colour only (red clothes, sunsets = false alarms). v2 learns the shape and texture of fire and smoke.</p></div></div>{foot(len(S)+1,title)}</section>''')
    S.append(f'''<section class="s">{B("Areeba")}<div class="kick">Data quality</div><h2>Clean data, tested limits</h2>
<div class="grid g4">
<div class="card stat"><div class="n">16,027</div><div class="l">D-Fire images scanned · 0 broken</div></div>
<div class="card stat"><div class="n">7,116</div><div class="l">clean weapon images · 5 duplicates removed</div></div>
<div class="card stat"><div class="n">4,304</div><div class="l">weather images made (rain, fog, shadow)</div></div>
<div class="card stat"><div class="n">3</div><div class="l">thresholds tuned from real false-alarm evidence</div></div></div>
<table style="margin-top:30px"><tr><th>Setting</th><th>Before</th><th>After</th><th>Why</th></tr>
<tr><td>Crowd danger ratio</td><td>0.90</td><td class="num">0.95</td><td>Crowd alarm fired too often</td></tr>
<tr><td>Event persistence</td><td>1.0 s</td><td class="num">1.5 s</td><td>Duplicate alerts within 2 s</td></tr>
<tr><td>Detection confidence</td><td>0.30</td><td class="num">0.35</td><td>False fights in dark frames</td></tr></table>{foot(len(S)+1,title)}</section>''')
    def bar(l,v,old,c): return f'<div style="margin-bottom:22px"><div style="display:flex;justify-content:space-between;font-size:18px;margin-bottom:8px"><b>{l}</b><span><b>{v}%</b> <span style="color:#94A3B8">vs {old}% (v1)</span></span></div><div class="bar"><i style="width:{v*1.6}%;background:{c}"></i></div><div class="bar" style="height:8px;margin-top:5px"><i style="width:{old*1.6}%;background:#94A3B8"></i></div></div>'
    S.append(f'''<section class="s">{B("Areeba")}<div class="kick">Measured results</div><h2>Fire v2: 2× the old method</h2>
<div class="grid g2"><div>{bar("Precision",47.6,25,"#06B6D4")}{bar("mAP@50",16.0,8,"#8B5CF6")}{bar("mAP@50-95",7.6,3,"#8B5CF6")}{bar("Recall",25.5,35,"#F59E0B")}</div>
<div class="card" style="background:#F1F5F9;border:none"><h3>How to read this</h3><p style="font-size:16.5px">• D-Fire is hard: many fires are tiny, far or hidden, and every box counts.<br><br>• We trade some recall for precision — fewer false alarms in a city.<br><br>• Alerts are decided over time: a fire missed in one frame is caught in the next.<br><br>• Weapon & violence evaluation: <b>in progress</b>. Target: mAP@50 ≥ 70%, Top-1 ≥ 85%.</p></div></div>{foot(len(S)+1,title)}</section>''')
    S.append(f'''<section class="s">{B("Abdul Rafay")}<div class="kick">Performance</div><h2>Async design: 43% faster on a small GPU</h2>
<div class="grid g3">
<div class="card stat"><div class="n">7 → 10</div><div class="l">display FPS at 720p (+43%)</div></div>
<div class="card stat"><div class="n">866 → 450</div><div class="l">dropped frames (−48%)</div></div>
<div class="card stat"><div class="n">42.7 → 29.9 s</div><div class="l">to process 300 frames (−30%)</div></div></div>
<p class="lead" style="margin-top:34px;font-size:20px">Measured on an NVIDIA Quadro T1000 (4 GB). Next tuning: 480p input, every-2nd-frame AI, smart specialist scheduling, FP16 — target 22+ FPS.</p>{foot(len(S)+1,title)}</section>''')
    S.append(f'''<section class="s">{B("Aqib" if team else "Abdul Rafay")}<div class="kick">Operator experience</div><h2>Command center & evidence</h2>
<div class="grid g3">
<div class="card"><div class="ic" style="background:#06B6D422">🗺️</div><h3>Camera matrix</h3><p>1×1, 2×2 and grid layouts. Location tree: city → sector → camera.</p></div>
<div class="card"><div class="ic" style="background:#EF444422">🚨</div><h3>Live alerts</h3><p>Pushed instantly over WebSocket, sorted by risk, colour-coded.</p></div>
<div class="card"><div class="ic" style="background:#8B5CF622">🎙️</div><h3>Voice control</h3><p>"What is going on?" — Gemini turns speech into commands, with an offline fallback.</p></div>
<div class="card"><div class="ic" style="background:#10B98122">🔐</div><h3>Evidence locker</h3><p>5 s before + 3 s after each event, sealed with a SHA-256 fingerprint.</p></div>
<div class="card"><div class="ic" style="background:#F59E0B22">📍</div><h3>Heatmaps</h3><p>Incident history shows where trouble happens most.</p></div>
<div class="card"><div class="ic" style="background:#64748B22">👤</div><h3>Human in the loop</h3><p>AI suggests; the operator confirms or dismisses.</p></div></div>{foot(len(S)+1,title)}</section>''')
    S.append(f'''<section class="s">{B("Abdul Rafay")}<div class="kick">Routing</div><h2>The right department, automatically</h2>
<table><tr><th>Event</th><th>Department</th><th>Dial</th><th>Priority</th></tr>
{"".join(f'<tr><td>{e}</td><td>{d}</td><td class="num">{n}</td><td><span class="pill" style="background:{c}22;color:{c}">{p}</span></td></tr>' for e,d,n,p,c in [
("🔥 Fire","Fire Brigade","16","CRITICAL","#EF4444"),("🔫 Weapon · 💰 Robbery · 🚐 Kidnapping","Sindh Police / Rangers","15","CRITICAL","#EF4444"),
("👥 Crowd crush","Disaster Management","1122","CRITICAL","#EF4444"),("🚗 Car / 🏍️ bike accident","Edhi / Rescue","115","CRITICAL / HIGH","#F59E0B"),
("👊 Fight · 🎒 Abandoned object","Police / Bomb Squad","15","HIGH","#F59E0B"),("🚧 Vehicle obstruction","Traffic Police","1915","MEDIUM","#0891B2")])}</table>{foot(len(S)+1,title)}</section>''')
    S.append(f'''<section class="s">{B("Areeba" if team else "Abdul Rafay")}<div class="kick">Trust</div><h2>Behavioural, not biometric</h2>
<div class="grid g2"><div class="card"><h3>🙅 No face recognition</h3><p>We detect actions and objects — never who a person is. No face database.</p></div>
<div class="card"><h3>👤 Humans decide</h3><p>Risk scores suggest; operators confirm before dispatch.</p></div>
<div class="card"><h3>🔐 Tamper-proof</h3><p>Every evidence file carries a SHA-256 hash. Any edit is detectable.</p></div>
<div class="card"><h3>🔑 Access control</h3><p>Login-protected dashboard; the city sets data retention.</p></div></div>{foot(len(S)+1,title)}</section>''')
    S.append(f'''<section class="s">{B("Abdul Rafay")}<div class="kick">Honest roadmap</div><h2>What we will do next</h2>
<div class="grid g2"><div><h3 style="font-size:20px;color:var(--muted);margin-bottom:14px">KNOWN LIMITS</h3><ul class="clean">
<li style="font-size:18px">Fire metrics still low on hard D-Fire set</li><li style="font-size:18px">Weapon & violence reports in progress</li><li style="font-size:18px">Small far weapons, night video</li><li style="font-size:18px">Pixel rules depend on camera angle</li></ul></div>
<div><h3 style="font-size:20px;color:var(--muted);margin-bottom:14px">NEXT STEPS</h3><ul class="clean">
<li style="font-size:18px">More epochs, bigger model, Karachi data</li><li style="font-size:18px">Finish evaluation of all 3 models</li><li style="font-size:18px">Low-light augmentation, per-camera calibration</li><li style="font-size:18px">City pilot · hospitals, schools, industry</li></ul></div></div>{foot(len(S)+1,title)}</section>''')
    S.append(f'''<section class="s dark">{B("All" if team else "Abdul Rafay")}<div style="margin-top:150px"><div class="quote">Cameras are already there.<br><span class="hl">VisionGuard gives them a brain.</span></div>
<p class="lead" style="margin-top:30px;font-size:26px">Detect · Decide · Dispatch</p>
<p style="margin-top:70px;font-size:30px;font-weight:800">Thank you — questions?</p>
<p style="margin-top:10px;color:#94A3B8;font-size:17px">Abdul Rafay · Moiz · Areeba · Aqib &nbsp;·&nbsp; github.com/AbdulRafay70/Vision-Guard</p></div></section>''')
    return f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>{CSS}</style></head><body>{"".join(S)}</body></html>'
open('/tmp/claude-0/pdf/deck_solo.html','w').write(build(False))
open('/tmp/claude-0/pdf/deck_team.html','w').write(build(True))
