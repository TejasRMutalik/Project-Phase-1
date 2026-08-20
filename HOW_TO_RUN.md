# How to Run Project Phase 1 — Traffic Surveillance System

Follow these steps to launch the complete AI pipeline backend and frontend dashboard:

### Step 1: Navigate to Backend Directory
```bash
cd "c:\mp\Project-Phase-1\backend"
```

### Step 2: Activate Virtual Environment
```powershell
.\venv\Scripts\activate
```

### Step 3: Run the FastAPI Server
Launch the server with live streaming and ML pipeline enabled:
```bash
python -m uvicorn main:app --reload
```

### Step 4: Open the Dashboard in Browser
Open your web browser (Chrome / Edge) and go to:
- **Live Surveillance Dashboard**: [http://localhost:8000/dashboard.html](http://localhost:8000/dashboard.html)
- **Offline Video Analysis**: [http://localhost:8000/video_analysis.html](http://localhost:8000/video_analysis.html)
- **System Settings & Config**: [http://localhost:8000/settings.html](http://localhost:8000/settings.html)

---

### Verification & Testing Scripts

- **Test Detection (YOLOv8)**: `python scripts/test_detect.py`
- **Test Tracking (DeepSORT)**: `python scripts/test_track.py`
- **Test ANPR (EasyOCR)**: `python scripts/test_anpr.py`
- **Run Full Pipeline**: `python scripts/run_pipeline.py`
- **Test REST APIs**: `python scripts/test_api.py`
