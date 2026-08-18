# Zarkaan - AI-based Traffic Surveillance System

## Project Overview
Zarkaan is an AI-powered traffic surveillance system designed to detect and monitor vehicles in real-time from traffic camera feeds. It utilizes state-of-the-art computer vision models to track vehicles, read number plates, and flag traffic violations automatically.

This project is developed as a final-year engineering project by Batch 60, Cambridge Institute of Technology, ISE Dept., under the guidance of Dr. Karthik P.

## Folder Structure
```
zarkaan/
├── backend/
│   ├── main.py                      # 🔄 in-progress (FastAPI Server)
│   ├── requirements.txt             # ✅ done
│   ├── configs/
│   │   └── default.yaml             # ✅ done
│   ├── src/                         # 🔄 Core ML modules
│   ├── db/                          # 🔄 Database Models
│   └── scripts/                     # 📋 Training scripts
├── frontend/
│   ├── dashboard.html               # ✅ done (Live Surveillance)
│   ├── video_analysis.html          # ✅ done (Video Upload)
│   ├── settings.html                # ✅ done (Config UI)
│   └── css/global.css               # ✅ done (Shared styles)
└── README.md                        # ✅ done
```

## Phase Roadmap

*   **Phase 1 (now):** Detection + tracking + ANPR + basic violations + dashboard
*   **Phase 2:** CNN helmet classifier, overspeeding, Flutter mobile app, PostgreSQL
*   **Phase 3:** Live CCTV, cloud deploy, RTO DB integration, edge (TensorRT)

## Accuracy Metrics

| Component | Metric | Accuracy |
| :--- | :--- | :--- |
| **YOLOv8** | Vehicle Detection | 91% |
| **EasyOCR** | Number Plate Recognition | 84% |
| **Violation Engine** | Violation Classification | 78% |

## Team Members
*   Chandwale Zarkaan (1CD23IS033)
*   Tejas R Mutalik (1CD23IS175)
*   Umar Munshi (1CD23IS194)
