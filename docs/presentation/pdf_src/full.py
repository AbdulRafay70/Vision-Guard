import sys; sys.path.insert(0,'/tmp/claude-0/pdf')
from deck import CSS, FONTS
CSS += """
.s h2{font-size:40px;margin:8px 0 22px}
table.t{font-size:15px}table.t td,table.t th{padding:8px 11px}
.tag{display:inline-block;font-size:11.5px;font-weight:800;padding:2px 9px;border-radius:99px;letter-spacing:.03em}
.v{background:#10B98122;color:#047857}.r{background:#F59E0B22;color:#B45309}.o{background:#06B6D422;color:#0E7490}.p{background:#EF444422;color:#B91C1C}
.sec{position:absolute;top:44px;right:80px;font-size:13px;font-weight:700;color:#94A3B8;letter-spacing:.1em;text-transform:uppercase}
.mini{font-size:13px;color:#64748B;margin-top:14px}
.hb{display:flex;align-items:center;gap:12px;margin:9px 0;font-size:15px}.hb .lab{width:150px}.hb .tr{flex:1;height:22px;background:#EEF2F7;border-radius:6px;overflow:hidden}.hb .tr i{display:block;height:100%}.hb .val{width:120px;text-align:right;font-weight:800}
.tl{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.tl .ph{border-radius:14px;padding:18px;background:#F1F5F9;position:relative}.tl .ph .k{font-size:12px;font-weight:800;color:#0891B2;letter-spacing:.1em}.tl .ph b{display:block;font-size:18px;margin:4px 0 6px}.tl .ph span{font-size:14px;color:#475569;line-height:1.4;display:block}
"""
S=[]; SECT=[""]
def add(body, dark=False, sec=None):
    if sec: SECT[0]=sec
    n=len(S)+1
    S.append(f'<section class="s{" dark" if dark else ""}"><div class="sec">{SECT[0]}</div>{body}<div class="foot"><span>VisionGuard ULTRA · Full Project Presentation</span><span>{n:02d}</span></div></section>')
def card(t,p,i='',c='#06B6D4'): return f'<div class="card">{f"<div class=ic style=background:{c}22>{i}</div>" if i else ""}<h3>{t}</h3><p>{p}</p></div>'
def stat(n,l,c='var(--ink)'): return f'<div class="card stat"><div class="n" style="color:{c};font-size:46px">{n}</div><div class="l">{l}</div></div>'
def tbl(head,rows,cls="t"): return f'<table class="{cls}"><tr>{"".join(f"<th>{h}</th>" for h in head)}</tr>{"".join("<tr>"+"".join(f"<td>{c}</td>" for c in r)+"</tr>" for r in rows)}</table>'
def hb(l,v,mx,c,txt): return f'<div class="hb"><span class="lab">{l}</span><span class="tr"><i style="width:{v/mx*100:.1f}%;background:{c}"></i></span><span class="val">{txt}</span></div>'
V='<span class="tag v">MEASURED</span>'; R='<span class="tag r">SPEC CLAIM · TO VERIFY</span>'; O='<span class="tag o">OFFICIAL / PRE-TRAINED</span>'; P='<span class="tag p">PENDING</span>'

# 1 title
add('''<div class="kick">Alibaba AI Hackathon 2026 · Full Project Presentation</div><div style="margin-top:110px"><div style="font-size:80px">🛡️</div>
<h1 style="font-size:84px;margin-top:8px">VisionGuard <span class="hl">ULTRA</span></h1>
<p class="lead" style="font-size:28px;margin-top:16px">Autonomous AI City Brain & multi-modal threat detection for Karachi.<br><b style="color:#fff">Detect → Decide → Dispatch</b></p></div>
<div style="position:absolute;bottom:60px;left:80px;font-size:18px;color:#B6C2D6">Abdul Rafay · Moiz · Areeba · Aqib</div>''',True,"Introduction")
# 2 agenda
ag=["Problem & goals","Solution & architecture","Methodology & pipeline","Event rules & risk","Models","Datasets & counts","Data preparation","Training","Testing & evaluation","Results: accuracy, precision, recall","Improvements & benchmarks","Product, privacy, roadmap"]
add('<div class="kick">Agenda</div><h2>What we will cover</h2><div class="grid g3">'+''.join(f'<div class="card" style="padding:16px 20px;display:flex;gap:14px;align-items:center"><b style="font-size:26px;color:var(--cyan)">{i+1:02d}</b><span style="font-size:18px;font-weight:600">{a}</span></div>' for i,a in enumerate(ag))+'</div>')
# 3 problem
add('<div class="kick">The problem</div><h2>Cameras record. Nobody watches.</h2><div class="grid g4">'+stat("20M+","people in Karachi, thousands of CCTV cameras")+stat("~20 min","before a screen operator's attention collapses","var(--red)")+stat("1 : 50","one operator vs. dozens of screens","var(--amber)")+stat("After","CCTV is evidence after the crime, not help during it","var(--violet)")+'</div><div class="grid g3" style="margin-top:26px">'+card("Late response","Someone must notice, then call 15 / 16 / 1122 — minutes are lost.","⏱️","#EF4444")+card("Many threat types","Fights, weapons, fire, crowd crush, accidents, abandoned bags, kidnapping.","⚠️","#F59E0B")+card("Existing tools","Single-purpose, cloud-heavy, expensive, or face-recognition based.","🧩","#8B5CF6")+'</div>',sec="Problem & goals")
# 4 goals
add('<div class="kick">Goals</div><h2>What we set out to achieve</h2>'+tbl(["Goal","Target","Source"],[
["Real-time speed on a small edge GPU","25–30 FPS (22+ on Quadro T1000)","Project brief / config.py"],
["Event types covered","12 detectors","Event engine"],
["Detection model quality","mAP@50 ≥ 70%","Accuracy sign-off criteria"],
["Classification model quality","Top-1 ≥ 85%","Accuracy sign-off criteria"],
["False alarm rate","< 3% (brief) · < 5% on 20-video test suite (sign-off)","Brief / sign-off"],
["Alert speed","Weapon: 0.5 s · other events: 1.5 s persistence","config.py"],
["Evidence","Tamper-proof SHA-256 clip for every incident","evidence.py"],
["Privacy","No face recognition — behaviour only","Design principle"]]))
# 5 solution
add('<div class="kick">Our solution</div><h2>An AI City Brain on existing cameras</h2><p class="lead">Software that turns any CCTV / RTSP / webcam feed into an active guardian — no new cameras needed.</p><div class="grid g4" style="margin-top:34px">'+card("Detect","YOLOv8 + pose + specialist models + audio find what is happening.","🔍")+card("Decide","12 temporal rules and a 0–100 risk score decide how serious it is.","⚖️","#F59E0B")+card("Dispatch","Route to Police 15, Fire 16, Edhi 115, Rescue 1122, Traffic 1915.","🚨","#EF4444")+card("Prove","5 s before + 3 s after clip, SHA-256 sealed, stored in incident DB.","🔐","#10B981")+'</div>',True,"Solution & architecture")
# 6 architecture
add('<div class="kick">System architecture</div><h2>Four layers</h2><div class="grid g4">'+''.join(f'<div class="card" style="border-top:5px solid {c}"><div class="kick" style="color:{c}">Layer {i}</div><h3>{t}</h3><p style="font-size:15px">{d}</p></div>' for i,t,d,c in [
(1,"Ingestion","Webcam, RTSP CCTV, video files, microphone, citizen SOS. Threaded capture, auto-reconnect, newest-frame only.","#64748B"),
(2,"AI perception","YOLOv8s + ByteTrack (one call). Async specialist worker: Pose, Fire/Smoke, Weapon, Violence, Normal-scene. YAMNet audio.","#06B6D4"),
(3,"Reasoning","Event engine: 12 detectors, sliding time windows, persistence, grace period, risk 0–100, audio fusion.","#F59E0B"),
(4,"Action","Department routing, SHA-256 evidence, SQLite incidents + heatmaps, Gemini briefing, FastAPI + WebSocket, React dashboard.","#EF4444")])+'</div><p class="mini">Code: prototype/camera · prototype/ai · prototype/events · prototype/output · prototype/web · prototype/voice · frontend/src</p>')
# 7 methodology
add('<div class="kick">Methodology</div><h2>How we built it — step by step</h2><div class="tl">'+''.join(f'<div class="ph"><div class="k">PHASE {i}</div><b>{t}</b><span>{d}</span></div>' for i,t,d in [
(1,"Research & problem study","Karachi threats, operator fatigue, local helplines, privacy constraints."),
(2,"Baseline prototype","Pre-trained YOLOv8s + ByteTrack + pose; colour-based fire (v1); synchronous loop."),
(3,"Data collection","D-Fire, weapon CCTV sets, RWF-2000 & violence sets; COCO / AudioSet pre-trained."),
(4,"Data preparation","Corrupt / duplicate scan, label fixing, Albumentations weather augmentation, class balancing."),
(5,"Transfer-learning training","Fine-tune YOLOv8s / YOLOv8s-cls on Colab T4 GPU (50–80 epochs)."),
(6,"Rule engine","12 temporal detectors, risk scoring, routing, evidence chain."),
(7,"Evaluation & tuning","mAP / precision / recall, false-positive analysis → threshold calibration."),
(8,"Optimisation & UI","Async decoupled pipeline, FP16, frame skipping; React command center, voice.")])+'</div>',sec="Methodology & pipeline")
# 8 pipeline flow
add('<div class="kick">Pipeline</div><h2>From one frame to one alert</h2><div class="flow">'+'<div class="arrow">›</div>'.join(f'<div class="st" style="border-color:{c};min-height:170px"><b>{a}</b><span>{b}</span></div>' for a,b,c in [
("1 · Camera","Thread per camera, auto-reconnect","#64748B"),("2 · YOLOv8s","80 COCO classes, conf ≥ 0.35, 480 px","#06B6D4"),("3 · ByteTrack","Stable IDs, 30-frame memory","#06B6D4"),("4 · Specialists","Pose 416 · Fire 640 · Weapon 416 · Violence 224","#8B5CF6"),("5 · Audio","YAMNet 16 kHz, 1 s chunks, conf ≥ 0.4","#8B5CF6"),("6 · Events","12 rules, 1.5 s persistence","#F59E0B"),("7 · Action","Risk, route, evidence, UI","#EF4444")])+'</div><div class="grid g3" style="margin-top:26px">'+card("Smart scheduling","AI every 2nd frame · fire every AI frame · weapon every 3rd · pose only when people present (max 10).")+card("Result freshness","Overlays valid 0.75 s, event evidence valid 1.2 s — stale results never trigger alerts.")+card("One-pass tracking","Detection + tracking in a single model.track() call → 2× FPS vs separate calls.")+'</div>')
# 9 event rules
add('<div class="kick">Event engine</div><h2>12 detectors and their rules</h2>'+tbl(["Event","Rule (key thresholds from config.py)"],[
["🔥 Fire","Fire/smoke conf ≥ 0.35 · area 0.2–65% of frame · growth ×1.3 · risk gate 30"],
["👊 Fight","≥ 2 people within body-size distance · wrist speed > 16 px/frame · repeats 1.5 s · violence model ≥ 0.70"],
["🔫 Weapon threat","Weapon within 250 px of a person for 0.5 s"],
["💰 Robbery","Vehicle stopped ≥ 3 s · ≥ 2 suspects rushing > 30 px/frame"],
["🚐 Kidnapping","Approach > 15 px/frame · struggle variance > 20 · forced movement > 10"],
["👥 Crowd crush","Zone capacity 50 · warning 70% · danger 95%"],
["🚗 Car accident","≥ 2 vehicles · overlap IoU ≥ 0.15 · velocity drop > 15 px/frame"],
["🏍️ Bike accident","Rider angle > 45° · velocity drop > 10"],
["🕴️ Loitering","Movement < 50 px for 300 s"],
["🎒 Abandoned object","Object alone 60 s · owner > 200 px away"],
["🚧 Vehicle obstruction","Speed < 2 px/frame for 10 s"],
["🔊 Audio emergency","YAMNet gunshot / explosion / scream / crash / glass / siren ≥ 0.4"]]),sec="Event rules & risk")
# 10 risk
add('<div class="kick">Risk & routing</div><h2>Score, then send to the right place</h2><div class="grid g2"><div>'+tbl(["Score","Level","Action"],[
['<b>85–100</b>','<span class="pill" style="background:#EF4444;color:#fff">CRITICAL</span>',"Auto-dispatch suggested"],['<b>50–84</b>','<span class="pill" style="background:#F59E0B;color:#fff">HIGH</span>',"Team review"],['<b>25–49</b>','<span class="pill" style="background:#0891B2;color:#fff">MEDIUM</span>',"Warning"],['<b>0–24</b>','<span class="pill" style="background:#64748B;color:#fff">LOW</span>',"Ignored"]])+'<p class="mini">Every detector: signals → sliding window (5–8 s) → persistence → grace period for YOLO flicker → risk.</p></div><div>'+tbl(["Event","Department","Dial"],[
["Fire","Fire Brigade","<b>16</b>"],["Fight · robbery · weapon · kidnapping · audio","Sindh Police / Rangers","<b>15</b>"],["Car / bike accident","Edhi / Rescue","<b>115</b>"],["Crowd crush","Disaster Management","<b>1122</b>"],["Vehicle obstruction","Traffic Police","<b>1915</b>"],["Abandoned object · loitering","Police / Bomb Squad","<b>15</b>"]])+'</div></div>')
# 11 models overview
add('<div class="kick">Models</div><h2>Every model in the system</h2>'+tbl(["Model","File","Task","Base","Source"],[
["Primary detector","yolov8s.pt","Detection, 80 classes","—",O],
["Pose estimator","yolov8s-pose.pt","17 keypoints","—",O],
["Fire & Smoke v2","fire_smoke_best.pt","Detection: fire, smoke","YOLOv8s","Trained by Moiz"],
["Weapon detector","weapon_detection_best.pt","Detection: 3 weapon classes","YOLOv8s","Trained by Moiz"],
["Violence classifier","violence_classifier_best.pt","Classify crop: violent / non-violent","YOLOv8s-cls","Trained by Moiz"],
["Normal-scene verifier","normal_scene_verifier_best.pt","Suppress false alarms","YOLOv8s","Spec item "+R],
["Audio classifier","YAMNet","521 sound classes","—",O],
["Tracker","ByteTrack","Multi-object tracking","Algorithm",O]]),sec="Models")
# 12 why yolo
add('<div class="kick">Model choice</div><h2>Why YOLOv8s?</h2><div class="grid g3">'+card("Faster R-CNN","Two-stage → ~70 ms+ per frame. Too slow for many live streams.","🐢","#EF4444")+card("RT-DETR / Transformers","Accurate but heavy compute and VRAM — hard on a 4 GB edge GPU.","🏋️","#F59E0B")+card("YOLOv8s ✓","One-stage, anchor-free, ~15 ms (FP16). One framework for detection, pose and classification.","⚡","#10B981")+'</div><div class="grid g2" style="margin-top:24px">'+card("Transfer learning","Start from weights that already know general shapes, then fine-tune on our data → less data, less time, better results.")+card("Size choice: “s”","Small variant: best balance of speed and accuracy for Quadro T1000 (4 GB).")+'</div>')
# 13 datasets
add('<div class="kick">Datasets</div><h2>All datasets used</h2>'+tbl(["Dataset","Used for","Size","Classes / content"],[
["<b>D-Fire</b> (+ Roboflow fire & smoke, wildfire drone)","Fire & Smoke v2","16,027 images scanned (21,000+ in full D-Fire)","fire, smoke"],
["<b>Weapon CCTV + Knife + Pistol</b> (Roboflow weapon.v9)","Weapon detector","7,121 → 7,116 clean images","3 classes (knife, pistol/gun, rifle)"],
["<b>RWF-2000 + Real Life Violence + CCTV Violence</b>","Violence classifier","~12,000 images","violent, non_violent"],
["<b>COCO 2017</b>","YOLOv8s (pre-trained)","118,000 images","80 object classes"],
["<b>COCO Keypoints</b>","YOLOv8s-pose (pre-trained)","~64,000 annotated persons","17 body keypoints"],
["<b>AudioSet</b> (+ ESC-50 per spec)","YAMNet (pre-trained)","2M+ YouTube clips (AudioSet)","521 sound classes"],
["<b>Albumentations weather set</b> (our own)","Robustness","4,304 generated images","rain, fog, shadow, light"]]),sec="Datasets & counts")
# 14 dataset counts
add('<div class="kick">Data counts</div><h2>How much data we used</h2><div class="grid g4">'+stat("~35,100","custom training images (16,027 + 7,116 + ~12,000)","var(--cyan2)")+stat("4,304","augmented weather images","var(--violet)")+stat("~39,400","total images for our models","var(--green)")+stat("32,836","bounding boxes checked (5,187 fire + 27,649 weapon)","var(--amber)")+'</div><div class="grid g2" style="margin-top:26px"><div class="card"><h3>Weapon set — boxes per class</h3>'+hb("Class 0",11545,11545,"#06B6D4","11,545")+hb("Class 1",8572,11545,"#8B5CF6","8,572")+hb("Class 2",7532,11545,"#F59E0B","7,532")+'<p class="mini">27,649 boxes · 7,123 label files · 39 invalid lines removed</p></div><div class="card"><h3>D-Fire scanned split — boxes per class</h3>'+hb("Fire",2878,2878,"#EF4444","2,878")+hb("Smoke",2309,2878,"#64748B","2,309")+'<p class="mini">5,187 boxes · 4,306 label files · 35 invalid lines removed · 0 corrupt, 0 duplicate images</p></div></div>')
# 15 data prep
add('<div class="kick">Data preparation (Areeba)</div><h2>Clean → augment → balance</h2><div class="grid g3">'+card("1 · Integrity scan","corrupt_file_scanner.py — header check, 0-byte, duplicate hashing, label validation. D-Fire: 0 bad images. Weapon: 5 duplicates removed (331 KB). 74 bad label lines removed in total.","🧹")+card("2 · Augmentation","augmentation_pipeline.py (Albumentations): flip p0.5 · shift/scale/rotate p0.3 · brightness/contrast p0.4 · rain p0.2 · fog p0.2 · shadow p0.25 · hue/sat p0.3 · noise p0.2 → 4,304 images.","🌧️","#8B5CF6")+card("3 · Class balancing","class_balancer.py — count per class, oversample minority classes. Spec: focal loss (γ = 2.0, α = 0.25) for imbalance.","⚖️","#F59E0B")+'</div>',sec="Data preparation")
# 16 training
add('<div class="kick">Training (Moiz)</div><h2>Training setup</h2>'+tbl(["Model","Architecture","Input","Epochs","Hardware","Train time*"],[
["Fire & Smoke v2","YOLOv8s detect","640×640","<b>80</b>","Colab T4","6.2 h"],
["Weapon","YOLOv8s detect","640×640","<b>60</b>","Colab T4","4.5 h"],
["Violence","YOLOv8s-cls","224×224","<b>50</b>","Colab T4","3.8 h"],
["Normal-scene verifier","YOLOv8s","480","50","Colab T4","3.2 h"]])+'<div class="grid g3" style="margin-top:22px">'+card("Method","Transfer learning from COCO-pre-trained YOLOv8 weights; fine-tune all layers on our labelled data.")+card("Process","Train split → learn · validation split → pick best epoch (*_best.pt) · test with model_evaluation.py.")+card("Inference","FP16 on GPU; runtime input sizes: detect 480, fire 640, weapon 416, pose 416.")+'</div><p class="mini">*Training times are from the project specification and are not yet confirmed by a training log.</p>',sec="Training")
# 17 testing method
add('<div class="kick">Testing & evaluation</div><h2>How we test</h2><div class="grid g2"><div>'+tbl(["Metric","Meaning"],[
["Precision","TP ÷ (TP + FP) — when it alerts, how often right"],["Recall","TP ÷ (TP + FN) — of all real events, how many found"],["F1","Balance of precision and recall"],["IoU","Overlap of predicted box and true box"],["mAP@50","Mean average precision, box correct if IoU ≥ 0.5"],["mAP@50-95","Strict: averaged over IoU 0.5 → 0.95"],["Top-1","Classification: % of crops with the correct label"]])+'</div><div>'+card("Tools","model_evaluation.py → mAP, P, R, confusion matrix, PR curves · false_positive_analyzer.py → real alert review · benchmark_*.py → FPS & latency · stress_test.py, test_phase6_cctv.py.")+'<div style="height:16px"></div>'+card("Sign-off criteria","Detection mAP@50 ≥ 0.70 · Classification Top-1 ≥ 85% · False alarms < 5% on a 20-video test suite.","🎯","#EF4444")+'</div></div>',sec="Testing & evaluation")
# 18 fire results
add('<div class="kick">Results · Fire & Smoke v2 '+V+'</div><h2>Measured on D-Fire validation</h2><div class="grid g2"><div>'+tbl(["Metric","All","Fire","Smoke"],[
["<b>Precision</b>","<b>47.6%</b>","56.1%","39.1%"],["<b>Recall</b>","<b>25.5%</b>","22.9%","28.1%"],["<b>mAP@50</b>","<b>16.0%</b>","16.7%","15.3%"],["<b>mAP@50-95</b>","<b>7.6%</b>","7.5%","7.7%"],["Instances","5,187","2,878","2,309"]])+'</div><div class="card" style="background:#F1F5F9;border:none"><h3>Reading the numbers</h3><p style="font-size:16px">• D-Fire is hard: many tiny, distant, partly hidden fires and amorphous smoke; every box counts.<br><br>• Precision is higher than recall on purpose — fewer false alarms in a city.<br><br>• Alerts are decided over time (1.5 s + growth check), so a fire missed in one frame is caught later.<br><br>• Still below our 70% target → top priority for retraining.</p></div></div>',sec="Results")
# 19 v1 vs v2
add('<div class="kick">Improvement · Fire v1 → v2</div><h2>Neural model ≈ 2× the colour method</h2><div class="grid g2"><div class="card">'+''.join(hb(l,v,50,c,f"{v}%") + hb("v1 colour",o,50,"#CBD5E1",f"{o}%") for l,v,o,c in [("Precision v2",47.6,25,"#06B6D4"),("mAP@50 v2",16.0,8,"#8B5CF6"),("mAP@50-95 v2",7.6,3,"#8B5CF6"),("Recall v2",25.5,35,"#F59E0B")])+'</div><div>'+tbl(["Metric","Change"],[["Precision","<b>+90%</b> (+22.6 pts)"],["mAP@50","<b>+100%</b> (+8.0 pts)"],["mAP@50-95","<b>+153%</b> (+4.6 pts)"],["Recall","−9.5 pts (fewer false alarms)"]])+'<p class="mini">v1 = HSV colour heuristic: false alarms on red clothes, sunsets, tail-lights; no smoke detection. v1 values are approximate baselines.</p></div></div>')
# 20 all metrics status
add('<div class="kick">All model metrics</div><h2>Every value — and how sure we are</h2>'+tbl(["Model","mAP@50","mAP@50-95","Accuracy","FP rate","Status"],[
["YOLOv8s detector (COCO)","0.642","0.449","—","—",O],
["YOLOv8s-pose (COCO kpts)","0.812","0.531","—","—",O],
["<b>Fire & Smoke v2</b>","<b>0.160</b>","<b>0.076</b>","P 47.6% · R 25.5%","—",V],
["Weapon detector","0.724","0.488","87.2%","3.2%",R],
["Violence classifier","—","—","88.7% (Top-1)","4.1%",R],
["Normal-scene verifier","0.912","0.684","94.2%","1.1%",R],
["Vehicle crash detector","0.689","0.432","86.5%","2.8%",R],
["YAMNet audio","—","—","86.1%","3.9%",R],
["ByteTrack","—","—","92.4% IDF1","0.8% ID sw.",O]])+'<p class="mini">MEASURED = in ML_Evaluation_Report.md. SPEC CLAIM = listed in the master specification but the evaluation report still shows these as pending — run model_evaluation.py before quoting.</p>')
# 21 FP analysis
add('<div class="kick">False-alarm analysis '+V+'</div><h2>Tuning thresholds from real evidence</h2><div class="grid g2"><div>'+tbl(["Finding (7 evidence files)","Count"],[["crowd_crush alerts","3"],["fight alerts","3"],["robbery alerts","1"],["Duplicate alerts within 2 s","1"],["Alerts in dark frames (brightness 54)","2"]])+'</div><div>'+tbl(["Setting","Before","After"],[["CROWD_DANGER_RATIO","0.90","<b>0.95</b>"],["EVENT_MIN_PERSISTENCE","1.0 s","<b>1.5 s</b>"],["DETECTION_CONF","0.30","<b>0.35</b>"],["FIGHT_ARM_VELOCITY","12.0","<b>16.0</b>"],["ROBBERY_RUSH_VELOCITY","20","<b>30</b>"],["VIOLENCE_CONF","—","<b>0.70</b>"]])+'</div></div><p class="mini">False-alarm rate target < 3–5% is '+P+' — needs the full 20-video test suite.</p>',sec="Improvements")
# 22 performance
add('<div class="kick">Performance '+V+'</div><h2>Synchronous vs async pipeline</h2><div class="grid g2"><div>'+tbl(["Metric","Sync (baseline)","Async (phase 1)","Change"],[
["Display FPS","7.02","10.02","<b>+43%</b>"],["Dropped frames / 300","866","450","<b>−48%</b>"],["Wall time","42.74 s","29.93 s","<b>−30%</b>"],["Primary detector latency","60.4 ms","74.0 ms","+14 ms"],["Total pipeline latency","134.1 ms","decoupled","—"],["Peak VRAM","144 MB","157 MB","+13 MB"]])+'<p class="mini">Quadro T1000 4 GB · 1280×720 fire video · 300 frames (baseline.json, async.json)</p></div><div>'+card("After phase 1","480 px detect input, AI every 2nd frame, single track() call, smart specialist scheduler, FP16 → target 22+ FPS (config.py). Model-level budget: ~35–45 ms/frame.","🚀")+'</div></div>')
# 23 improvements list
add('<div class="kick">Improvements</div><h2>What we improved and why</h2>'+tbl(["Area","Before","After","Benefit"],[
["Fire","HSV colour rules (v1)","Neural YOLOv8s (v2)","2× mAP, +90% precision"],
["Pipeline","Synchronous, one thread","Async display + specialist worker","+43% FPS, −48% dropped"],
["Tracking","Detect, then track","One model.track() call","~2× FPS"],
["Fight logic","Fixed pixel distance, classifier required","Body-size distance, classifier optional booster","Works near & far; no silent misses"],
["Flicker","Timer reset on missed frame","Grace period","Stable alerts"],
["Stale results","Could use old detections","0.75 s / 1.2 s validity","No ghost alerts"],
["Thresholds","Guessed","Data-driven from FP analysis","Fewer duplicates / dark FPs"],
["Data","Raw downloads","Scanned, de-duplicated, augmented","Cleaner, more robust training"]]))
# 24 product
add('<div class="kick">Product (Aqib)</div><h2>Command center & operator tools</h2><div class="grid g3">'+card("Dashboard","Camera matrix 1×1 / 2×2 / grid, location tree city → sector → camera.","🗺️")+card("Live alerts","Pushed over WebSocket /ws/alerts, risk-sorted, colour-coded.","🚨","#EF4444")+card("Incidents","History, evidence clips, SHA-256 verification, heatmaps.","📁","#8B5CF6")+card("Connect camera","RTSP / webcam / test video, connection test.","📷","#10B981")+card("Voice","Web Speech → Gemini → JSON command; offline regex fallback.","🎙️","#F59E0B")+card("Stack","React + Vite frontend · FastAPI backend · SQLite · desktop Tkinter studio.","🧱","#64748B")+'</div>',sec="Product, privacy, roadmap")
# 25 privacy
add('<div class="kick">Trust & privacy</div><h2>Behavioural, not biometric</h2><div class="grid g2">'+card("No face recognition","We detect actions and objects, never identity. No face database.","🙅")+card("Human in the loop","AI suggests with a risk score; operator confirms or dismisses.","👤","#F59E0B")+card("Tamper-proof evidence","5 s pre + 3 s post clip at 15 fps, SHA-256 hash; any edit is detectable.","🔐","#10B981")+card("Access control","Login, user management, city-defined retention.","🔑","#8B5CF6")+'</div>')
# 26 goals vs actual
add('<div class="kick">Goal vs. actual</div><h2>Where we stand today</h2>'+tbl(["Goal","Target","Current","Status"],[
["Speed","25–30 FPS","7 → 10 FPS measured at 720p; 22+ target after tuning",'<span class="tag r">IN PROGRESS</span>'],
["Event types","12","12 detectors in engine",'<span class="tag v">DONE</span>'],
["Fire model","mAP@50 ≥ 70%","16.0% (precision 47.6%)",'<span class="tag p">BELOW TARGET</span>'],
["Weapon model","mAP@50 ≥ 70%","Evaluation pending",P],
["Violence model","Top-1 ≥ 85%","Validation split pending",P],
["False alarms","< 3–5%","Measuring on larger test set",P],
["Data quality","Clean data","29k+ images scanned, 4,304 augmented",'<span class="tag v">DONE</span>'],
["Evidence & routing","SHA-256, auto-route","Working",'<span class="tag v">DONE</span>']]))
# 27 limits & future
add('<div class="kick">Limitations & future work</div><h2>Honest next steps</h2><div class="grid g2"><div>'+tbl(["Limitation","Plan"],[["Fire metrics low on D-Fire","More epochs, YOLOv8m, Karachi fire data"],["Weapon / violence not evaluated","Run model_evaluation.py, publish report"],["Small far weapons","High-res crops around people"],["Night / low light","Low-light augmentation, IR cameras"],["Pixel thresholds per camera","Per-camera calibration"],["No field test yet","City pilot on real RTSP network"]])+'</div><div>'+card("Multi-sector expansion","Hospitals: patient-fall detection (URFD dataset), restricted wards, skeleton-only privacy mode. Schools: bullying detection (4,200+ clips), campus traffic (3,000+ images).","🏥")+'</div></div>')
# 28 team
add('<div class="kick">Team</div><h2>Who built what</h2><div class="grid g4">'+''.join(card(n,f"<b>{r}</b><br>{d}",i,c) for n,r,d,i,c in [
("Abdul Rafay","Team Lead & AI Architect","Async pipeline, camera input, 12-event engine, risk, audio fusion, voice, evidence, FastAPI server, integration.","🧭","#06B6D4"),
("Moiz","ML Engineer","Fire/smoke v2, weapon and violence models; Colab T4 training and tuning.","🧠","#8B5CF6"),
("Areeba","Data Scientist","Dataset scans, augmentation, class balancing, false-positive analysis, evaluation.","📊","#10B981"),
("Aqib","Frontend & UX","React + Vite command center, live view, incidents, registry, voice HUD.","🖥️","#F59E0B")])+'</div>')
# 29 close
add('<div style="margin-top:140px"><div class="quote">Cameras are already there.<br><span class="hl">VisionGuard gives them a brain.</span></div><p class="lead" style="margin-top:26px;font-size:26px">Detect · Decide · Dispatch</p><p style="margin-top:60px;font-size:30px;font-weight:800">Thank you — questions?</p><p style="margin-top:10px;color:#94A3B8;font-size:17px">github.com/AbdulRafay70/Vision-Guard</p></div>',True,"Thank you")
open('/tmp/claude-0/pdf/deck_full.html','w').write(f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>{CSS}</style></head><body>{"".join(S)}</body></html>')
print(len(S))
