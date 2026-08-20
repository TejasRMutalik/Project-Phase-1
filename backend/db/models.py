from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class VehicleDetection(Base):
    __tablename__ = 'vehicle_detections'

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, index=True)
    job_id = Column(String, ForeignKey('upload_jobs.id'), nullable=True, index=True)
    track_id = Column(Integer, index=True)
    vehicle_class = Column(String)
    confidence = Column(Float)
    plate_number = Column(String, index=True, nullable=True)
    plate_confidence = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Violation(Base):
    __tablename__ = 'violations'

    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(Integer, ForeignKey('vehicle_detections.id'))
    violation_type = Column(String, index=True) # e.g. NO_HELMET, SIGNAL_JUMP
    plate_number = Column(String, index=True, nullable=True)
    plate_confidence = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    video_evidence_path = Column(String, nullable=True)

class UploadJob(Base):
    __tablename__ = 'upload_jobs'

    id = Column(String, primary_key=True, index=True)
    filename = Column(String)
    status = Column(String, default="PENDING") # PENDING, PROCESSING, COMPLETED, FAILED
    progress = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

