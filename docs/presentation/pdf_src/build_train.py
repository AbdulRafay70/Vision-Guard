import sys; sys.path.insert(0,'/tmp/claude-0/pdf')
from train import *
D='/home/user/Vision-Guard/docs/presentation/'
SLIDES_SOLO = [
("Title","0:20","Assalam-o-Alaikum. My name is Abdul Rafay, team lead of VisionGuard. I built the main AI system. My team is Moiz, who trained our models, Areeba, who prepared and tested the data, and Aqib, who made the website.","Smile. Say your name slowly. Then pause 1 second before the next slide."),
("Problem","0:40","Karachi has more than 20 million people and thousands of cameras. But cameras only record — nobody is really watching. An operator gets tired after about 20 minutes. So the camera sees the crime, but nobody acts.","Stop for 2 seconds after “nobody acts”. Look at the judges, not the screen."),
("Solution","0:30","VisionGuard makes cameras smart. It watches all cameras together, finds the danger, gives a risk score, saves proof, and sends the alert to the right department. Detect, decide, dispatch.","Point to the three boxes one by one while saying the three words."),
("12 detectors","0:20","We cover twelve kinds of emergency — from fire and fights to accidents, crowds and bags left alone.","Do not read all twelve. Say 3–4, then move on."),
("Live demo","2:00","Let me show you live. This is the control room… Here a fire is found — it goes to Fire Brigade 16… Here a fight — see the body points… Every event gets a risk score… and evidence is sealed with a fingerprint.","Switch to the app. Tell judges where to look. If slow: “While it loads, let me explain…”"),
("How it works","1:00","One frame goes in: YOLO finds objects, ByteTrack gives each person an ID, special models check pose, fire and weapons, and the event engine checks rules over time — not one frame.","Use your hand to follow the arrows left to right."),
("Models","0:40","Moiz used transfer learning — we took YOLOv8, which already knows general shapes, and trained it more on fire, weapon and violence data on Colab GPUs.","Give Moiz credit by name."),
("Data quality","0:30","Areeba scanned sixteen thousand fire images and seven thousand weapon images, removed duplicates, made four thousand weather images, and tuned three settings from real false alarms.","Say “data-driven” — we changed settings because of evidence."),
("Results","0:40","Our fire model is two times better than the old colour method — precision 47.6 percent. The dataset is hard, with tiny fires, and our time checks catch fires across many frames. Weapon and violence reports are in progress.","Be honest and calm. Never round numbers up."),
("Performance","0:30","Our async design made it 43 percent faster on a small 4 GB GPU, and dropped half the lagging frames.","Say “measured on our test GPU”."),
("Operator experience","0:30","Aqib built the command center: live alerts sorted by risk, voice control, heatmaps, and an evidence locker.","Give Aqib credit by name."),
("Routing","0:20","Each event goes to the right number: fire to 16, police events to 15, accidents to Edhi 115, crowds to 1122.","Keep it short."),
("Trust","0:30","We are behavioural, not biometric — no face recognition. AI suggests, a human decides, and evidence cannot be secretly changed.","Slow down here; ethics matters to judges."),
("Roadmap","0:30","We know our limits: fire numbers can improve, two reports are pending. Next: more training, local Karachi data, and a city pilot.","Saying limits first builds trust (اعتماد)."),
("Close","0:15","Cameras are already there. VisionGuard gives them a brain. Built by Moiz, Areeba, Aqib and me. Thank you — questions?","Stop talking. Smile. Wait."),
]
WHO_TEAM = ["All","All","Abdul Rafay","Abdul Rafay","Abdul Rafay","Aqib","Abdul Rafay","Moiz","Areeba","Areeba","Abdul Rafay","Aqib","Abdul Rafay","Areeba","Abdul Rafay","All"]
SLIDES_TEAM = [("Title + team","0:30","We are team VisionGuard. We make normal CCTV cameras smart. Let us introduce ourselves.","Each member says one line (5 s), stepping forward a little.")] + [SLIDES_SOLO[0]] + SLIDES_SOLO[1:]
SLIDES_TEAM[1] = ("Team","0:20","I am Abdul Rafay, team lead… I am Moiz, ML engineer… I am Areeba, data scientist… I am Aqib, I made the website.","Each person speaks for their own card. Same order every time.")

DRILLS = """
| # | Judge question | Your 30-second answer (key points) |
|---|---|---|
| 1 | What did YOU build? | Pipeline, async worker, cameras, 12-event engine, risk, audio, voice, evidence, server; connected everyone's work. |
| 2 | Why YOLOv8, not RT-DETR? | Fast on a 4 GB GPU; one tool for detection, pose, classification; transformers need more compute. |
| 3 | Your fire mAP is only 16% — why? | Hard dataset with tiny fires; every box counts; v2 is 2× v1; alerts decided over time; plan: more epochs, local data. |
| 4 | What is precision vs recall? | Precision: when it says fire, how often right. Recall: of all fires, how many found. We prefer fewer false alarms. |
| 5 | Hugging or sports = fight? | Body-size distance + fast wrists + repeats 1.5 s + violence classifier ≥ 0.70. |
| 6 | Weapon accuracy? | Model works in demo; formal report not finished; I won't give an unproven number. |
| 7 | Is this mass surveillance? | Behavioural, not biometric; no face database; human confirms. |
| 8 | 1000 cameras? | Each camera independent; add edge GPUs; server receives only alerts. |
| 9 | Internet goes down? | Detection is local; only Gemini report/voice uses internet, with offline fallback. |
| 10 | How is evidence tamper-proof? | SHA-256 fingerprint; one pixel change = different hash. |
| 11 | How did you get more speed? | Display thread + background specialist thread; 7 → 10 FPS, 48% fewer dropped frames. |
| 12 | What is new here? | Many threats + two-stage check + time rules + evidence + routing, for local cities, on a small GPU. |
"""
PLAN = """
| Day | Practice (مشق) | Goal |
|---|---|---|
| Day 1 | Read the whole book once. Read the script out loud 3 times. | Know the story |
| Day 2 | Practice with slides and a timer. Record yourself on phone. | Finish on time |
| Day 3 | Practice the live demo 5 times. Break it on purpose once. | Calm demo |
| Day 4 | Q&A drill: a friend asks the 12 questions + 5 random ones. | Answers < 30 s |
| Day 5 | Full run in front of 2–3 people. Fill the score sheet. | Score 4+ everywhere |
| Final day | One light run only. Sleep well. | Fresh mind |
"""
def solo():
    b = cover("Rehearsal & Training Book","Solo Presentation Training","Abdul Rafay — full practice guide, slide by slide, with Urdu help words.",[("Presenter","Abdul Rafay"),("Deck","15 slides · ~7 min"),("Event","Alibaba AI Hackathon 2026")])
    b += sec(1,"How to use this book", md("""
This book trains you to present the **VisionGuard ULTRA solo deck** (the 15-slide PDF). Simple English is used; hard words have Urdu meaning in brackets.

1. **Part 2** — what to say on every slide, with time.
2. **Part 3** — Q&A drill: practise these 12 questions until answers are short.
3. **Part 4** — rehearsal plan and score sheet.
4. **Part 5** — the full knowledge guide (every part of the project, from start to end).
""") + box("tip","Golden rule","<p>Your <b>story</b> wins, not perfect English. Speak slowly, short sentences, look at the judges.</p>") + box("warn","Numbers rule","<p>Only say numbers that are in the deck. Weapon and violence accuracy and false-alarm rate are <b>not final</b> — never invent (گھڑنا) them.</p>"))
    b += sec(2,"Slide-by-slide script", ''.join(slide(i+1,*s) for i,s in enumerate(SLIDES_SOLO)) + box("info","Total time","<p>About 7–8 minutes. For 3 minutes: slides 1, 2, 3, 5, 6, 9, 15. For 1 minute: 1, 3, 15 + one demo clip.</p>"))
    b += sec(3,"Q&A drill (سوال و جواب کی مشق)", md("Use the **L.A.B.** method: **Listen** (سنیں) → **Accept** (مانیں) “Good question” → **Bring back** (واپس لائیں) to a strength. Under 30 seconds.\n"+DRILLS))
    b += sec(4,"Rehearsal plan & score sheet", md(PLAN) + "<h2>Score sheet</h2>" + RUBRIC + "<h2>Day-of checklist</h2><ul class='chk'>"+''.join(f'<li>{x}</li>' for x in ["Laptop charged, notifications off","Backend running (python prototype/run_web.py)","Website running (npm run dev), logged in","Desktop app warmed up with fire.mp4","Backup demo video on laptop + USB + phone","Slides PDF open in full screen","Water, phone silent"])+"</ul>")
    b += sec(5,"Full knowledge guide", mdfile(D+'PRESENTATION_SOLO.md'))
    return page(b)
def team():
    b = cover("Rehearsal & Training Book","Team Presentation Training","Abdul Rafay · Moiz · Areeba · Aqib — who says what, handovers, Q&A routing and drills.",[("Team","4 presenters"),("Deck","16 slides · ~7 min"),("Event","Alibaba AI Hackathon 2026")])
    b += sec(1,"How to use this book", md("""
This book trains the whole team to present the **16-slide team deck**. Every member reads the whole book, not only their own part.

| Member | Slides | Extra job |
|---|---|---|
| **Abdul Rafay** | 1–5, 7, 11, 13, 15, 16 | Moderator (منتظم) — gives each question to the right person |
| **Aqib** | 6 (demo), 12 | Demo driver — clicks and fixes problems |
| **Moiz** | 8 | Technical backup |
| **Areeba** | 9, 10, 14 | Timekeeper (وقت دیکھنے والی) — signals at 1 min and 30 s left |
""") + box("tip","Handover lines (باری دینا)","<p>Rafay → Aqib: <i>“Aqib, please show them.”</i> · Aqib → Moiz: <i>“How does the AI decide this? Moiz.”</i> · Moiz → Areeba: <i>“A fast model is useless if it gives wrong alarms. Areeba.”</i> · Areeba → Rafay: <i>“Rafay will show how this works for a whole city.”</i></p>"))
    b += sec(2,"Slide-by-slide script", ''.join(slide(i+1,*s,who=WHO_TEAM[i]) for i,s in enumerate(SLIDES_TEAM)))
    b += sec(3,"Q&A routing drill", md("""
**Rules:** Rafay repeats the question → names one person → that person answers in under 30 s → others stay quiet. Never correct a teammate in front of judges.

| Topic | First | Backup |
|---|---|---|
| System, speed, server, voice, scaling | Abdul Rafay | Moiz |
| Models, training, YOLO, GPU | Moiz | Abdul Rafay |
| Data, accuracy, false alarms, privacy | Areeba | Moiz |
| Website, operator workflow | Aqib | Abdul Rafay |
| Business, cost, roadmap | Abdul Rafay | Areeba |

**Drill:** one friend reads the questions below in random order. Rafay must route each in under 3 seconds.
""" + DRILLS.replace("What did YOU build?","Who did what? (each member answers own part)")))
    b += sec(4,"Rehearsal plan, failure drill & score sheet", md(PLAN + """
### Special team drills
1. **Handover drill** — run only the 4 handover lines, 5 times, until smooth.
2. **Swap drill** — each member presents another member's slides once (for absence / غیر حاضری).
3. **Failure drill** — Aqib stops the backend mid-demo; Rafay keeps talking about slide 7 while Aqib restarts it in under 20 s; if not, play the backup video.
""") + "<h2>Score sheet (fill for each member)</h2>" + RUBRIC)
    b += sec(5,"Full team guide", mdfile(D+'PRESENTATION_TEAM.md'))
    b += sec(6,"Technical knowledge (everyone should know)", mdfile(D+'PRESENTATION_SOLO.md').split('<h3>0. Before You Start')[0].split('<h3>FULL PROJECT EXPLAINED')[-1].join(['<h3>FULL PROJECT EXPLAINED','']) if False else md(open(D+'PRESENTATION_SOLO.md').read().split('## FULL PROJECT EXPLAINED',1)[1].split('## 0. Before You Start')[0].replace('\n### ','\n## ',0)))
    return page(b)
open('/tmp/claude-0/pdf/train_solo.html','w').write(solo())
open('/tmp/claude-0/pdf/train_team.html','w').write(team())
