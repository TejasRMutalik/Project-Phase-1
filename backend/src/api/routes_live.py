import os
import time
import asyncio
import logging

import cv2
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from db.session import get_db, SessionLocal
from db.models import Violation, VehicleDetection
from src.api import shared

logger = logging.getLogger("ProjectPhase1")
router = APIRouter()

SAMPLE_VIDEO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "sample_traffic.mp4"
)


@router.get("/api/status")
async def get_status():
    """System operational status endpoint."""
    return {
        "status": "operational",
        "active_cameras": 1,
        "version": "1.0.0",
        "ml_engine": "YOLOv8 + DeepSORT + EasyOCR",
        "scheduling_governor": "RATG-OC (Risk-Adaptive Temporal Gating)",
        "gating_enabled": getattr(shared.pipeline, "ratg_enabled", True) if shared.pipeline else True
    }


@router.get("/api/violations")
async def get_violations(db: Session = Depends(get_db)):
    """Retrieve recorded violations from database."""
    violations = db.query(Violation).order_by(Violation.timestamp.desc()).all()
    results = []
    for v in violations:
        det = db.query(VehicleDetection).filter(VehicleDetection.id == v.detection_id).first()
        results.append({
            "id": v.id,
            "detection_id": v.detection_id,
            "violation_type": v.violation_type,
            "plate_number": v.plate_number or "UNKNOWN",
            "plate_confidence": v.plate_confidence,
            "vehicle_class": det.vehicle_class if det else "Vehicle",
            "camera_id": det.camera_id if det else "CAM-01",
            "timestamp": v.timestamp.isoformat() if v.timestamp else None
        })
    return results


@router.websocket("/ws/live")
async def websocket_live_feed(websocket: WebSocket):
    """Live WebSocket feed pushing pipeline inferences to dashboard."""
    await shared.manager.connect(websocket)

    db = SessionLocal()
    try:
        while True:
            cap = cv2.VideoCapture(SAMPLE_VIDEO)
            fidx = 0
            last_frame_time = time.time()
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                fidx += 1
                if shared.pipeline:
                    result = shared.pipeline.process_frame(frame, frame_idx=fidx, camera_id="CAM-01", db=db)
                    now = time.time()
                    result["fps"] = round(1.0 / max(now - last_frame_time, 1e-6), 1)
                    last_frame_time = now
                    await websocket.send_json(result)
                await asyncio.sleep(0.05)  # ~20 FPS loop for real-time live preview
            cap.release()
    except WebSocketDisconnect:
        shared.manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket live feed ended: {e}")
        shared.manager.disconnect(websocket)
    finally:
        db.close()
