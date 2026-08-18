from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class VehicleDetection(Base):
    __tablename__ = 'vehicle_detections'

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, index=True)
    track_id = Column(Integer, index=True)
    vehicle_class = Column(String)
    confidence = Column(Float)
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
