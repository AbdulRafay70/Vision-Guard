# 🛡️ VisionGuard ULTRA — Solo Guide for Abdul Rafay
**Abdul Rafay (Team Lead) tells the full story alone: talk → show demo → explain → answer questions.**

> Simple English is used. Hard words have Urdu meaning in brackets, like this: *detect (پتا لگانا)*.

---

## Introduction (تعارف)

### What is this document?
This is a guide for **Abdul Rafay** to present (پیش کرنا) VisionGuard ULTRA alone, for the full team. You can use it with judges at the stall, on stage, in a viva, or on an online call.
Read it fully one time. Then practice (مشق) sections 2 and 4 out loud. Keep the small card (section 7) in your pocket.

### Our project in 30 seconds
**VisionGuard ULTRA** is an AI system. It makes normal CCTV cameras smart.
- It can **detect (پتا لگانا)** fire, fights, guns, big crowds, road accidents, and bags left alone.
- It gives a **risk score (خطرے کا نمبر)** from 0 to 100.
- It saves the video as **evidence (ثبوت)** that nobody can change secretly.
- It sends the alert to the right number: **Police 15, Fire 16, Rescue 1122**.

Made by Abdul Rafay, Moiz, Areeba and Aqib for the Alibaba AI Hackathon 2026.

### How to introduce yourself (say this first)
> "Assalam-o-Alaikum. My name is **Abdul Rafay**. I am the **team lead** of team **VisionGuard**. I built the main AI system — the part that runs all the models together in real time. My team is **Moiz**, who trained our AI models, **Areeba**, who prepared and tested the data, and **Aqib**, who made the website. Today I will show you how we make normal CCTV cameras smart. Our system can **find a problem, decide, and send help** — very fast."

Tips: Smile. Say your name slowly. Keep it short (15–20 seconds).

### Your work vs. team work — know the difference (فرق)
Judges may ask "What did **you** do?" Be clear and fair (منصفانہ):

| Part | Who made it | How you say it |
|---|---|---|
| AI pipeline (`pipeline.py`), camera input, Event Engine (12 checks), voice commands, FastAPI server | **You (Abdul Rafay)** | "**I** built…" |
| Training fire, gun and fight models | **Moiz** | "**Moiz** trained… I connected them to the system." |
| Data cleaning, augmentation, testing, false-alarm study | **Areeba** | "**Areeba** prepared and tested…" |
| React dashboard, design, control room screen | **Aqib** | "**Aqib** designed…" |

Always give credit (کریڈٹ) to teammates by name. Judges like a lead who respects the team.

### If a judge asks something from a teammate's part
You know the basic answer (section 3). If it goes very deep, say:
> "Moiz did the training in detail. The main idea is… If you want, I can share his exact training settings later."

### How to use this guide
| If you have… | Read this |
|---|---|
| 5 minutes | Section 7 (small card) + Section 4 (if demo breaks) |
| 30 minutes | Sections 1, 2, 5, 7 |
| One full day | Everything. Practice questions (section 3) with a friend. |

---

## 0. Before You Start — Checklist (30 minutes before)

| ✅ | Thing to check |
|---|---|
| ☐ | Laptop is fully charged. Charger is plugged in. Notifications are off. |
| ☐ | Start backend (سرور): `python prototype/run_web.py`. Open `http://localhost:8000/docs` to check. |
| ☐ | Start website: `cd frontend && npm run dev`. Open `http://localhost:5173` and log in. |
| ☐ | Open the desktop app one time: `python prototype/visionguard_app.py` and play `fire.mp4` (so it is ready and fast). |
| ☐ | **Backup video (متبادل ویڈیو)** of the full demo is saved on laptop, USB and phone. |
| ☐ | Demo videos are in `prototype/Videos/` (fire, fighting, gun, crowded, thugs). |
| ☐ | Browser tabs are open in this order: Dashboard → Live View → Incidents → Registry. Close other tabs. |
| ☐ | Screen zoom is 110–125%, so judges can read. |
| ☐ | Water bottle with you. Phone on silent. |

**Remember:** The demo only helps. Your **story** is the main thing. If the demo stops, your story can still win.

---

## 1. The Plan (remember this order)

```
HOOK (20s) → PROBLEM (40s) → SOLUTION (40s) → LIVE DEMO (2–3 min)
→ HOW IT WORKS (1 min) → BENEFIT & FUTURE (30s) → END (15s) → QUESTIONS
```

**Hook (ہُک)** = the first line that catches attention (توجہ کھینچنا).

Change length by your time:

| Time you get | What to say |
|---|---|
| **1 minute** | Hook + 1 line problem + solution + 1 video (fire or gun) + end |
| **3 minutes** | Full plan below, show 2 videos |
| **5–7 minutes** | Full plan + 3–4 videos + system diagram + future plans |
| **10+ minutes (viva)** | Everything + show **your own code** (`prototype/ai/pipeline.py`, `prototype/events/engine.py`, `prototype/voice/interpreter.py`, `prototype/web/server.py`) + team's data part |

---

## 2. What to Say — Step by Step

### Step 1 — Hook (about 20 seconds)
> "Karachi has more than 20 million people and thousands of CCTV cameras. But these cameras only **record**. Nobody is really **watching**. A person watching screens gets tired after about 20 minutes. So the camera sees the crime… but nobody acts."

**Tip:** Stop for 2 seconds after "nobody acts". Look at the judges.

### Step 2 — Problem (مسئلہ) (about 40 seconds)
- Normal CCTV only shows the crime **after** it happens. It does not stop it.
- People who watch screens get tired. One person cannot watch 50 screens.
- Help comes late, because first someone must see it, then call 15 / 16 / 1122.
- There are many dangers: fights, robbery, fire, big crowds, accidents, bags left alone.

### Step 3 — Solution (حل) (about 40 seconds)
> "**VisionGuard ULTRA** makes cameras smart. It watches all cameras at the same time. It finds fire, fights, guns, crowds, accidents and left bags in **real time (فوری طور پر)**. It gives a risk score, saves the proof, and sends the alert to the right place — Police 15, Fire 16, Rescue 1122."

Repeat these three words: **Detect → Decide → Dispatch** (پتا لگاؤ → فیصلہ کرو → مدد بھیجو).

### Step 4 — Live Demo (2–3 minutes)

| # | What you click | What you say |
|---|---|---|
| 1 | Open **Dashboard** (camera grid) | "This is the control room screen. AI is checking every camera right now." |
| 2 | Play **`fire.mp4`**, wait for red box | "It found fire and smoke. It checks for a few seconds first, so it does not give a **false alarm (غلط الارم)**. Alert goes to **Fire Brigade 16**." |
| 3 | Play **`gun.mp4`** or **`fighting.mp4`** | "Here is a gun / a fight. For fights, we see 17 points on the body (skeleton / ڈھانچہ). If the arms move very fast, a second model checks it again. Two checks = fewer mistakes." |
| 4 | Point at **risk score** and alert list | "Every event gets a score from 0 to 100. The most dangerous one is always on top." |
| 5 | Open **Incidents** page | "Every event saves a video clip as **evidence (ثبوت)**. We add a **SHA-256 hash** — a digital fingerprint (ڈیجیٹل انگوٹھے کا نشان). If someone changes the video, the fingerprint will not match." |
| 6 | (Optional) Say **"What is going on?"** | "The operator can talk to the system. No need to click." |
| 7 | (Optional) **`crowded.mp4`** | "It checks crowd size and movement, to warn before a **stampede (بھگدڑ)**." |

**Demo rules:**
- Tell the judge where to look: "Look at the top left. The box is red now."
- Never say "it usually works". If it is slow, say: "While it loads, let me explain what it is doing…"
- Only 2–3 videos in a 3-minute talk. Show less, explain better.

### Step 5 — How It Works (about 1 minute)
Show or draw this:

```
CAMERAS / MIC / SOS
      ↓
YOLOv8 (finds objects) → ByteTrack (follows each person) → Pose (17 body points)
      ↓
Special models (fire/smoke, gun, fight)
      ↓
Event Engine (12 checks, over time) → Risk score 0–100
      ↓
Send alert · Save evidence · Show on dashboard · AI short report
```

Main points:
1. **Two parts run separately (الگ الگ)** — video shows on one side, AI works on the other side. So the video never freezes (رکتی نہیں).
2. **Two checks** — first a quick check, then a strong check. This means fewer false alarms.
3. **Time check** — the event must continue for some time, not only one frame (تصویر).
4. **Works on a small computer** — tested on an NVIDIA Quadro T1000 graphics card (4 GB).

### Step 6 — Benefit & Future (فائدہ اور مستقبل) (about 30 seconds)
- **Benefit:** help comes faster, workers get less tired, cities can use the cameras they already have. No new cameras needed.
- **Future:** test it on real city cameras, use it in hospitals, schools and factories (see `prototype/MULTI_SECTOR_EXPANSION_PLAN.md`), connect directly to the helplines, collect more local Karachi data.

### Step 7 — End (about 15 seconds)
> "Cameras are already there. VisionGuard gives them a brain. **Find, decide, send help — in less than one second.** This was built by Moiz, Areeba, Aqib and me. Thank you. I am happy to take your questions."

Then **stop talking**. Silence (خاموشی) invites questions.

---

## 3. Questions and Answers (سوال و جواب)

### 3.1 The easy method for every question — L.A.B.
1. **Listen (سنیں)** — listen to the full question. Do not interrupt (بیچ میں نہ بولیں).
2. **Accept (مانیں)** — say "Good question" or "That is an important point."
3. **Bring back (واپس لائیں)** — answer in 1–3 short lines, then go back to a strong point of the project.

Keep each answer **under 30 seconds**.

### 3.2 Common questions and simple answers

**Technical questions (تکنیکی سوالات)**

| Question | Simple answer |
|---|---|
| Why YOLOv8 and not a Transformer (RT-DETR) or Faster R-CNN? | YOLOv8 is fast and needs less memory. Faster R-CNN is too slow for many live cameras. Transformers need a stronger computer. YOLOv8 can do objects, body points and classification in one tool. |
| What about false alarms? Hugging, playing, sports? | We use three steps: (1) fast arm movement starts a check, (2) a second model checks the person again, (3) the event must continue for some time. We can also change the limits in `config.py`. |
| How fast is it? | 24–30 frames per second. AI takes about 28–42 ms for one frame. The alert comes in less than 300 ms (less than one third of a second). Say: "on our test computer". |
| Which data did you use? | Fight: RWF-2000 and other violence video sets. Fire/smoke: D-Fire. Guns: public weapon image sets. We trained on Google Colab (T4 GPU). We removed broken files and added blur and rain effects to look like real CCTV. |
| How accurate (درست) is it? | Only tell numbers from `prototype/data_science/ML_Evaluation_Report.md`. If they are not ready, say: "We are still finishing the final test report. In our demo videos it works well, and the system checks two times before it gives an alert." |
| How does tracking (پیچھا کرنا) work? | ByteTrack gives each person or car a fixed ID number. So we can see how long someone stays, if a bag is left, and how fast things move. |
| How do you find a left bag? | We follow the bag by its ID. If it does not move and its owner is gone for some time, we give an alert. |
| Can it work with 1000 cameras? | Yes. Each camera works on its own. We add more small GPU computers. The main server only gets alerts and small pictures, not full video. |
| What does Gemini (the LLM) do? | It writes a short report in normal language, and it understands voice commands. Finding the danger does **not** need Gemini. |
| What if internet stops? | Detection works on the local computer. Only the voice and report part uses internet, and it has an offline backup. |

**Privacy and ethics questions (رازداری اور اخلاقیات)**

| Question | Simple answer |
|---|---|
| Is this spying (جاسوسی) on everyone? | No. We check **actions**, not **who** the person is. We do not use face recognition. We do not keep a face database. |
| Is it biased (جانبدار)? | We look at actions and objects, not skin, face or clothes. We still want more local data and more testing in different light and crowds. |
| Who can see the data? | Only people with login. Evidence has a hash, so any change can be caught. The city decides how long data is kept. |
| What if it sends police by mistake? | The system only **suggests**. A human operator checks and confirms. AI helps, humans decide. |

**Business questions (کاروباری سوالات)**

| Question | Simple answer |
|---|---|
| Who will buy it? | Safe City projects, police control rooms, malls, universities, hospitals, factories. |
| What is the cost? | It uses the cameras that already exist. Cost is only small GPU computers and support. Cheaper than many people watching screens 24 hours. |
| What is different from others? | Many dangers in one system, two checks, safe evidence, voice control, made for local needs (15, 16, 1122), works on a small computer. |
| Next 6 months? | Test with real city cameras, collect local data, finish the accuracy report, connect to helplines. |

### 3.3 Difficult moments (مشکل حالات)

| Situation | What to do / say |
|---|---|
| **Judge asks "What did YOU do?"** | "I am the team lead. I built the main AI pipeline, the event engine with 12 checks, the voice commands and the server. I also connected everyone's work into one system." |
| **You do not know the answer** | "Good question. I don't want to guess. What I know is… I will send you the exact details later." Never make up numbers. |
| **Judge says "this is not new"** | "Yes, finding objects is not new. Our new part is putting many dangers, two checks, evidence and alerts together in one fast system for our cities." |
| **Judge doubts (شک) a number** | "Fair point. These numbers are from our test computer and demo videos. A real city test is our next step." Being honest is better than fighting. |
| **Judge is angry or rude** | Stay calm. Speak slowly. Say thank you. Answer the main point. Do not argue (بحث نہ کریں). |
| **Two questions together** | "Let me answer one by one. First…" |
| **Question not about our project** | Connect it to the project in one line, or say "This is not in our project now, but it can be added like this…" |
| **You forget what to say** | Remember the order: Problem → Solution → Demo → How → Benefit. Say "Let me show you the main part" and start the demo. |
| **Time is almost over** | Go to the End (Step 7) now. Do not rush. |

---

## 4. If the Demo Breaks (Plan A → B → C)

| Problem | Quick fix (20 seconds) | If it still fails |
|---|---|---|
| Backend stopped | `python prototype/run_web.py` | Plan B |
| Website stopped | `cd frontend && npm run dev -- --host` | Use desktop app: `python prototype/visionguard_app.py` |
| Video is slow | Use 1×1 layout, close other apps | Use simple player: `python prototype/run.py --source video --file prototype/Videos/fire.mp4` |
| Mic not working | Type the command in the voice box | Skip voice. It is optional (اختیاری). |
| Laptop crash / no GPU | — | **Plan C: play the backup video** and explain it |
| Projector problem | Turn your laptop to the judges | Draw the system on paper or board |

Say this when you switch: *"Let me show you the recorded run, so we don't waste your time. This is the same system."*

---

## 5. Numbers to Remember (say them carefully)

- **12** event checks: fire, fight, gun, robbery, kidnapping, crowd, car accident, bike accident, loitering (بلا وجہ گھومنا), left bag, blocked road, sound emergency.
- **3** models we trained: fight, fire/smoke, gun (+ YOLOv8 base models for objects and body points).
- **24–30 FPS** (frames per second), **28–42 ms** AI per frame, alert in **less than 300 ms** — on Quadro T1000 4 GB.
- **17** body points for each person.
- **SHA-256** fingerprint for evidence.
- Helplines: Police **15**, Fire **16**, Rescue **1122**, Traffic **1915**.

> ⚠️ Only say accuracy numbers that are in a real report. A wrong number makes judges stop trusting (اعتماد) you.

---

## 6. Body Language (جسمانی انداز) and Speaking

- Stand next to the screen, not in front of it. Keep your hands visible.
- Speak a little slower than normal. Stop for a moment after important lines.
- Look at the judges, not the screen. Look at the screen only to point.
- Smile at the start and at the end.
- Use short sentences. One idea in one sentence.
- If your English stops, it is okay. Take a breath and say it in simple words. Judges care about the idea, not perfect English.

---

## 7. Small Card (print this)

```
INTRO    Abdul Rafay, team lead, built AI pipeline. Team: Moiz, Areeba, Aqib.
HOOK     20 million people. Cameras record. Nobody watches.
PROBLEM  Cameras only record, people get tired, help comes late, many dangers.
SOLUTION Smart cameras: Find → Decide → Send help.
DEMO     Dashboard → fire.mp4 → gun/fight → risk score → Incidents (SHA-256) → voice
HOW      YOLOv8 → ByteTrack → Pose → Special models → Event Engine → Risk → Alert
         separate parts · two checks · time check · small computer
BENEFIT  Use old cameras, faster help, more areas in future.
END      "Cameras are there. We give them a brain." + thank team → questions.
BROKEN   run_web.py · npm run dev · desktop app · backup video
```
