import os
import uuid
import csv
import io
import asyncio
import logging

import cv2
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session

from db.session import get_db, SessionLocal
from db.models import VehicleDetection, Violation, UploadJob
from src.pipeline.pipeline import SurveillancePipeline
from src.api.shared import CONFIG_PATH, UPLOAD_DIR
from src.api import shared

logger = logging.getLogger("ProjectPhase1")
router = APIRouter()


def process_uploaded_video_job(job_id: str, file_path: str):
    """Background task to process uploaded video with SurveillancePipeline."""
    db = SessionLocal()
    try:
        job = db.query(UploadJob).filter(UploadJob.id == job_id).first()
        if not job:
            return
        job.status = "PROCESSING"
        db.commit()

        cap = cv2.VideoCapture(file_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1

        local_pipeline = SurveillancePipeline(CONFIG_PATH)
        fidx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            fidx += 1
            result = local_pipeline.process_frame(
                frame, frame_idx=fidx, camera_id="UPLOAD-CAM", db=db, job_id=job_id
            )
            if shared.MAIN_LOOP:
                asyncio.run_coroutine_threadsafe(shared.manager.broadcast(result), shared.MAIN_LOOP)
            if fidx % 10 == 0:
                job.progress = round((fidx / total_frames) * 100.0, 1)
                db.commit()

        cap.release()
        job.status = "COMPLETED"
        job.progress = 100.0
        db.commit()
    except Exception as e:
        logger.error(f"Error processing upload job {job_id}: {e}")
        job.status = "FAILED"
        db.commit()
    finally:
        db.close()


def save_thumbnail(job_id: str, file_path: str) -> None:
    """Grab the first frame as a JPEG preview. Cheap - runs before the
    background job even starts, so a thumbnail exists immediately."""
    cap = cv2.VideoCapture(file_path)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return
    thumb_path = os.path.join(UPLOAD_DIR, f"{job_id}_thumb.jpg")
    cv2.imwrite(thumb_path, frame)


@router.post("/api/upload_video")
async def upload_video(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload video file for async pipeline analysis."""
    job_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    save_thumbnail(job_id, file_path)

    job = UploadJob(id=job_id, filename=file.filename, status="PENDING", progress=0.0)
    db.add(job)
    db.commit()

    background_tasks.add_task(process_uploaded_video_job, job_id, file_path)

    return {"job_id": job_id, "filename": file.filename, "status": "PENDING", "message": "Video received. Processing queued."}


@router.get("/api/jobs/{job_id}/thumbnail")
async def get_job_thumbnail(job_id: str, db: Session = Depends(get_db)):
    """First-frame JPEG preview for a job, used by the dashboard's Recent Uploads panel."""
    job = db.query(UploadJob).filter(UploadJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    thumb_path = os.path.join(UPLOAD_DIR, f"{job_id}_thumb.jpg")
    if not os.path.isfile(thumb_path):
        raise HTTPException(status_code=404, detail="Thumbnail not available")

    return FileResponse(thumb_path, media_type="image/jpeg")


@router.get("/api/jobs/{job_id}/video")
async def get_job_video(job_id: str, db: Session = Depends(get_db)):
    """The originally uploaded video file, used to play real footage on the
    dashboard's main feed / mini-cams instead of the demo clips."""
    job = db.query(UploadJob).filter(UploadJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    file_path = os.path.join(UPLOAD_DIR, f"{job_id}_{job.filename}")
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Video file not available")

    return FileResponse(file_path, media_type="video/mp4")


@router.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get upload job status."""
    job = db.query(UploadJob).filter(UploadJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "filename": job.filename,
        "status": job.status,
        "progress": job.progress,
        "created_at": job.created_at.isoformat() if job.created_at else None
    }


@router.get("/api/jobs")
async def list_jobs(limit: int = 4, db: Session = Depends(get_db)):
    """Latest uploaded files with detection/violation summary counts."""
    jobs = db.query(UploadJob).order_by(UploadJob.created_at.desc()).limit(limit).all()
    result = []
    for job in jobs:
        vehicle_count = db.query(VehicleDetection).filter(VehicleDetection.job_id == job.id).count()
        violation_count = (
            db.query(Violation)
            .join(VehicleDetection, Violation.detection_id == VehicleDetection.id)
            .filter(VehicleDetection.job_id == job.id)
            .count()
        )
        result.append({
            "id": job.id,
            "job_id": job.id,
            "filename": job.filename,
            "status": job.status,
            "progress": job.progress,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "vehicles_detected": vehicle_count,
            "violations_flagged": violation_count,
            "thumbnail_url": f"/api/jobs/{job.id}/thumbnail",
            "video_url": f"/api/jobs/{job.id}/video"
        })
    return result


@router.get("/api/jobs/{job_id}/results")
async def get_job_results(job_id: str, db: Session = Depends(get_db)):
    """Detections + violations for one specific upload job."""
    job = db.query(UploadJob).filter(UploadJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    detections = db.query(VehicleDetection).filter(VehicleDetection.job_id == job_id).all()
    detection_ids = [d.id for d in detections]
    violations = (
        db.query(Violation).filter(Violation.detection_id.in_(detection_ids)).all()
        if detection_ids else []
    )
    plates_read = sum(1 for d in detections if d.plate_number)

    violation_rows = []
    for v in violations:
        det = next((d for d in detections if d.id == v.detection_id), None)
        violation_rows.append({
            "timestamp": v.timestamp.isoformat() if v.timestamp else None,
            "violation_type": v.violation_type,
            "vehicle_class": det.vehicle_class if det else "Vehicle",
            "plate_number": v.plate_number or "UNKNOWN",
            "plate_confidence": v.plate_confidence
        })

    return {
        "job_id": job.id,
        "filename": job.filename,
        "status": job.status,
        "vehicles_detected": len(detections),
        "violations_flagged": len(violations),
        "plates_read": plates_read,
        "violations": violation_rows
    }


@router.get("/api/jobs/{job_id}/report.csv")
async def get_job_report_csv(job_id: str, db: Session = Depends(get_db)):
    """Real CSV export of a job's violation rows."""
    job = db.query(UploadJob).filter(UploadJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    detections = db.query(VehicleDetection).filter(VehicleDetection.job_id == job_id).all()
    detection_ids = [d.id for d in detections]
    violations = (
        db.query(Violation).filter(Violation.detection_id.in_(detection_ids)).all()
        if detection_ids else []
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["timestamp", "violation_type", "vehicle_class", "plate_number", "plate_confidence"])
    for v in violations:
        det = next((d for d in detections if d.id == v.detection_id), None)
        writer.writerow([
            v.timestamp.isoformat() if v.timestamp else "",
            v.violation_type,
            det.vehicle_class if det else "Vehicle",
            v.plate_number or "UNKNOWN",
            v.plate_confidence or ""
        ])

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=job_{job_id}_report.csv"}
    )
