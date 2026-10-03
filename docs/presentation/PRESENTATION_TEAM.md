# 🛡️ VisionGuard ULTRA — Guide for the Team
**Four people, one story. Everyone speaks. Everyone can answer. Everyone can help each other.**

Team: **Abdul Rafay** (Lead, AI system) · **Moiz** (ML / model training) · **Areeba** (Data and testing) · **Aqib** (Website and design)

> Simple English is used. Hard words have Urdu meaning in brackets, like this: *detect (پتا لگانا)*.

---

## Introduction (تعارف)

### What is this document?
This is the guide for presenting (پیش کرنا) **VisionGuard ULTRA as a team of four**. It tells you:
- who speaks and when,
- the exact line to pass the turn to the next person (handover / باری دینا),
- who answers which question,
- what to do if the demo breaks or someone is absent (غیر حاضر).

**Every member must read the full document**, not only their own part.

### Our project in 30 seconds
**VisionGuard ULTRA** is an AI system. It makes normal CCTV cameras smart.
- It can **detect (پتا لگانا)** fire, fights, guns, big crowds, road accidents, and bags left alone.
- It gives a **risk score (خطرے کا نمبر)** from 0 to 100.
- It saves the video as **evidence (ثبوت)** that nobody can change secretly.
- It sends the alert to the right number: **Police 15, Fire 16, Rescue 1122**.

Made for the Alibaba AI Hackathon 2026.

### How the team introduces itself
**Start (Abdul Rafay):**
> "Assalam-o-Alaikum. We are team **VisionGuard**. We make normal CCTV cameras smart, so they can **find a problem, decide, and send help** very fast. Let us introduce ourselves."

**Each person says one line, in this order (5 seconds each, take one small step forward):**
| Member | Line |
|---|---|
| Abdul Rafay | "I am Abdul Rafay, team lead. I built the main AI system." |
| Moiz | "I am Moiz, ML engineer. I trained our fire, gun and fight models." |
| Areeba | "I am Areeba, data scientist. I prepared the data and I test how correct the models are." |
| Aqib | "I am Aqib. I made the website and the control room screen you will see." |

**Back to Abdul Rafay:** > "Let's start with the problem." → hook.

*If time is short (1–3 min):* Rafay introduces everyone in one line: "I am Abdul Rafay, with Moiz on models, Areeba on data, and Aqib on the website."

### How to use this guide
| Section | Who must know it well |
|---|---|
| 1–3 (roles, timing, scripts) | Everyone — your own part word by word, others' parts roughly |
| 4 (questions) | Everyone, mostly Rafay (he gives questions to others) |
| 5 (short time) | Rafay + Areeba (she watches the time) |
| 6 (demo breaks) | Aqib + Rafay |
| 7–8 (practice, small card) | Everyone |

---

## 0. Team Checklist (one day before + 30 minutes before)

| ✅ | Thing to check | Who |
|---|---|---|
| ☐ | Backend (سرور) running: `python prototype/run_web.py` | Abdul Rafay |
| ☐ | Website running: `cd frontend && npm run dev`, logged in, tabs in order | Aqib |
| ☐ | Model files are there (`violence_classifier_best.pt`, `fire_smoke_best.pt`, `weapon_detection_best.pt`), one test run done | Moiz |
| ☐ | Numbers printed from `prototype/data_science/ML_Evaluation_Report.md` (only real, checked numbers) | Areeba |
| ☐ | **Backup video (متبادل ویڈیو)** of the demo on laptop + USB + phone | Aqib |
| ☐ | Full practice **at least 3 times** with a timer | Everyone |
| ☐ | Everyone has read **the full document** | Everyone |
| ☐ | Same type of clothes. Phones on silent. | Everyone |

---

## 1. Who Does What

| Member | Speaks about | Answers questions about | Extra job on stage |
|---|---|---|---|
| **Abdul Rafay** | Start, problem, solution, system diagram, end | System design, speed, server, voice, many cameras | **Moderator (منتظم)** — gives each question to the right person |
| **Aqib** | Live demo (uses the laptop) | Website, design, how the operator uses it | **Demo driver** — does all clicks and fixes problems |
| **Moiz** | Models and training | Why YOLOv8, training, GPU, speed | Helps with technical questions |
| **Areeba** | Data, testing, false alarms, privacy | Data, accuracy, false alarms, bias, privacy | **Timekeeper (وقت دیکھنے والی)** — shows signal at 1 min and 30 sec left |

**Where to stand:** the speaker stands in the middle front. Aqib stays at the laptop. Others stand a little back and look at the speaker (not at phones).

---

## 2. Time Plan (about 7 minutes; for less time see section 5)

| Time | Who | Part |
|---|---|---|
| 0:00–0:30 | All (Rafay starts) | Team introduction + hook |
| 0:30–1:00 | Abdul Rafay | Problem |
| 1:00–1:30 | Abdul Rafay | Solution (Find → Decide → Send help) |
| 1:30–3:30 | **Aqib** | Live demo |
| 3:30–4:30 | **Moiz** | Models and training |
| 4:30–5:30 | **Areeba** | Data, testing, false alarms, privacy |
| 5:30–6:30 | Abdul Rafay | System diagram + many cameras + future |
| 6:30–7:00 | Abdul Rafay | End → questions |

---

## 3. What Each Person Says

### 🎤 Abdul Rafay — Start (0:00–1:30)

*(First, the team introduction — see Introduction above.)*

**Hook (ہُک — first line to catch attention):**
> "Karachi has more than 20 million people and thousands of CCTV cameras. But these cameras only **record**. Nobody is really **watching**."

**Problem (مسئلہ):**
- Normal CCTV shows the crime only **after** it happens.
- People watching screens get tired after about 20 minutes. One person cannot watch 50 screens.
- Help comes late, because first someone must see it, then call.
- There are many dangers: fights, guns, fire, big crowds, accidents, bags left alone.

**Solution (حل):**
> "VisionGuard ULTRA makes cameras smart. It watches all cameras together. It finds dangers in **real time (فوری طور پر)**, gives a risk score, saves proof, and sends the alert to Police 15, Fire 16 or Rescue 1122. **Find, decide, send help.** Aqib will show you live."

**Pass the turn →** *"Aqib, please show them."*

---

### 🖥️ Aqib — Live Demo (1:30–3:30)

| # | Click | Say |
|---|---|---|
| 1 | Dashboard (camera grid) | "This is the control room screen. AI is checking every camera live." |
| 2 | Play `fire.mp4` | "It found fire and smoke. It checks for a few seconds first, so there is no **false alarm (غلط الارم)**. Alert goes to Fire Brigade 16." |
| 3 | Play `fighting.mp4` or `gun.mp4` | "Here is a fight / a gun. You can see the body points (skeleton / ڈھانچہ). Moiz will explain how the system checks a fight." |
| 4 | Point at risk score + alert list | "Every event gets a score from 0 to 100. The most dangerous one is always on top." |
| 5 | Incidents page | "Every event saves a video clip as evidence. It has a **SHA-256 hash** — a digital fingerprint (ڈیجیٹل انگوٹھے کا نشان). If someone changes the video, it will not match." |
| 6 | (Optional) Say "What is going on?" | "The operator can talk to the system. No clicking needed." |

**Aqib's rules:** tell the judges where to look. Never say sorry for slow speed. Stay calm if something breaks (see section 6).

**Pass the turn →** *"So how does the AI decide this? Moiz."*

---

### 🧠 Moiz — Models and Training (3:30–4:30)
- "The base is **YOLOv8**. It finds objects like people, cars and bags. **YOLOv8-Pose** finds 17 points on the body. **ByteTrack** gives each person a fixed ID number, so we can follow them."
- "Then we **trained (تربیت دی) three special models** on Google Colab: one for **fights**, one for **fire and smoke** (D-Fire data), and one for **guns**."
- "Why YOLOv8? It is fast on a small computer. We get 24–30 frames per second on a 4 GB Quadro T1000. And one tool can do objects, body points and classification."
- "The video part and the AI part run **separately (الگ الگ)**. So the video never freezes (رکتی نہیں)."

**Pass the turn →** *"But a fast model is useless if it gives wrong alarms. Areeba."*

---

### 📊 Areeba — Data, Testing, Trust (4:30–5:30)
- "First we cleaned the data. We removed broken files, balanced the classes (برابر کیا), and added blur, rain and low light to the images, so they look like real CCTV."
- "False alarms are the biggest risk. So we check **two times**: first fast arm movement starts a check, then the fight model checks the person again. The event also must continue for some time before an alert."
- "We test using precision, recall and mAP *(say only the real numbers from the report)*."
  - *Precision (درستگی)* = when it gives an alarm, how often it is right.
  - *Recall (پکڑنے کی شرح)* = from all real events, how many it catches.
- "About privacy (رازداری): we check **actions**, not **who** the person is. No face recognition, no face database. A human confirms before police are sent."

**Pass the turn →** *"Rafay will show how this works for a whole city."*

---

### 🎤 Abdul Rafay — System, Future, End (5:30–7:00)

```
Cameras / Mic / SOS → YOLOv8 → ByteTrack → Pose → Special models
→ Event Engine (12 checks over time) → Risk 0–100
→ Send alert · Save evidence · Dashboard · AI short report
```
- **Many cameras:** each camera works alone. We add more small GPU computers. The main server only gets alerts, not full video.
- **No internet:** detection works on the local computer. Only voice and report need internet, and they have a backup.
- **Future:** test on real city cameras, more local data, use in hospitals, schools and factories, connect directly to helplines.

**End (everyone steps forward):**
> "Cameras are already there. VisionGuard gives them a brain. Find, decide, send help. Thank you. We are happy to take your questions."

---

## 4. Team Questions System (سوال و جواب)

### 4.1 Rules
1. **Abdul Rafay is the moderator.** He repeats the question in simple words (this gives time to think), then says *"Moiz, can you answer this?"*
2. Only **one person** answers. Others do not interrupt (بیچ میں نہ بولیں). If someone wants to add, wait and say *"Can I add one point?"* — only one line.
3. Each answer is **less than 30 seconds**.
4. If you don't know, say *"Areeba worked on this, she can answer better."* — no long silence.
5. **Never say a teammate is wrong in front of judges.** Add gently: "To add to that…"

### 4.2 Who answers what

| Topic | First person | Backup |
|---|---|---|
| System design, speed, server, many cameras, voice, Gemini | Abdul Rafay | Moiz |
| Model choice, training, YOLO vs Transformers, GPU, FPS | Moiz | Abdul Rafay |
| Data, accuracy, false alarms, bias, privacy | Areeba | Moiz |
| Website, design, how the operator uses it | Aqib | Abdul Rafay |
| Business, cost, customers, other products, future | Abdul Rafay | Areeba |

### 4.3 Ready answers (everyone should know all of them)

| Question | Simple answer (who) |
|---|---|
| Why YOLOv8, not RT-DETR / Faster R-CNN? | YOLOv8 is fast and light. Faster R-CNN is too slow for many cameras. Transformers need a strong computer. YOLOv8 does objects + body points + classification in one tool. **(Moiz)** |
| What about hugging or sports — false alarm? | Fast movement starts a check → fight model checks again → event must continue for some time → limits can be changed. **(Areeba)** |
| How accurate (درست) is it? | Only real numbers from the report. If not ready: "We are finishing the final test report. The system checks two times before an alert." **(Areeba)** |
| How fast? | 24–30 FPS, 28–42 ms AI per frame, alert in less than 300 ms, on Quadro T1000 4 GB. **(Moiz)** |
| Can it work with 1000 cameras? | Yes, add more small GPU computers. Main server only gets alerts. **(Rafay)** |
| What if internet stops? | Detection works locally. Voice and report have offline backup. **(Rafay)** |
| Is this spying (جاسوسی)? | No. We check actions, not faces. No face database. Only logged-in people see data. Evidence has a fingerprint. **(Areeba)** |
| What if police are sent by mistake? | The system only suggests. A human checks and confirms. **(Rafay)** |
| Is the screen easy to use in stress? | Danger sorted on top, colors, one click to open an event, voice control. **(Aqib)** |
| Who will buy it? Cost? | Safe City, police control rooms, malls, universities, hospitals. Uses old cameras, only needs small GPU computers. **(Rafay)** |
| What is new in it? | Many dangers + two checks + evidence + alerts in one fast system, made for our cities, works on a small computer. **(Rafay)** |
| Who did what? | Each person says their own part in one line (section 1). **(All)** |

### 4.4 Difficult moments (مشکل حالات)

| Situation | What the team does |
|---|---|
| Nobody knows the answer | Rafay: "Honestly, we have not tested that yet. This is how we would do it…" Never make up numbers. |
| Judge asks a quiet member directly | That member answers. Others stay quiet, even if they know more. (Judges check if everyone worked.) |
| Two people start talking | The person who was not given the question stops and says "Go ahead." |
| Judge doubts (شک) a number | "Fair point. This is from our test computer and videos. Real city test is next." |
| A teammate says something wrong | Don't correct right away. Later Rafay says: "Just to make that point clear…" |
| Judge is angry or rude | Rafay answers. Calm, short, says thank you. No arguing (بحث نہیں). |
| A member is absent | Their backup takes their part (table 4.2). If Aqib is absent, Moiz does the demo. If Rafay is absent, Moiz starts and gives questions. |
| Time is cut short | Areeba gives the signal → Rafay goes to the End. |

---

## 5. Short Time? Use This

| Time | Who speaks |
|---|---|
| **1 minute** | Only Rafay (hook + solution + end). Aqib plays one video quietly. |
| **3 minutes** | Rafay (1 min) → Aqib demo (1.5 min) → Rafay end (30 sec). Moiz and Areeba answer questions. |
| **5 minutes** | Rafay 1 min → Aqib 1.5 min → Moiz 45 sec → Areeba 45 sec → Rafay 1 min |
| **7+ minutes** | Full plan (section 2) |

Even in short time: **say all four names**, so judges know who to ask.

---

## 6. If the Demo Breaks (Aqib fixes, Rafay keeps talking)

While Aqib fixes it, **Rafay keeps talking** and explains the system diagram. Maximum 20 seconds for each fix.

| Problem | Fix | If still broken |
|---|---|---|
| Backend stopped | `python prototype/run_web.py` | Desktop app: `python prototype/visionguard_app.py` |
| Website stopped | `cd frontend && npm run dev -- --host` | Desktop app |
| Video slow | Use 1×1 layout, close other apps | Simple player: `python prototype/run.py --source video --file prototype/Videos/fire.mp4` |
| Mic not working | Type in the voice box | Skip voice |
| Full crash | — | **Play backup video**: "This is the same system, recorded before." |

---

## 7. Practice Plan (مشق کا منصوبہ)

1. **Practice 1 — reading:** everyone reads their part. Use a timer.
2. **Practice 2 — passing turns:** practice every handover line until it is smooth.
3. **Practice 3 — full with fake judges:** a friend asks the questions from 4.3 and some random ones. Practice giving questions to the right person.
4. **Practice 4 — break the demo:** stop the backend on purpose and fix it.
5. **Swap practice:** each person presents someone else's part one time (in case someone is absent).
6. **English practice:** say your part out loud 5 times. If a word is hard, use a simpler word. Judges care about the idea, not perfect English.

---

## 8. Small Card (print one for each person)

```
RAFAY  Introduction → Hook → Problem → Solution → "Aqib, please show them."
AQIB   Dashboard → fire → fight/gun → risk score → Incidents/SHA-256 → voice → "Moiz."
MOIZ   YOLOv8 + Pose + ByteTrack → 3 trained models → 24–30 FPS, separate parts → "Areeba."
AREEBA Clean data → two checks + time check → real numbers → privacy → "Rafay."
RAFAY  System diagram → many cameras / no internet → future → END (all step forward)
Q&A    Rafay gives questions · one person talks · under 30 sec · never make up numbers
BROKEN Rafay talks, Aqib fixes in 20 sec, else backup video
```
