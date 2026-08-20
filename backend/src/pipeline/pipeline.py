import os
import cv2
import logging
import numpy as np
from sqlalchemy.orm import Session

from src.detection.vehicle_detector import VehicleDetector
from src.tracking.deepsort_tracker import DeepSortTracker
from src.anpr.plate_recogniser import PlateRecogniser
from src.violations.violation_engine import ViolationEngine
from db.models import VehicleDetection, Violation

logger = logging.getLogger(__name__)

CLASS_NAME_MAP = {
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck"
}

class SurveillancePipeline:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "configs", "default.yaml"
        )
        logger.info(f"Initializing SurveillancePipeline with config: {self.config_path}")
        self.detector = VehicleDetector(self.config_path)
        self.tracker = DeepSortTracker(self.config_path)
        self.anpr = PlateRecogniser(self.config_path)
        self.violation_engine = ViolationEngine(self.config_path)

    def process_frame(
        self,
        frame: np.ndarray,
        frame_idx: int,
        camera_id: str = "CAM-01",
        light_status: str = None,
        db: Session = None,
        job_id: str = None
    ) -> dict:
        """
        Runs complete frame inference pipeline:
        Detection -> Tracking -> ANPR -> Violation Checks -> Database Persistence
        """
        if frame is None:
            return {"frame_idx": frame_idx, "camera_id": camera_id, "vehicles": [], "violations": []}

        h, w = frame.shape[:2]

        # 1. Vehicle Detection
        detections = self.detector.detect(frame)

        # 2. Multi-Object Tracking
        tracks = self.tracker.update(detections, frame=frame)

        processed_vehicles = []
        frame_violations = []

        for track in tracks:
            track_id = track.get("track_id")
            bbox = track.get("bbox", [0, 0, 0, 0])
            class_id = track.get("class_id", 2)
            conf = track.get("confidence", 0.0)

            vehicle_class = CLASS_NAME_MAP.get(class_id, "Vehicle")

            # Crop vehicle bounding box safely
            x1, y1, x2, y2 = [int(v) for v in bbox]
            crop_x1, crop_y1 = max(0, x1), max(0, y1)
            crop_x2, crop_y2 = min(w, x2), min(h, y2)
            
            vehicle_crop = None
            if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                vehicle_crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]

            # 3. ANPR Plate Recognition
            plate_number, plate_conf = ("UNKNOWN", 0.0)
            if vehicle_crop is not None and vehicle_crop.size > 0:
                plate_number, plate_conf = self.anpr.read_plate(vehicle_crop)

            # 4. Violation Evaluation
            track_info = {
                "track_id": track_id,
                "bbox": bbox,
                "class_id": class_id
            }
            violations_list, speed_kmh = self.violation_engine.evaluate(
                track_info, frame_idx=frame_idx, light_status=light_status, vehicle_crop=vehicle_crop
            )

            vehicle_data = {
                "track_id": track_id,
                "camera_id": camera_id,
                "vehicle_class": vehicle_class,
                "confidence": round(float(conf), 2),
                "bbox": [x1, y1, x2, y2],
                "plate_number": plate_number,
                "plate_confidence": round(float(plate_conf), 2),
                "speed_kmh": speed_kmh,
                "violations": violations_list
            }
            processed_vehicles.append(vehicle_data)

            # 5. Database Persistence (if db session provided)
            if db:
                try:
                    db_det = VehicleDetection(
                        camera_id=camera_id,
                        job_id=job_id,
                        track_id=int(track_id) if str(track_id).isdigit() else 1,
                        vehicle_class=vehicle_class,
                        confidence=float(conf),
                        plate_number=plate_number if plate_number != "UNKNOWN" else None,
                        plate_confidence=float(plate_conf) if plate_conf > 0 else None
                    )
                    db.add(db_det)
                    db.flush() # get db_det.id

                    for viol_type in violations_list:
                        db_viol = Violation(
                            detection_id=db_det.id,
                            violation_type=viol_type,
                            plate_number=plate_number if plate_number != "UNKNOWN" else None,
                            plate_confidence=float(plate_conf) if plate_conf > 0 else None
                        )
                        db.add(db_viol)
                        frame_violations.append({
                            "id": db_viol.id if hasattr(db_viol, 'id') else None,
                            "camera_id": camera_id,
                            "track_id": track_id,
                            "vehicle_class": vehicle_class,
                            "plate_number": plate_number,
                            "violation_type": viol_type,
                            "speed_kmh": speed_kmh
                        })
                    db.commit()
                except Exception as e:
                    logger.warning(f"Error persisting pipeline data to DB: {e}")
                    db.rollback()
            else:
                for viol_type in violations_list:
                    frame_violations.append({
                        "camera_id": camera_id,
                        "track_id": track_id,
                        "vehicle_class": vehicle_class,
                        "plate_number": plate_number,
                        "violation_type": viol_type,
                        "speed_kmh": speed_kmh
                    })

        return {
            "frame_idx": frame_idx,
            "camera_id": camera_id,
            "vehicles": processed_vehicles,
            "violations": frame_violations,
            "violations_count": len(frame_violations)
        }
