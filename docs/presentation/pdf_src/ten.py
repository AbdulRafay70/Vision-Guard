import sys; sys.path.insert(0,'/tmp/claude-0/pdf')
from mini import CSS as MCSS, FONTS
from diag import *
import re
EMO=re.compile('[\U0001F000-\U0001FFFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200d]')
CSS = MCSS + """
.s{padding:70px 90px}
h2{font-size:44px;margin:10px 0 14px}
.tag{font-size:22px;color:#0891B2;font-weight:600;font-style:italic;margin-bottom:34px}
.ft{left:90px;right:90px}.ft .tm{background:#0B1220;color:#fff;padding:3px 12px;border-radius:99px;font-weight:700}
.pts{list-style:none}.pts li{font-size:22px;line-height:1.45;padding:10px 0 10px 40px;position:relative;border-bottom:1px solid #F1F5F9}
.pts li b{color:#0F172A}.pts li:before{content:attr(data-n);position:absolute;left:0;top:11px;width:26px;height:26px;border-radius:50%;background:#06B6D4;color:#fff;font-size:14px;font-weight:800;display:grid;place-items:center}
.cards{display:grid;gap:18px}.c2{grid-template-columns:1fr 1fr}.c3{grid-template-columns:repeat(3,1fr)}.c4{grid-template-columns:repeat(4,1fr)}
.cd{border:1px solid #E2E8F0;border-radius:16px;padding:20px 22px}.cd h3{font-size:21px;font-weight:800;margin-bottom:6px}.cd p{font-size:16.5px;color:#475569;line-height:1.45}
.cd .big{font-size:40px;font-weight:900;letter-spacing:-.02em;line-height:1;margin-bottom:8px}
table{border-collapse:collapse;width:100%;font-size:18px}th{text-align:left;font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:#64748B;padding:10px 12px;border-bottom:2px solid #E2E8F0}td{padding:11px 12px;border-bottom:1px solid #E2E8F0}
svg text{font-family:Inter,sans-serif}
.dark{background:radial-gradient(1100px 600px at 85% 10%,#0E3A4D 0%,#0B1220 55%);color:#fff}.dark .tag{color:#67E8F9}.dark .lead{color:#B6C2D6}
"""
S=[]
def add(time,b,dark=False):
    n=len(S)+1; S.append(f'<section class="s{" dark" if dark else ""}">{b}<div class="ft"><span>VisionGuard ULTRA · 10-minute presentation</span><span><span class="tm">⏱ {time}</span> &nbsp; {n:02d}</span></div></section>')
def head(k,h,t): return f'<div class="k">{k}</div><h2>{h}</h2><div class="tag">{t}</div>'
def pts(items): return '<ul class="pts">'+''.join(f'<li data-n="{i+1}">{x}</li>' for i,x in enumerate(items))+'</ul>'
def cd(t,p,big=None,c="#0F172A"):
    if big and not EMO.sub('',big).strip(): big=None
    return f'<div class="cd">{f"<div class=big style=color:{c}>{big}</div>" if big else ""}<h3>{t}</h3><p>{p}</p></div>'
def tb(h,rows): return '<table><tr>'+''.join(f'<th>{x}</th>' for x in h)+'</tr>'+''.join('<tr>'+''.join(f'<td>{c}</td>' for c in r)+'</tr>' for r in rows)+'</table>'

# ---------- SVG diagrams ----------
def box(x,y,w,h,title,sub,col,fill="#fff"):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{col}" stroke-width="2.5"/><rect x="{x}" y="{y}" width="{w}" height="8" rx="4" fill="{col}"/><text x="{x+w/2}" y="{y+h/2-2}" text-anchor="middle" font-size="18" font-weight="800" fill="#0F172A">{title}</text><text x="{x+w/2}" y="{y+h/2+22}" text-anchor="middle" font-size="13.5" fill="#475569">{sub}</text>'
def arr(x1,y1,x2,y2,c="#94A3B8",lbl=""):
    mx,my=(x1+x2)/2,(y1+y2)/2
    t=f'<text x="{mx}" y="{my-8}" text-anchor="middle" font-size="12" font-weight="700" fill="#0891B2">{lbl}</text>' if lbl else ''
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="2.5" marker-end="url(#a)"/>{t}'
DEFS='<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#94A3B8"/></marker></defs>'

def runtime_svg():
    g=DEFS
    # row 1
    g+=box(0,10,170,90,"📷 Camera","CCTV · RTSP · webcam","#64748B")
    g+=box(220,10,170,90,"🎯 YOLOv8s","finds people, cars, bags","#06B6D4")
    g+=box(440,10,170,90,"🔗 ByteTrack","ID for each object","#06B6D4")
    g+=box(660,10,200,90,"🖥️ Live display","boxes + skeletons","#10B981")
    g+=arr(170,55,218,55,lbl="frame");g+=arr(390,55,438,55,lbl="boxes");g+=arr(610,55,658,55,lbl="tracks")
    # thread label
    g+='<text x="0" y="128" font-size="13" font-weight="800" fill="#10B981" letter-spacing="1.5">THREAD 1 · FAST DISPLAY LOOP</text>'
    g+='<line x1="0" y1="142" x2="1100" y2="142" stroke="#E2E8F0" stroke-dasharray="6 6"/>'
    g+='<text x="0" y="168" font-size="13" font-weight="800" fill="#8B5CF6" letter-spacing="1.5">THREAD 2 · SPECIALIST WORKER (background, newest frame only)</text>'
    for i,(t,s) in enumerate([("🧍 Pose","17 body points"),("🔥 Fire/Smoke","fire_smoke_best.pt"),("🔫 Weapon","weapon_detection_best.pt"),("👊 Violence","person crop → yes/no")]):
        g+=box(i*190,185,170,82,t,s,"#8B5CF6")
    g+=arr(525,100,525,183,lbl="newest frame")
    g+=box(800,185,170,82,"🔊 YAMNet","gunshot · scream","#8B5CF6")
    # event engine
    g+=box(250,320,420,92,"⚖️ Event Engine","12 rules · 1.5 s persistence · grace period","#F59E0B","#FFFBEB")
    for x in [85,275,465,655]: g+=arr(x,267,min(max(x,300),620),318)
    g+=arr(885,267,640,318)
    g+=box(740,320,230,92,"📊 Risk 0–100","LOW · MED · HIGH · CRITICAL","#F59E0B")
    g+=arr(670,366,738,366)
    # outputs
    outs=[("🚨 Dispatch","15 · 16 · 115 · 1122"),("🔐 Evidence","5s+3s · SHA-256"),("🗄️ Incident DB","history · heatmaps"),("📡 Dashboard","WebSocket alerts"),("🤖 Gemini","short briefing")]
    for i,(t,s) in enumerate(outs):
        x=i*200; g+=box(x,460,180,80,t,s,"#EF4444")
        g+=arr(855,412,x+90,458)
    g+='<text x="1010" y="505" font-size="14" font-weight="800" fill="#0F172A">👤 Operator</text><text x="1010" y="525" font-size="12.5" fill="#64748B">confirms / dismisses</text>'
    return f'<svg viewBox="0 0 1110 545" width="930" height="457" style="display:block;margin:-12px auto 0">{g}</svg>'

def training_svg():
    g=DEFS
    steps=[("📥 Collect","D-Fire · weapon · RWF-2000","#64748B"),("🧹 Clean","broken · duplicates · labels","#06B6D4"),("🌧️ Augment","rain · fog · shadow · noise","#06B6D4"),("⚖️ Balance","oversample small classes","#06B6D4"),
           ("🧠 Train","YOLOv8 transfer learning","#8B5CF6"),("✅ Validate","keep *_best.pt","#8B5CF6"),("📏 Test","precision · recall · mAP","#F59E0B"),("🔧 Tune","thresholds from real alerts","#EF4444")]
    for i,(t,s,c) in enumerate(steps):
        r,ci=divmod(i,4); x=ci*275; y=20+r*190
        if r==1: x=3*275-ci*275
        g+=box(x,y,235,110,t,s,c)
        g+=f'<circle cx="{x+22}" cy="{y+30}" r="14" fill="{c}"/><text x="{x+22}" y="{y+35}" text-anchor="middle" font-size="13" font-weight="800" fill="#fff">{i+1}</text>'
    for i in range(3): g+=arr(i*275+235,75,(i+1)*275-2,75)
    g+=arr(3*275+117,130,3*275+117,208)
    for i in range(3): x=3*275-i*275; g+=arr(x,265,x-38,265)
    g+='<path d="M117,320 C117,380 117,380 117,380 L960,380 L960,135" fill="none" stroke="#EF4444" stroke-width="2" stroke-dasharray="7 6" marker-end="url(#a)"/>'
    g+='<text x="540" y="372" text-anchor="middle" font-size="14" font-weight="700" fill="#EF4444">feedback loop: errors found in testing → better data & settings → retrain</text>'
    return f'<svg viewBox="0 0 1060 395" width="1080" height="400">{g}</svg>'

# ---------- slides ----------
add("0:25",'<div class="k">Alibaba AI Hackathon 2026</div><div style="margin-top:130px"><h1 style="font-size:80px">VisionGuard <span style="color:#06B6D4">ULTRA</span></h1><div class="tag" style="font-size:28px;margin-top:20px">“Every camera becomes a guard that never gets tired.”</div><p class="lead">AI that finds emergencies in CCTV video and sends help — automatically.</p></div><div class="note" style="color:#B6C2D6;font-size:18px">Abdul Rafay · Moiz · Areeba · Aqib</div>',True)
add("0:30",head("1 · Problem","Cameras record. Nobody watches.","“The camera sees the crime — but nobody acts.”")+'<div class="cards c3">'+cd("Too many screens","One operator cannot watch 50 cameras at the same time.","20M+","#0F172A")+cd("Human fatigue","Attention drops after about 20 minutes of watching screens.","~20 min","#EF4444")+cd("Late help","CCTV gives proof after the crime — not help during it.","After","#F59E0B")+'</div>')
add("0:25",head("2 · Goal","What we want to achieve","“Find danger fast, decide smart, send the right help.”")+pts(["<b>Watch every camera</b> at the same time — no tired humans","<b>Find 12 types</b> of emergency in real time","<b>Few false alarms</b> — target under 3–5 wrong alerts in 100","<b>Send to the right department</b> with sealed proof","<b>Protect privacy</b> — no face recognition"]))
add("0:25",head("3 · Solution","VisionGuard in one line","“Detect → Decide → Dispatch.”")+'<div class="cards c3">'+cd("Detect","AI models look at every frame and every sound.","🔍")+cd("Decide","Rules check the danger over time and give a risk score 0–100.","⚖️")+cd("Dispatch","Alert goes to Police 15, Fire 16, Edhi 115 or Rescue 1122 with video proof.","🚨")+'</div><p class="lead" style="margin-top:30px;font-size:21px">Works on cameras the city already has — no new cameras needed.</p>')
add("0:30",head("4 · Methodology","How we built it — 6 steps","“Start simple, measure, improve.”")+'<div class="cards c3">'+''.join(cd(f"{i}. {t}",d) for i,t,d in [(1,"Study the problem","Karachi threats, operator fatigue, helplines, privacy."),(2,"Build a baseline","Ready YOLOv8 + tracking + simple colour fire rule."),(3,"Prepare data","Collect, clean, augment and balance datasets."),(4,"Train our models","Fine-tune YOLOv8 for fire, weapon and violence."),(5,"Add rules & actions","12 event rules, risk score, routing, evidence."),(6,"Test & improve","Measure accuracy and speed, fix, repeat.")])+'</div>')
add("0:40",head("5 · Pipeline overview","Six phases from camera to action","“Each phase has one job — and a clear reason.”")+phase_cards())
add("0:40",'<div style="display:grid;grid-template-columns:380px 1fr;gap:50px;align-items:start"><div style="margin-top:-30px">'+decision_flow()+'</div><div>'+head("6 · Logical flow","Decision gates","“The system asks three questions before it raises an alarm.”")+pts(["<b>Gate 1 — Anything there?</b> If YOLO finds no people or objects, the frame is skipped.","<b>Gate 2 — Does it last?</b> The danger must continue 1.5 s (weapon 0.5 s). Otherwise we keep watching.","<b>Gate 3 — Is it serious?</b> Risk below 25 is discarded; 85+ is critical.","<b>Human gate:</b> the operator confirms or dismisses every dispatch."])+'</div></div>')
add("0:40",head("7 · System architecture","Complete end-to-end pipeline","“Two lanes: one keeps video smooth, one does the heavy thinking.”").replace('<h2>','<h2 style="font-size:34px;margin:4px 0 4px">').replace('class="tag"','class="tag" style="font-size:18px;margin-bottom:10px"')+'<div style="margin-top:-14px;text-align:center">'+architecture().replace('width="1100" height="560"','width="930" height="495"')+'</div>')
add("0:30",head("8 · Event engine","Rules that think over time","“One frame can lie — a few seconds tell the truth.”")+'<div class="cards c2"><div>'+pts(["Collect <b>signals</b> from every frame","Keep a <b>time window</b> of the last 5–8 seconds","Event must last <b>1.5 s</b> (weapon: <b>0.5 s</b>)","<b>Grace period</b>: one missed frame does not reset","Give a <b>risk score</b> 0–100"])+'</div><div>'+tb(["Score","Level","Action"],[["85–100",'<b style="color:#EF4444">CRITICAL</b>',"Send help"],["50–84",'<b style="color:#F59E0B">HIGH</b>',"Team review"],["25–49",'<b style="color:#0891B2">MEDIUM</b>',"Warning"],["0–24","LOW","Ignore"]])+'<p style="font-size:16px;color:#64748B;margin-top:14px">Example — Fight = 2+ people close + fast wrists + repeats 1.5 s + violence model ≥ 70%.</p></div></div>')
add("0:30",head("9 · Models","The AI brains inside","“Ready-made eyes, plus 3 specialists we trained ourselves.”")+tb(["Model","Job","Type","Made by"],[["YOLOv8s","Find people, cars, bags (80 objects)","Detection","Pre-trained (COCO)"],["YOLOv8s-pose","17 body points per person","Pose","Pre-trained"],["<b>Fire & Smoke v2</b>","Find fire and smoke","Detection","<b>Trained by us</b>"],["<b>Weapon</b>","Find knife, pistol, rifle","Detection","<b>Trained by us</b>"],["<b>Violence</b>","Is this person fighting? yes / no","Classification","<b>Trained by us</b>"],["YAMNet","Gunshot, scream, explosion","Audio","Pre-trained"],["ByteTrack","Keep the same ID for each person","Tracking","Algorithm"]])+'<p style="font-size:17px;color:#64748B;margin-top:14px">Why YOLOv8s? Fast on a small 4 GB GPU, one tool for boxes, body points and yes/no.</p>')
add("0:25",head("10 · Datasets","What our models learned from","“Good data makes a good model.”")+'<div class="cards c4">'+cd("Fire & Smoke","D-Fire + Roboflow fire/smoke","16,027","#EF4444")+cd("Weapon","CCTV weapon, knife, pistol sets","7,116","#8B5CF6")+cd("Violence","RWF-2000 + Real Life Violence + CCTV","~12,000","#F59E0B")+cd("Weather extra","made by our augmentation","4,304","#06B6D4")+'</div><div class="cards c3" style="margin-top:18px">'+cd("Total for our models","~35,100 real images + 4,304 augmented ≈ 39,400 images")+cd("Boxes checked","32,836 labels (5,187 fire/smoke + 27,649 weapon)")+cd("Pre-trained on","COCO 118,000 images · AudioSet sound clips")+'</div>')
add("0:40",head("11 · Training pipeline","From raw data to a trained model","“Clean it, grow it, balance it — then teach it.”")+training_flow()+'<div class="cards c4" style="margin-top:26px">'+cd("Data in","~35,100 real images from 3 dataset groups")+cd("Prepared","5 duplicates + 74 bad labels removed, 4,304 augmented")+cd("Trained","3 models, 50–80 epochs, transfer learning")+cd("Tuned","3 thresholds changed from real false alarms")+'</div>')
add("0:30",head("12 · Data preparation","Clean → Augment → Balance","“Real CCTV is messy — so we trained on messy data.”")+'<div class="cards c3">'+cd("🧹 Clean","Checked 23,000+ images. Removed 5 copied images and 74 broken label lines. 0 broken images in D-Fire.","1")+cd("🌧️ Augment","Added rain, fog, shadow, light change, rotation and camera noise → 4,304 new images.","2")+cd("⚖️ Balance","Weapon classes were uneven (11,545 vs 7,532 boxes). Small classes shown more often so the model is not biased.","3")+'</div>')
add("0:25",head("13 · Training","How we taught the models","“Don't start from zero — teach a model that already knows how to see.”")+'<div class="cards c2"><div>'+tb(["Model","Input","Epochs"],[["Fire & Smoke","640 × 640","<b>80</b>"],["Weapon","640 × 640","<b>60</b>"],["Violence","224 × 224","<b>50</b>"]])+'<p style="font-size:16px;color:#64748B;margin-top:12px">Google Colab · free T4 GPU · about 3–6 hours each.</p></div><div>'+pts(["<b>Transfer learning:</b> start from YOLOv8 that already knows shapes","<b>Epoch</b> = model sees all images once","Fire gets most epochs — <b>no fixed shape</b>, hardest","Too many epochs = <b>memorising</b>, so we keep the best version"])+'</div></div>')
add("0:30",head("14 · Testing","How we measure accuracy","“Precision = how often an alarm is right. Recall = how many dangers we catch.”")+'<div class="cards c2"><div>'+tb(["Word","Simple meaning"],[["Precision","When it says “fire”, how often it is right"],["Recall","Of all real fires, how many it found"],["mAP@50","Overall box quality (box overlaps ≥ 50%)"],["mAP@50-95","Same, but much stricter"],["Top-1","Classifier's first answer is correct"]])+'</div><div>'+cd("Our pass marks","Detection mAP@50 ≥ 70% · Classification Top-1 ≥ 85% · False alarms < 5% on 20 test videos.","🎯")+'<div style="height:14px"></div>'+cd("Our test tools","model_evaluation.py · false_positive_analyzer.py · speed benchmarks")+'</div></div>')
add("0:30",head("15 · Results","Fire & Smoke model — measured","“Twice as good as our old method — and we know how to make it better.”")+'<div class="cards c4">'+cd("Precision","old colour method: ~25%","47.6%","#06B6D4")+cd("Recall","finds 1 in 4 boxes per frame","25.5%","#F59E0B")+cd("mAP@50","old: ~8% → 2× better","16.0%","#8B5CF6")+cd("mAP@50-95","old: ~3%","7.6%","#64748B")+'</div><div class="cards c2" style="margin-top:18px">'+cd("Why numbers look low","D-Fire is hard: tiny, far, hidden fires and soft smoke. But alerts use time — a fire missed in one frame is caught in the next.")+cd("Fire vs smoke","Fire precision 56.1% · Smoke 39.1%. Weapon & violence tests: in progress.")+'</div>')
add("0:25",head("16 · Improvements","What we made better","“Measure → find the problem → fix → measure again.”")+tb(["What","Before","After","Gain"],[["Fire model","Colour rule","Trained AI","2× mAP, +90% precision"],["Pipeline","One slow thread","Two lanes (async)","+43% FPS (7 → 10)"],["Dropped frames","866","450","−48%"],["Crowd alarm","0.90","0.95","fewer false crowds"],["Time before alert","1.0 s","1.5 s","no duplicate alerts"],["Confidence","0.30","0.35","fewer dark-video errors"]]))
add("0:20",head("17 · Trust","Safe, fair and private","“We watch actions — not faces.”")+'<div class="cards c4">'+cd("No face ID","No face recognition, no face database.","🙅")+cd("Human decides","AI suggests, operator confirms.","👤")+cd("Sealed proof","5 s before + 3 s after, SHA-256 fingerprint.","🔐")+cd("Login only","Only allowed users see data.","🔑")+'</div>')
add("0:20",head("18 · Goal vs today","Honest status","“We know where we are — and where we are going.”")+tb(["Goal","Today",""],[["12 emergency types","12 rules working",'<b class="ok">● Done</b>'],["Sealed evidence + privacy","Working",'<b class="ok">● Done</b>'],["Speed 25–30 FPS","10 FPS on a 4 GB GPU",'<b class="wip">● In progress</b>'],["Detection mAP@50 ≥ 70%","Fire 16%",'<b class="no">● Not yet</b>'],["Violence / weapon tests","Running",'<b class="wip">● In progress</b>'],["False alarms < 5%","Measuring",'<b class="wip">● In progress</b>']]))
add("0:25",head("19 · Next steps","Where we go from here","“From a strong prototype to a real city system.”")+pts(["<b>Better models:</b> more epochs, bigger YOLO, local Karachi data","<b>Finish testing:</b> weapon & violence reports, 20-video false-alarm test","<b>Night vision:</b> low-light training and IR cameras","<b>City pilot:</b> real cameras, real helplines","<b>New sectors:</b> hospitals (fall detection), schools, factories"]))
add("0:15",'<div style="margin-top:150px"><h1 style="font-size:62px">Cameras are already there.<br><span style="color:#06B6D4">VisionGuard gives them a brain.</span></h1><div class="tag" style="margin-top:28px;font-size:26px">Detect · Decide · Dispatch</div><p class="lead">Thank you — questions?</p></div>',True)
html=EMO.sub('',f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>{CSS}</style></head><body>{"".join(S)}</body></html>')
open('/tmp/claude-0/pdf/ten.html','w').write(html)

for nm,body,ttl in [("pipeline_overview",phase_cards(),"High-level pipeline overview and engineering rationale"),("pipeline_decision_flow",decision_flow(),"Logical flow with decision gates"),("pipeline_architecture",architecture(),"Complete end-to-end architecture"),("pipeline_training",training_flow(),"Training pipeline")]:
    open(f'/tmp/claude-0/pdf/{nm}.html','w').write(f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>body{{margin:0;padding:36px;background:#fff;font-family:Inter;width:1180px}}h1{{font-size:20px;color:#64748B;font-weight:600;text-align:center;margin:0 0 22px}}</style></head><body><h1>VisionGuard ULTRA — {ttl}</h1>{body}</body></html>')
