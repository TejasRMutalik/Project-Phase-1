# System Improvement and Presentation Readiness Plan
## Project Phase 1: RATG-OC AI-based Traffic Surveillance System

**Document Version:** 1.0.0  
**Authors:** Chandwale Zarkaan, Tejas R Mutalik, Umar Munshi  
**Guide:** Dr. Karthik P, Cambridge Institute of Technology, ISE Dept.  
**Date:** October 2026  

---

## 1. Executive Summary & Audit Overview

This document outlines the comprehensive roadmap to transform the **Project Phase 1 Traffic Surveillance System** from its current prototype state into a production-grade, highly polished, and presentation-ready academic and technical demonstration.

### Current System Status
* **Backend Architecture:** Modularized into FastAPI routers (`routes_live.py`, `routes_upload.py`, `routes_config.py`), backed by SQLite (`zarkaan.db`) and SQLAlchemy ORM.
* **Supervisory Algorithm (RATG-OC):** Mathematically implemented in `src/pipeline/ratg_controller.py` and `src/anpr/plate_consensus.py`, following equations from the IEEE conference research paper (`research_paper.tex`).
* **Frontend:** Built with Next.js 16 + React 19 + TailwindCSS, replacing the previous legacy HTML static files.

### Identified Critical Deficiencies Before Presentation
1. **Unannotated Video Loop on Dashboard:** The home page video player plays an unannotated stock MP4 loop while WebSocket metadata scrolls separately in a table. It lacks drawn bounding boxes, tracking labels, and speed tags directly on the video.
2. **GPU Training Status:** Model weights (`backend/weights/yolov8n.pt`) are off-the-shelf COCO weights. Custom training on Indian driving data (including auto-rickshaws) has not been performed. Local training is blocked due to hardware constraints (Intel UHD 620 GPU, 7.3 GB free disk space).
3. **0% ANPR Recognition on Wide Clip:** On `sample_traffic.mp4`, vehicles are distant (~20px plate height), resulting in `UNKNOWN` plates across the board.
4. **Startup & Documentation Disconnect:** `start_demo.bat` only starts the backend; `HOW_TO_RUN.md` refers to outdated static HTML endpoints.
5. **UI Gaps:** Initial stats are hardcoded constants (e.g. 1402, 1185), traffic signal states lack visual cues, and violation evidence snapshots are missing.

---

## 2. Workstream 1: Live Video Feed & Camera Overhaul

### 2.1 The Problem
* The frontend `<video>` tag plays `/assets/videos/sample_traffic.mp4` locally in the browser.
* The backend reads the video separately with OpenCV and emits bounding box JSON over `/ws/live`.
* Because the video is not visually annotated, evaluators cannot see the AI detecting vehicles.
* Sub-camera buttons (CAM-02, CAM-03) link to external Mixkit CDN clips unrelated to the pipeline, while CAM-04 and CAM-05 are blank.

### 2.2 Action Steps
* [ ] **Step 1.1: Implement Live Annotated MJPEG Streaming Route**
  * Create an endpoint `/api/live_stream` in `backend/src/api/routes_live.py`.
  * For each frame processed by `SurveillancePipeline`:
    * Draw bounding boxes using `cv2.rectangle` (Cyan for compliant, Red for violations).
    * Draw tracking ID, vehicle classification, and speed badge (`cv2.putText`).
    * Overlay consensus license plate string above the vehicle box.
    * Encode frame to JPEG (`cv2.imencode('.jpg', frame)`) and yield via `StreamingResponse(..., media_type="multipart/x-mixed-replace; boundary=frame")`.
* [ ] **Step 1.2: Upgrade Dashboard Video Display Component**
  * In `frontend/src/app/page.tsx`, support dual modes:
    1. **AI Annotated Feed (Default):** Stream from `http://localhost:8000/api/live_stream`.
    2. **Canvas HUD Overlay:** Render bounding box vectors on top of raw HTML5 video.
  * Provide a toggle button: `[Annotated Stream] | [Raw Camera View]`.
* [ ] **Step 1.3: Add Interactive Webcam Demonstration Mode**
  * Add a source switch in the backend pipeline: `source="0"` for live laptop webcam.
  * Allows live testing during presentations (e.g., detecting toy cars, physical signs, or phone screens).
* [ ] **Step 1.4: Rationalize Camera Selector Bar**
  * Replace dead/external stock URLs with structured presets:
    * `CAM-01: Main Intersection (Sample Clip 1)`
    * `CAM-02: Close-Up Traffic (High ANPR Legibility)`
    * `CAM-03: Live Laptop Webcam (Interactive Demo)`
    * `CAM-04: Offline Batch Upload Feed`

---

## 3. Workstream 2: GPU Training & Indian Traffic Domain Adaptation

### 3.1 Hardware Reality & Constraints
* **Local Laptop Specs:** Intel(R) UHD Graphics 620 (integrated), 0 NVIDIA CUDA cores, PyTorch `torch.cuda.is_available() == False`.
* **Disk Space:** 7.3 GB free on drive `C:`. Full IDD Detection dataset requires 22.8 GB.
* **Conclusion:** Model fine-tuning must be executed on cloud infrastructure (Google Colab).

### 3.2 Action Steps
* [ ] **Step 2.1: Prepare Google Colab Training Notebook**
  * Create a standalone notebook `notebooks/YOLOv8_Indian_Traffic_FineTune.ipynb`.
  * Connect to free NVIDIA Tesla T4 GPU (15 GB VRAM).
  * Environment setup:
    ```bash
    pip install ultralytics roboflow
    ```
* [ ] **Step 2.2: Acquire Indian Traffic Dataset**
  * Sourced via Roboflow Universe or IDD vehicle subset with 5 target classes:
    1. `car` (Class 0)
    2. `motorcycle` (Class 1)
    3. `bus` (Class 2)
    4. `truck` (Class 3)
    5. `autorickshaw` (Class 4)
* [ ] **Step 2.3: Execute Transfer Learning**
  * Fine-tune from `yolov8n.pt`:
    ```python
    from ultralytics import YOLO
    model = YOLO('yolov8n.pt')
    results = model.train(
        data='traffic_data.yaml',
        epochs=50,
        imgsz=640,
        batch=16,
        device=0,
        name='yolov8n_indian_traffic'
    )
    ```
* [ ] **Step 2.4: Export Metrics & Artifacts**
  * Save training loss curves, mAP@0.5, Precision-Recall curves, and confusion matrix images to `docs/training_results/`.
  * Download `best.pt` (~6.2 MB).
* [ ] **Step 2.5: Deploy Model to Project Backend**
  * Save model checkpoint to `backend/weights/best.pt`.
  * Update `backend/configs/default.yaml`:
    ```yaml
    model:
      yolo_weights: "weights/best.pt"
      classes: [0, 1, 2, 3, 4]
    ```
  * Update `CLASS_NAME_MAP` in `backend/src/pipeline/pipeline.py`:
    ```python
    CLASS_NAME_MAP = {
        0: "Car",
        1: "Motorcycle",
        2: "Bus",
        3: "Truck",
        4: "Autorickshaw"
    }
    ```

---

## 4. Workstream 3: License Plate Recognition (Resolving 0% OCR)

### 4.1 The Problem
* The stock video `sample_traffic.mp4` captures vehicles from a distant elevated angle.
* Plate regions are roughly 20px wide, causing EasyOCR to fail confidence gates and return `UNKNOWN`.
* Presenting an ANPR dashboard where all plates show `UNKNOWN` weakens the demo.

### 4.2 Action Steps
* [ ] **Step 3.1: Procure High-Legibility Demo Clip**
  * Source a close-angle video clip (`backend/assets/anpr_demo_traffic.mp4`) where plates occupy at least 60×25 pixels.
* [ ] **Step 3.2: Verify RATG-OC Consensus Cache in Action**
  * Demonstrate that:
    1. Low-sharpness crops are rejected by Laplacian filter (&tau;<sub>L</sub> = 100).
    2. Sharp crops are voted into the track candidate buffer.
    3. The plate locks with a green `[LOCKED]` badge when consensus weight exceeds &tau;<sub>C</sub> = 2.0.
* [ ] **Step 3.3: Expose Consensus Details in UI**
  * Display voting candidate count and cluster weight next to identified plates in the live table.

---

## 5. Workstream 4: UI/UX Modernization & Presentation Polish

### 5.1 Action Steps
* [ ] **Step 4.1: Connect Dynamic Database KPIs**
  * Remove hardcoded initial state values (`1402`, `1185`, `87`) in `frontend/src/app/page.tsx`.
  * On mount, fetch `/api/status` and `/api/violations` to compute true historical totals.
* [ ] **Step 4.2: Add Live Traffic Signal State Indicator**
  * Render an animated Red/Green light widget in the dashboard header or video HUD.
  * Matches `violation_engine.get_current_light_status()`, providing visual justification when a `SIGNAL_JUMP` violation is triggered.
* [ ] **Step 4.3: Build Infraction Evidence Modal**
  * Allow clicking any violation row in the table.
  * Opens a modal displaying:
    * Vehicle crop thumbnail
    * Detected plate string & confidence
    * Timestamp and camera ID
    * Measured speed vs speed limit
    * Violation classification badge
* [ ] **Step 4.4: Enhance Video Analysis (Offline Upload) Page**
  * Enable processed video playback with bounding boxes for uploaded batch files.
  * Provide one-click CSV report export.
* [ ] **Step 4.5: Add Settings Presets**
  * Add quick-configuration buttons on `frontend/src/app/settings/page.tsx`:
    * **Demo / Presentation Mode:** Balanced settings, visible bounding boxes, high responsiveness.
    * **High Throughput (Edge Mode):** Higher gating threshold (&tau;<sub>D</sub> = 0.7), K<sub>max</sub> = 6.
    * **Strict Enforcement Mode:** Lower thresholds, mandatory detector passes.

---

## 6. Workstream 5: Launcher & Documentation Alignment

### 6.1 Action Steps
* [ ] **Step 5.1: Create Unified Startup Script (`run_all.bat`)**
  * Launches FastAPI backend on `http://localhost:8000`.
  * Launches Next.js frontend on `http://localhost:3000`.
  * Opens default browser to `http://localhost:3000`.
* [ ] **Step 5.2: Update README.md & HOW_TO_RUN.md**
  * Update instructions to reflect the modern Next.js + FastAPI dual architecture.
  * Document all API routes, WebSocket protocols, and verification test scripts.

---

## 7. Viva Defense & Presentation Q&A Preparation

### Expected Questions & Recommended Responses

**Q1: Did you train YOLOv8 from scratch?**
> *"No. Training object detection backbones from scratch requires millions of annotated images and hundreds of GPU hours. We utilized transfer learning starting from YOLOv8n pretrained on COCO, and fine-tuned on an Indian driving dataset to incorporate domestic vehicle classes such as auto-rickshaws. Furthermore, our core research contribution (RATG-OC) is a supervisory scheduling layer that gates inference dynamically, not a new neural network architecture."*

**Q2: What is the primary novelty of RATG-OC?**
> *"Standard surveillance systems run heavy detection and OCR models on every frame at fixed rates, wasting compute on static scenes and motion-blurred crops. RATG-OC introduces a multi-factor risk governor that evaluates scene dynamics, tracker covariance, and enforcement line proximity. It runs YOLOv8 only on high-risk frames while propagating tracks via Kalman filters during low-risk frames, reducing detector calls by over 56% while maintaining tracking accuracy."*

**Q3: How does the Track-Level OCR Consensus work?**
> *"Single-frame OCR is vulnerable to glare, blur, and oblique camera angles. Instead of accepting single-frame predictions, RATG-OC filters crops using a Laplacian sharpness threshold, weights character strings using a Levenshtein-distance clustering algorithm, and locks the final plate only when a candidate cluster achieves statistical consensus across consecutive frames."*

**Q4: Why does the system run on CPU here?**
> *"The backend is architected to be edge-compatible. Because RATG-OC cuts full detector forward passes by more than half and suppresses redundant OCR inferences by ~72%, the pipeline achieves real-time throughput even on resource-constrained edge devices and standard CPU hardware."*

---

## 8. Execution Timeline & Next Steps

1. **Phase A (Immediate):** Implement `/api/live_stream` annotated video route and update dashboard player.
2. **Phase B (Frontend Polish):** Connect live traffic signal widget, real database stats, and violation evidence viewer.
3. **Phase C (Model & Data):** Run Colab training notebook for Indian traffic dataset; download and wire `best.pt`.
4. **Phase D (Integration & Review):** Build `run_all.bat`, update documentation, and perform full dry-run presentation.
