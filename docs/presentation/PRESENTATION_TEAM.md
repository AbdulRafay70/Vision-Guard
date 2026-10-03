# 🛡️ VisionGuard ULTRA — Team Presentation Playbook
**Four presenters, one story. Every member speaks, every member can answer, every member can cover for the others.**

Team: **Abdul Rafay** (Lead Architect & AI Engineer) · **Moiz** (ML Engineer) · **Areeba** (Data Scientist & Evaluation) · **Aqib** (UI/UX & Frontend)

---

## 0. Team Prep Checklist (Day before + 30 min before)

| ✅ | Item | Owner |
|---|---|---|
| ☐ | Backend `python prototype/run_web.py` running & tested | Abdul Rafay |
| ☐ | Frontend `cd frontend && npm run dev` running, logged in, tabs in order | Aqib |
| ☐ | Models present (`violence_classifier_best.pt`, `fire_smoke_best.pt`, `weapon_detection_best.pt`), warm-up run done | Moiz |
| ☐ | Metrics sheet printed from `prototype/data_science/ML_Evaluation_Report.md` (only real, verified numbers) | Areeba |
| ☐ | Backup demo recording on laptop + USB + phone | Aqib |
| ☐ | Full rehearsal **at least 3 times** with a timer, including handovers | Everyone |
| ☐ | Everyone has read **the whole doc** — not just their own part | Everyone |
| ☐ | Same dress code; phones silent | Everyone |

---

## 1. Roles During the Presentation

| Member | Speaking part | Owns in Q&A | Backup role on stage |
|---|---|---|---|
| **Abdul Rafay** | Opening hook, Problem, Solution, Architecture, Close | Architecture, pipeline, event engine, voice, backend, scaling | **Moderator** — routes questions to the right person |
| **Aqib** | Live Demo (drives the laptop) | Dashboard, UX, frontend, operator workflow | **Demo driver** — handles all clicks + failure recovery |
| **Moiz** | Models & Training | Model choice, training, YOLOv8, hyperparameters, inference speed | Covers technical questions if Rafay is busy |
| **Areeba** | Data & Evaluation, False-alarm handling, Ethics | Datasets, metrics, false positives, bias, privacy | **Timekeeper** — signals 1-min / 30-s left |

**Standing positions:** Speaker in front-center; Aqib at the laptop; others half a step back, looking at the speaker (never at phones).

---

## 2. Run of Show (≈ 7 minutes; scale down using section 5)

| Time | Speaker | Segment |
|---|---|---|
| 0:00–0:20 | Abdul Rafay | Hook + introduce team |
| 0:20–1:00 | Abdul Rafay | Problem |
| 1:00–1:30 | Abdul Rafay | Solution (Detect → Decide → Dispatch) |
| 1:30–3:30 | **Aqib** | Live demo |
| 3:30–4:30 | **Moiz** | Models & training |
| 4:30–5:30 | **Areeba** | Data, evaluation, false alarms, ethics |
| 5:30–6:30 | Abdul Rafay | Architecture + scaling + roadmap |
| 6:30–7:00 | Abdul Rafay | Close → open Q&A |

---

## 3. Script per Member

### 🎤 Abdul Rafay — Opening (0:00–1:30)

**Hook + intro**
> "Good morning. Karachi has more than 20 million people and thousands of CCTV cameras. But those cameras only **record** — nobody is truly **watching**. We are team VisionGuard: I'm Abdul Rafay, lead architect; Moiz, our ML engineer; Areeba, our data scientist; and Aqib, who built the command center you'll see."

**Problem**
- Passive CCTV only gives evidence *after* the crime.
- Operators lose focus after ~20 minutes of watching screens; one person can't watch 50 feeds.
- Emergency response is delayed — someone first has to notice, then call.
- Threats vary: fights, weapons, fire, crowd surges, accidents, abandoned bags.

**Solution**
> "VisionGuard ULTRA turns existing cameras into an **AI City Brain**. It watches every feed simultaneously, detects emergencies in real time, scores the risk, stores tamper-proof evidence, and routes the alert to Police 15, Fire 16 or Rescue 1122. **Detect, decide, dispatch.** Aqib will show you it live."

**Handover line →** *"Aqib, show them."*

---

### 🖥️ Aqib — Live Demo (1:30–3:30)

| # | Click | Say |
|---|---|---|
| 1 | Dashboard grid | "This is the operator command center. Every tile is analysed live by AI." |
| 2 | Play `fire.mp4` | "Fire and smoke detected — notice it confirms over several frames before alerting. Routed to Fire Brigade 16." |
| 3 | Play `fighting.mp4` or `gun.mp4` | "A fight / weapon. You can see the pose skeletons — Moiz will explain how they confirm violence." |
| 4 | Point at risk score + alert list | "Every event gets a 0–100 risk score, so the most dangerous incident is always at the top." |
| 5 | Incidents page | "Each incident saves an evidence clip with a SHA-256 hash — any edit to the video breaks the hash." |
| 6 | (Optional) Voice: "What is going on?" | "Operators can control it hands-free." |

**Rules for Aqib:** narrate where to look, never apologise for speed, keep calm on failure (see section 6).

**Handover line →** *"So how does the AI actually decide this? Moiz."*

---

### 🧠 Moiz — Models & Training (3:30–4:30)
- "The base is **YOLOv8s** for objects and **YOLOv8s-Pose** for 17 body keypoints, with **ByteTrack** to give everyone a stable ID."
- "On top, we trained **three specialist models** on Colab T4 GPUs: a **violence classifier**, a **fire/smoke detector** (D-Fire dataset), and a **weapon detector**."
- "Why YOLOv8? It's real-time on modest hardware — we run at 24–30 FPS on a 4 GB Quadro T1000 — and one framework covers detection, pose and classification."
- "The pipeline is **asynchronous**: display and AI run on separate threads, so video never freezes."

**Handover line →** *"But a fast model is useless if it cries wolf. Areeba."*

---

### 📊 Areeba — Data, Evaluation, Trust (4:30–5:30)
- "Data quality first: we scanned datasets for corrupt files, balanced classes, and augmented images with blur, rain and low light using Albumentations, to mimic real CCTV."
- "False alarms are the biggest risk, so we use **two-stage verification**: pose speed raises a suspicion, the violence classifier confirms on the person crop, and the event must **persist over time** before it alerts."
- "We evaluate with precision, recall and mAP — *(quote only verified numbers from the evaluation report)*."
- "On ethics: VisionGuard is **behavioural, not biometric**. We detect events, not identities — no face database. Humans confirm high-impact dispatches."

**Handover line →** *"Rafay will show how this scales to a whole city."*

---

### 🎤 Abdul Rafay — Architecture, Roadmap, Close (5:30–7:00)

```
Cameras / Mic / SOS → YOLOv8 → ByteTrack → Pose → Specialists
→ Event Engine (12 detectors, temporal rules) → Risk 0–100
→ Dispatch · SHA-256 Evidence · Dashboard · AI briefing
```
- **Scaling:** each camera is an independent worker; add edge GPU nodes; the center only receives events and thumbnails.
- **Offline-safe:** detection is local; only the AI narration/voice uses the cloud and has an offline fallback.
- **Roadmap:** city pilot on real RTSP cameras, local training data, multi-sector (hospitals, schools, industry), real dispatch integration.

**Close (everyone steps forward):**
> "Cameras already exist. VisionGuard gives them a brain. Detect, decide, dispatch. Thank you — we'd love your questions."

---

## 4. Team Q&A System

### 4.1 Routing rules
1. **Abdul Rafay is moderator.** He repeats/rephrases the question (buys time, makes sure everyone heard), then says *"Moiz, would you take that?"*
2. Only **one person** answers. Others don't interrupt. If a teammate wants to add, they wait and say *"If I may add one point…"* — max one sentence.
3. Answers **≤ 30 seconds.**
4. If the assigned person doesn't know, they say *"Let me hand that to Areeba, she worked on that directly."* — no awkward silence.
5. **Never contradict a teammate in front of judges.** Fix it gently: "To add to that…"

### 4.2 Who answers what

| Topic | Primary | Backup |
|---|---|---|
| Architecture, pipeline, latency, scaling, backend, API, voice, LLM | Abdul Rafay | Moiz |
| Model choice, training, YOLO vs Transformers, GPU, FPS | Moiz | Abdul Rafay |
| Datasets, accuracy, false alarms, bias, privacy, ethics | Areeba | Moiz |
| UI, operator workflow, usability, dashboard features | Aqib | Abdul Rafay |
| Business, cost, customers, competition, roadmap | Abdul Rafay | Areeba |

### 4.3 Prepared answers (everyone should know all of these)

| Question | Answer (owner) |
|---|---|
| Why YOLOv8 not RT-DETR / Faster R-CNN? | Real-time on edge; Faster R-CNN too slow for multiple streams; transformers need more compute; YOLOv8 covers detection + pose + classification in one framework. **(Moiz)** |
| What about hugging / sports false alarms? | Pose trigger → violence classifier confirmation → temporal persistence → configurable thresholds. **(Areeba)** |
| Your accuracy? | Quote verified report numbers only. If not final: "formal validation is being finalised; pipeline verifies before alerting." **(Areeba)** |
| FPS / latency? | 24–30 FPS, ~28–42 ms AI per frame, alert < ~300 ms on Quadro T1000 4 GB. **(Moiz)** |
| Scale to 1000 cameras? | Horizontal edge nodes; central server gets events only. **(Rafay)** |
| Internet down? | Detection is local; LLM features have offline fallback. **(Rafay)** |
| Privacy / mass surveillance? | Behavioural not biometric, no face DB, role-based access, hashed evidence. **(Areeba)** |
| Wrong dispatch? | AI recommends with risk score, human operator confirms. **(Rafay)** |
| Is the UI usable under stress? | Risk-sorted alerts, color coding, one-click incident view, voice control. **(Aqib)** |
| Who buys this? Cost? | Safe City projects, police control rooms, malls, campuses, hospitals; runs on existing cameras + edge GPU. **(Rafay)** |
| What's novel? | Multi-threat + verification + evidence + dispatch in one real-time system, tuned for local context, on modest hardware. **(Rafay)** |
| Who did what? | Each member states their own part in one line (section 1). **(All)** |

### 4.4 Hard situations

| Situation | Team response |
|---|---|
| Nobody knows the answer | Moderator: "Honest answer — we haven't tested that yet. Here's how we'd approach it…" Never invent numbers. |
| Judge asks a quiet member directly | That member answers; others stay quiet even if they know more. (Judges test whether everyone contributed.) |
| Two members start answering | The one who did **not** get routed stops: "Go ahead." |
| Judge challenges a number | "Fair point — that's on our test hardware/videos; field pilot is next." |
| Teammate says something wrong | Don't correct immediately. Moderator adds later: "Just to clarify that point…" |
| Hostile judge | Moderator answers, calm and short, thanks them. |
| A member is absent | Their part goes to their **backup** (table 4.2). If Aqib is absent, Moiz drives demo. If Rafay is absent, Moiz moderates and opens. |
| Time cut short | Timekeeper (Areeba) signals → Rafay jumps to Close. |

---

## 5. Scaling the Team Pitch to Any Time Slot

| Slot | Who speaks |
|---|---|
| **1 min** | Rafay only (hook + solution + close), Aqib shows one clip silently |
| **3 min** | Rafay (1 min) → Aqib demo (1.5 min) → Rafay close (30 s); Moiz & Areeba answer in Q&A |
| **5 min** | Rafay 1 min → Aqib 1.5 min → Moiz 45 s → Areeba 45 s → Rafay 1 min |
| **7+ min** | Full run of show (section 2) |

Even in short slots: **introduce all four names** so judges know who to ask.

---

## 6. Demo Failure Protocol (Aqib leads, Rafay fills the silence)

While Aqib fixes, **Rafay keeps talking** (explains architecture). Max 20 seconds per fix.

| Failure | Fix | Fallback |
|---|---|---|
| Backend down | `python prototype/run_web.py` | Desktop Studio `python prototype/visionguard_app.py` |
| Frontend down | `cd frontend && npm run dev -- --host` | Desktop Studio |
| Lag | 1×1 layout, close apps | OpenCV player `python prototype/run.py --source video --file prototype/Videos/fire.mp4` |
| Mic blocked | Type in Voice HUD | Skip voice |
| Total crash | — | **Play backup recording**: "Here's the exact same system recorded earlier." |

---

## 7. Rehearsal Plan

1. **Run 1 — read-through:** each member reads their script, time it.
2. **Run 2 — handovers:** practise every handover line until smooth.
3. **Run 3 — full with mock judges:** a friend asks the questions in 4.3 *and* random ones; practise routing.
4. **Run 4 — failure drill:** kill the backend mid-demo on purpose and recover.
5. **Swap drill:** each member presents another member's section once (prepares for absences).

---

## 8. Team Cue Card (print one per member)

```
RAFAY  Hook → Problem → Solution → "Aqib, show them."
AQIB   Dashboard → fire → fight/gun → risk score → Incidents/SHA-256 → voice → "Moiz."
MOIZ   YOLOv8 + Pose + ByteTrack → 3 specialist models → 24–30 FPS async → "Areeba."
AREEBA Data cleaning/augment → two-stage verify + persistence → metrics → ethics → "Rafay."
RAFAY  Architecture → scaling/offline → roadmap → CLOSE (all step forward)
Q&A    Rafay routes · one voice at a time · ≤30 s · never invent numbers
FAIL   Rafay talks, Aqib fixes ≤20 s, else backup video
```
