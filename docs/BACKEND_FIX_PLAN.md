# Backend Fix Plan

Formerly `BACKEND_WIRING_ROADMAP.md`. That roadmap's M0-M9 got implemented, but an audit (2026-08-19) found several milestones were only superficially done — code existed but didn't do what it claimed. This doc tracks what's actually fixed vs. still outstanding, and the frontend work layered on top.

## 00. Scope & constraint

Same as before: no layout/CSS/structure changes to `dashboard.html`, `video_analysis.html`, `settings.html` beyond the minimum markup needed to carry real data. Small new elements (a table row, a stat id) are fine when a feature genuinely needs them — full redesigns are not.

## 01. Audit findings (2026-08-19) — status

| Item | Original claim | Audit finding | Status |
|---|---|---|---|
| M0 Environment | weights + sample clip + test script | Confirmed present, detection runs | ✅ DONE |
| M1 Database | engine + session + init_db | Confirmed, `zarkaan.db` populated | ✅ DONE |
| M2 Detection | real YOLOv8 parse + filter | Confirmed, called from pipeline | ✅ DONE |
| M3 Tracking | real DeepSORT | Confirmed, `update_tracks()` wired | ✅ DONE |
| M4 ANPR | EasyOCR + confidence gate | OCR real, but confidence-threshold branch was dead code — both paths returned the same result regardless of threshold | ⚠️ BUG — see below |
| M5 Violations | speed calc, signal-line RED/GREEN timer, helmet heuristic | Speed calc real. Signal light hardcoded `"RED"` forever in `main.py` — no timer, so signal-jump can never fire. Helmet check still `if motorcycle: return False`, unchanged from the pre-wiring mock | ❌ NOT DONE (helmet), ❌ NOT DONE (signal timer) |
| M6 Pipeline | chains detect→track→ANPR→violations→DB | Confirmed, `SurveillancePipeline.process_frame()` | ✅ DONE |
| M7 API surface | all 7 contract endpoints, router split | `/api/status`, `/api/config`, `/api/upload_video`, `/api/jobs/{id}` real. Missing: `/api/jobs/{id}/results` (frontend was hitting global `/api/violations` instead), CSV export route (didn't exist at all — download button was decorative), `/ws/jobs/{id}` (upload page polls REST instead, functionally fine). Router split never happened, still one `main.py` | ⚠️ PARTIAL |
| M8 Frontend swap | delete `Math.random()`, wire real fetch/WS | `video_analysis.html` correctly wired. `dashboard.html`'s WebSocket wiring real, but `updateFPS()` was still `Math.random()` on its own `setInterval`, running 24/7 regardless of the real feed. Orphaned `simulateDetection()` left in the file, unused but not deleted | ⚠️ PARTIAL |
| M9 Demo prep | run script, real measured numbers | `HOW_TO_RUN.md` skips `pip install` step. No measured FPS/OCR-hit-rate/accuracy numbers written down anywhere | ❌ NOT DONE |

## 02. Fixed in this pass (2026-08-19)

New feature: uploaded videos now show up on the dashboard, both live while processing and afterward in a recent-uploads list.

- **`db/models.py`** — `VehicleDetection.job_id` (FK to `upload_jobs.id`, nullable) added, so detections/violations can be scoped to the upload job that produced them.
- **`db/session.py`** — `init_db()` patches the column into the existing `zarkaan.db` in place (`ALTER TABLE ... ADD COLUMN`) since there's no migration tool for this single-file SQLite dev DB.
- **`src/pipeline/pipeline.py`** — `process_frame()` takes `job_id` and stamps it on every `VehicleDetection` row it writes.
- **`main.py`**:
  - `process_uploaded_video_job` passes `job_id` through to the pipeline and broadcasts each processed frame to the same `/ws/live` connections the dashboard already listens on (`asyncio.run_coroutine_threadsafe`, since the background task runs in a worker thread, not the event loop) — this is the "video upload updates the dashboard live" behavior.
  - `GET /api/jobs?limit=4` — latest N uploaded files with vehicle/violation summary counts. Powers the dashboard's recent-uploads panel.
  - `GET /api/jobs/{job_id}/results` — detections/violations scoped to one job. Fixes the M7 gap and the video_analysis.html bug where "results" were actually the global violations table, not that job's.
- **`dashboard.html`** — new "RECENT UPLOADS" panel (reuses existing `.panel`/`.panel-header`/`.badge` classes, no new CSS), polls `/api/jobs?limit=4` every 5s.
- **`video_analysis.html`** — results section (`342`/`12`/`289`) was hardcoded static numbers; now pulls real counts from `/api/jobs/{id}/results`.

Verified: backend imports clean, migration runs against the real `zarkaan.db` without data loss, both new endpoints return correct JSON against the one existing upload job in the DB.

Known limitation carried forward: `plate_number` is only persisted on `Violation` rows, not on every `VehicleDetection` — so "plates read" counts only reflect plates seen on flagged vehicles, not the true total. Would need a schema change (store plate on every detection) to fix properly; noted, not done in this pass.

## 03. Fixed in pass 2 (2026-08-19, same day)

- **ANPR confidence gate** (`plate_recogniser.py:111-114`) — dead branch removed; a read below `anpr.confidence_threshold` now actually returns `"UNKNOWN"` instead of the raw low-confidence text.
- **Signal-jump timer** — `ViolationEngine` now owns a real wall-clock RED/GREEN cycle (`get_current_light_status()`), config keys `violations.signal_red_seconds` / `signal_green_seconds` (default 10/10s). `main.py` no longer hardcodes `light_status="RED"`; verified the timer actually flips RED→GREEN over time.
- **CSV export** — `GET /api/jobs/{job_id}/report.csv` implemented for real (streams violation rows). `video_analysis.html` results header didn't even have a download button before — added one, wired to the real endpoint.
- **Dashboard FPS counter** — was `Math.random()` on its own timer. `/ws/live` now computes real inter-frame FPS server-side and sends it in the payload; `dashboard.html` displays that instead.
- **Dead code removed from `dashboard.html`** — orphaned `simulateDetection()`, `generatePlate()`, and the fake-data constant arrays (`vehicleClasses`, `platePrefixes`, `plateChars`, `violationTypes`) it alone used.

Verified: backend still imports clean, server boots, CSV endpoint returns 200 with correct headers, signal timer confirmed flipping RED→GREEN in a standalone check.

## 04. Model training — deferred, plan locked in

Current detector (`yolov8n.pt`), tracker embedder, and OCR are all stock pretrained weights — never trained on this project's own data. `backend/scripts/train_yolov8.py` is decorative (its own comments say "Fake import to simulate YOLO" / "Fake training loop") — not wired to anything, does not actually train.

Decision: real training happens later on a separate laptop with a dedicated GPU. Until then:

1. **Dataset** — bootstrap from IDD (Indian Driving Dataset) vehicle subset — closest domain match to the sample footage (has an auto-rickshaw class COCO lacks). Fine-tune further on the project's own camera footage once labeled, if needed.
2. **Method** — transfer learning from `yolov8n.pt`, not from scratch (`YOLO('yolov8n.pt').train(data='data.yaml', epochs=50-100, imgsz=640)`). COCO already knows vehicle-shaped objects, so this needs far less data/compute than training cold.
3. **Compute** — GPU laptop (not yet available). CPU training on this machine was ruled out as impractical.
4. **Validation** — ultralytics reports real mAP50/precision/recall on the val split; those numbers replace the report's aspirational 91%/84%/78%.
5. **Deploy** — swap `model.yolo_weights` in `default.yaml` to the new `best.pt`, no other code changes needed.

Everything else in this doc is being finished first, so training is the last step once the GPU laptop is available.

## 05. Fixed in pass 3 (2026-08-19, same day) — everything not dependent on the user

- **`plates_read` undercount fixed** — `VehicleDetection` now has its own `plate_number`/`plate_confidence` columns (migrated into `zarkaan.db` in place), set on every detection, not just flagged ones. `/api/jobs`, `/api/jobs/{id}/results` updated to count off real per-detection data instead of the violation-only proxy.
- **Router split done** — `main.py` is now a thin bootstrap (app creation, CORS, startup event, router registration, static mount). Real routes moved to `src/api/routes_live.py` (`/api/status`, `/api/violations`, `/ws/live`), `src/api/routes_upload.py` (`/api/upload_video`, `/api/jobs*`), `src/api/routes_config.py` (`/api/config`). Shared state (`pipeline`, `MAIN_LOOP`, the WebSocket `ConnectionManager`) moved to `src/api/shared.py` so routers can reach it without circular imports. Deleted `src/api/stream_server.py` in the process — another decorative fake file (`"""simulated"""` WebSocket loop, never wired to anything).
- **Real FPS/OCR numbers measured** (`scripts/benchmark.py`, new) — ran the full sample clip through the real pipeline:
  - **3.62 FPS** on CPU (expected — no GPU on this machine; matches the "Using CPU" warning EasyOCR/torch already logs)
  - **339 vehicles detected** across 377 frames
  - **0 plates read, 0.0% OCR hit-rate**

Verified: backend re-imports clean, all 7 REST routes plus the CSV/results endpoints return 200 through the new router split, migration confirmed adding `plate_number`/`plate_confidence` columns without data loss.

### 0% OCR hit-rate — root cause, not a bug

Traced it: `assets/sample_traffic.mp4` is a wide/overhead-angle stock clip. A detected vehicle box at frame 100 measured **115×72px** in a 768×432 frame — the plate region inside that crop is roughly 20px tall. No OCR model reads text that small; `test_anpr.py` confirms every plate read on this clip returns `UNKNOWN`, consistently, not intermittently. This is a camera-distance/resolution problem with the current demo clip, not a `plate_recogniser.py` defect — the code path (locate plate → EasyOCR → threshold gate) all worked correctly, there's just no legible text in the input. `scripts/fetch_sample.py` pulled this clip from a generic public source list, not one chosen for plate legibility.

Real fix needs a closer-angle or higher-resolution traffic clip — a content/sourcing decision, flagged for the user rather than auto-swapped.

## 06. Still outstanding

- **Helmet detection** — still the pre-wiring placeholder (`if motorcycle: return False`). Blocked on the training path in section 04 (needs labeled data + GPU) — stays an honest, commented placeholder until then.
- **Sample clip swap for legible plates** — needs a traffic clip with closer/higher-res vehicle framing; the current 0% OCR hit-rate is a clip problem, not a code problem (see above). User call — sourcing footage.
- **M9 detection-accuracy number** — FPS/OCR now measured and honest (3.62 FPS, 0% hit-rate pending a better clip); a real mAP/accuracy number still needs the training pass in section 04.

## 07. Demo & report prep checklist

- [x] Sample clip runs through the full pipeline without crashing, start to finish (confirmed via `scripts/benchmark.py`, 377/377 frames)
- [x] Dashboard shows real detections live, with no visible layout change from today's version
- [x] Upload page: real file in, real progress, real job-scoped results table
- [x] Upload page: real CSV out
- [ ] Settings page: change confidence threshold, save, restart, confirm it persisted
- [x] Signal-jump can fire (real RED/GREEN timer) — no-helmet still blocked on training
- [ ] Screenshots captured for the report's backend deep-dive chapter
- [x] Real FPS/OCR-hit-rate written down honestly (3.62 FPS, 0% OCR hit-rate — traced to clip quality, see section 05)
- [ ] Real detection-accuracy number — waits on the training pass in section 04
