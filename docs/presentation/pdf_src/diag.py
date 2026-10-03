# Professional flat diagrams (no emoji)
F="Inter,sans-serif"; M="JetBrains Mono,monospace"
DEF='<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0L10,5L0,10z" fill="#64748B"/></marker></defs>'
PAL={"blue":("#EFF6FF","#3B82F6"),"cyan":("#ECFEFF","#0891B2"),"violet":("#F5F3FF","#7C3AED"),"amber":("#FFFBEB","#D97706"),"green":("#ECFDF5","#059669"),"rose":("#FFF1F2","#E11D48"),"slate":("#F8FAFC","#64748B")}
def node(x,y,w,h,lines,c="blue",bold=0,fs=13,pill=False):
    f,s=PAL[c]; r=h/2 if pill else 6
    o=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{f}" stroke="{s}" stroke-width="1.4"/>'
    n=len(lines); y0=y+h/2-(n-1)*fs*0.65
    for i,t in enumerate(lines):
        o+=f'<text x="{x+w/2}" y="{y0+i*fs*1.3+fs*0.35}" text-anchor="middle" font-family="{F}" font-size="{fs if i else fs+0.5}" font-weight="{700 if i==0 else 400}" fill="{"#1E293B" if i==0 else "#475569"}">{t}</text>'
    return o
def dia(cx,cy,w,h,lines,c="violet",fs=12.5):
    f,s=PAL[c]; p=f"{cx},{cy-h/2} {cx+w/2},{cy} {cx},{cy+h/2} {cx-w/2},{cy}"
    o=f'<polygon points="{p}" fill="{f}" stroke="{s}" stroke-width="1.4"/>'
    n=len(lines)
    for i,t in enumerate(lines): o+=f'<text x="{cx}" y="{cy-(n-1)*fs*0.65+i*fs*1.3+fs*0.35}" text-anchor="middle" font-family="{F}" font-size="{fs}" font-weight="{600 if i==0 else 400}" fill="#1E293B">{t}</text>'
    return o
def ln(pts,lbl=None,lx=None,ly=None,dash=False):
    d="M"+" L".join(f"{x},{y}" for x,y in pts)
    da='stroke-dasharray="5 4"' if dash else ''
    o=f'<path d="{d}" fill="none" stroke="#64748B" stroke-width="1.4" {da} marker-end="url(#ar)"/>'
    if lbl: o+=f'<rect x="{lx-len(lbl)*3.3-6}" y="{ly-11}" width="{len(lbl)*6.6+12}" height="17" rx="3" fill="#fff"/><text x="{lx}" y="{ly+2}" text-anchor="middle" font-family="{F}" font-size="11.5" font-weight="600" fill="#0F766E">{lbl}</text>'
    return o
def group(x,y,w,h,title,c="slate"):
    f,s=PAL[c]
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{f}" fill-opacity=".55" stroke="{s}" stroke-width="1" stroke-dasharray="0"/><text x="{x+10}" y="{y+17}" font-family="{F}" font-size="11.5" font-weight="700" fill="{s}" letter-spacing=".4">{title}</text>'

def decision_flow():
    """vertical logical flow with decision gates"""
    W=560; cx=W/2; g=DEF; y=10
    g+=node(cx-130,y,260,40,["Camera Frame In","RTSP / webcam / video file"],"cyan",pill=True,fs=12)
    g+=ln([(cx,50),(cx,70)])
    g+=node(cx-170,72,340,48,["Ingestion","threaded capture · auto-reconnect · newest frame only"],"blue",fs=12)
    g+=ln([(cx,120),(cx,140)])
    g+=node(cx-170,142,340,48,["Stage 1: YOLOv8s + ByteTrack","480 px · conf ≥ 0.35 · one track() call"],"blue",fs=12)
    g+=ln([(cx,190),(cx,206)])
    g+=dia(cx,252,190,92,["Persons or","objects found?"])
    g+=ln([(cx-95,252),(40,252),(40,560)],"No: idle frame",70,244)
    g+=ln([(cx,298),(cx,318)],"Yes",cx+16,310)
    g+=node(cx-170,320,340,48,["Stage 2: Specialist Worker (async)","Pose · Fire/Smoke · Weapon · Violence · YAMNet"],"violet",fs=12)
    g+=ln([(cx,368),(cx,388)])
    g+=node(cx-170,390,340,48,["Stage 3: Event Engine","12 rules · 5–8 s window · grace period"],"amber",fs=12)
    g+=ln([(cx,438),(cx,452)])
    g+=dia(cx,500,210,96,["Signal persists","≥ 1.5 s? (weapon 0.5 s)"])
    g+=ln([(cx,548),(cx,568)],"Yes",cx+16,560)
    g+=node(cx-170,570,340,48,["Risk Score 0–100","LOW / MEDIUM / HIGH / CRITICAL"],"amber",fs=12)
    g+=ln([(cx+105,500),(W-30,500),(W-30,240),(cx+170,166)],"No: keep watching",W-70,492,dash=True)
    g+=ln([(cx,618),(cx,632)])
    g+=dia(cx,676,190,88,["Risk ≥ 25?",""])
    g+=ln([(cx-95,676),(40,676),(40,560)],None,dash=True)
    g+=f'<text x="48" y="600" font-family="{F}" font-size="11.5" font-weight="600" fill="#0F766E">No: discard</text>'
    g+=ln([(cx,720),(cx,740)],"Yes",cx+16,732)
    g+=node(cx-170,742,340,48,["Action Layer","route 15/16/115/1122 · SHA-256 evidence · DB"],"green",fs=12)
    g+=ln([(cx,790),(cx,806)])
    g+=node(cx-150,808,300,44,["Operator Confirms / Dismisses","WebSocket alert on dashboard"],"cyan",pill=True,fs=12)
    return f'<svg viewBox="0 0 {W} 860" width="{W*0.66}" height="{860*0.66}">{g}</svg>'

PHASES=[("1","Input","Camera stream","RTSP · webcam · file","Why threaded capture","Each camera runs on its own thread with auto-reconnect and keeps only the newest frame, so delay never builds up.","#EA580C"),
("2","Detection","YOLOv8s + ByteTrack","480 px · one pass","Why YOLOv8s","One-stage, anchor-free and fast on a 4 GB GPU. Detection and tracking share one call — about 2x faster.","#2563EB"),
("3","Specialists","Pose · Fire · Weapon · Violence","async worker","Why a second thread","Heavy models run in the background on the newest frame, so the live video never freezes (+43% FPS).","#0891B2"),
("4","Event Engine","12 temporal rules","1.5 s persistence","Why time rules","One frame can be wrong. A danger must last 1.5 s (weapon 0.5 s); a grace period ignores flicker.","#059669"),
("5","Risk & Route","Score 0–100","85+ = critical","Why a risk score","Operators see the most dangerous event first; each event type goes to the right helpline.","#7C3AED"),
("6","Evidence & UI","SHA-256 · WebSocket","5 s + 3 s clip","Why sealed evidence","Any edit changes the fingerprint, so clips are trustworthy; alerts reach the dashboard instantly.","#DB2777")]
def phase_cards(items=PHASES):
    o='<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:14px;align-items:stretch">'
    for i,(n,t,tech,pill,wh,txt,c) in enumerate(items):
        o+=f'''<div style="border:1px solid #E2E8F0;border-radius:14px;background:#F8FAFC;padding:18px 14px;text-align:center;position:relative">
<div style="width:46px;height:46px;margin:0 auto 12px;border-radius:12px;border:1.5px solid {c}55;background:{c}14;color:{c};display:grid;place-items:center;font:700 20px Georgia,serif">{n}</div>
<div style="font-weight:800;font-size:16px;line-height:1.2">{t}</div>
<div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#64748B;margin:8px 0">{tech}</div>
<div style="display:inline-block;background:{c}18;color:{c};font-weight:700;font-size:12px;border-radius:99px;padding:3px 10px;margin-bottom:10px">{pill}</div>
<div style="font-size:13.5px;color:#334155;line-height:1.45"><b>{wh}:</b> {txt}</div></div>'''
    return o+'</div>'

def architecture():
    g=DEF; W=1100
    # stage 0
    g+=group(10,10,1080,70,"STAGE 0 · INGESTION","slate")
    for i,(a,b) in enumerate([("RTSP / CCTV","rtsp.py · reconnect"),("Webcam","webcam.py · threaded"),("Video file","video_file.py"),("Microphone","16 kHz · 1 s chunks")]):
        g+=node(30+i*265,32,240,40,[a,b],"slate",fs=11.5)
    # stage 1 thread 1
    g+=group(10,100,520,150,"STAGE 1 · THREAD 1 — FAST DISPLAY LOOP","blue")
    g+=node(25,128,150,58,["YOLOv8s (COCO)","80 classes · 480 px","conf ≥ 0.35"],"blue",fs=11)
    g+=node(195,128,150,58,["ByteTrack","stable IDs","30-frame buffer"],"blue",fs=11)
    g+=node(365,128,150,58,["Display renderer","boxes · skeletons","risk overlay"],"blue",fs=11)
    g+=ln([(175,157),(193,157)]);g+=ln([(345,157),(363,157)])
    g+=f'<text x="25" y="210" font-family="{F}" font-size="11" fill="#475569">AI every 2nd frame · FP16 · overlays valid 0.75 s</text>'
    g+=f'<text x="25" y="228" font-family="{F}" font-size="11" fill="#475569">baseline 7.0 FPS → async 10.0 FPS (+43%) · dropped 866 → 450</text>'
    # stage 2 thread 2
    g+=group(550,100,540,150,"STAGE 2 · THREAD 2 — SPECIALIST WORKER (newest frame)","violet")
    sp=[("Pose","yolov8s-pose","416 px · 17 kpts"),("Fire/Smoke v2","fire_smoke_best","640 px · every AI frame"),("Weapon","weapon_detection","416 px · every 3rd"),("Violence","yolov8s-cls","224 crop · ≥ 0.70")]
    for i,(a,b,c) in enumerate(sp): g+=node(562+i*131,128,122,58,[a,b,c],"violet",fs=10.5)
    g+=node(562,196,250,42,["YAMNet audio","gunshot · scream · blast · ≥ 0.4"],"violet",fs=10.5)
    g+=node(826,196,250,42,["Result freshness gate","event evidence valid ≤ 1.2 s"],"violet",fs=10.5)
    for x in [130,395,660,925]: g+=ln([(x,80),(x,98)])
    g+=ln([(270,186),(270,272)])
    g+=ln([(820,250),(820,272)])
    # stage 3
    g+=group(10,275,1080,135,"STAGE 3 · EVENT REASONING ENGINE (events/engine.py)","amber")
    ev=["Fire","Fight","Weapon","Robbery","Kidnap","Crowd","Car crash","Bike crash","Loitering","Abandoned","Obstruction","Audio"]
    for i,e in enumerate(ev): g+=node(22+i*88,300,80,30,[e],"amber",fs=10.5)
    g+=node(22,342,520,52,["Temporal logic per detector","signals → 5–8 s window → persistence 1.5 s → grace period → risk"],"amber",fs=11)
    g+=node(560,342,250,52,["Risk score 0–100","< 25 discarded"],"amber",fs=11)
    g+=node(828,342,250,52,["Audio-visual fusion","sounds from last 5 s raise risk"],"amber",fs=11)
    g+=ln([(542,368),(558,368)])
    # stage 4 decision
    g+=group(10,430,1080,120,"STAGE 4 · DECISION & ACTION","green")
    g+=node(22,458,200,78,["CRITICAL 85–100","dispatch suggested"],"rose",fs=11)
    g+=node(232,458,200,78,["HIGH 50–84","team review"],"amber",fs=11)
    g+=node(442,458,200,78,["MEDIUM 25–49","warning only"],"cyan",fs=11)
    g+=node(660,458,130,78,["Routing","15 · 16 · 115","1122 · 1915"],"green",fs=11)
    g+=node(800,458,130,78,["Evidence","5 s + 3 s clip","SHA-256"],"green",fs=11)
    g+=node(940,458,138,78,["Incident DB","SQLite","heatmaps"],"green",fs=11)
    g+=ln([(685,410),(685,428)])
    # stage 5
    g+=group(10,570,1080,80,"STAGE 5 · OPERATOR INTERFACE","cyan")
    for i,(a,b) in enumerate([("FastAPI server","REST · MJPEG feed"),("WebSocket /ws/alerts","instant push"),("React dashboard","matrix · incidents · registry"),("Voice + Gemini","JSON command · offline fallback"),("Human operator","confirm / dismiss")]):
        g+=node(22+i*214,596,204,44,[a,b],"cyan",fs=11)
    g+=ln([(550,550),(550,568)])
    return f'<svg viewBox="0 0 {W} 660" width="1100" height="560" preserveAspectRatio="xMidYMid meet">{g}</svg>'

def training_flow():
    g=DEF
    st=[("Collect","D-Fire · Weapon v9","RWF-2000 + violence","slate"),("Clean","scanner: header, 0-byte","dup hash · labels","blue"),("Augment","Albumentations","4,304 images","blue"),("Balance","oversample minority","class counts","blue"),
        ("Train","YOLOv8 transfer","Colab T4 · 50–80 ep","violet"),("Validate","best epoch","*_best.pt","violet"),("Test","P · R · mAP · Top-1","model_evaluation.py","amber"),("Tune","FP analysis","3 thresholds","rose")]
    for i,(a,b,c,col) in enumerate(st):
        x=10+i*136; g+=node(x,40,120,74,[a,b,c],col,fs=10.8)
        g+=f'<text x="{x+60}" y="28" text-anchor="middle" font-family="{F}" font-size="11" font-weight="700" fill="#94A3B8">STEP {i+1}</text>'
        if i<7: g+=ln([(x+120,77),(x+134,77)])
    g+=ln([(1031,114),(1031,150),(71,150),(71,116)],"feedback: errors in testing → better data and settings → retrain",551,150,dash=True)
    return f'<svg viewBox="0 0 1100 170" width="1100" height="170">{g}</svg>'
