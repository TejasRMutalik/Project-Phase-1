import os
import cv2
import yaml
import logging
import numpy as np
from sqlalchemy.orm import Session

from src.detection.vehicle_detector import VehicleDetector
from src.tracking.deepsort_tracker import DeepSortTracker
from src.anpr.plate_recogniser import PlateRecogniser
from src.anpr.plate_consensus import TrackLevelOCRConsensus
from src.pipeline.ratg_controller import RATGGovernor
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
    """
    RATG-OC (Risk-Adaptive Temporal Gating and Track-Level OCR Consensus) Pipeline:
    Supervisory scheduling layer wrapping YOLOv8, DeepSORT, and EasyOCR.
    """
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "configs", "default.yaml"
        )
        logger.info(f"Initializing RATG-OC SurveillancePipeline with config: {self.config_path}")
        self.detector = VehicleDetector(self.config_path)
        self.tracker = DeepSortTracker(self.config_path)
        self.anpr = PlateRecogniser(self.config_path)
        self.violation_engine = ViolationEngine(self.config_path)

        self._last_tracks = []
        self._load_ratg_config()

    def _load_ratg_config(self):
        cfg = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    cfg = yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Error loading config for RATG-OC: {e}")

        ratg_cfg = cfg.get("ratg_oc", {})
        self.ratg_enabled = ratg_cfg.get("enabled", True)

        self.governor = RATGGovernor(
            weights=ratg_cfg.get("weights", [0.25, 0.20, 0.25, 0.15, 0.15]),
            tau_d=ratg_cfg.get("tau_d", 0.5),
            tau_z=ratg_cfg.get("tau_z", 0.7),
            k_max=ratg_cfg.get("k_max", 4),
            hysteresis_delta=ratg_cfg.get("hysteresis_delta", 0.05),
            zone_distance=ratg_cfg.get("zone_distance", 150.0)
        )

        self.consensus_cache = TrackLevelOCRConsensus(
            tau_l=ratg_cfg.get("tau_l", 100.0),
            tau_c=ratg_cfg.get("tau_c", 2.0),
            stability_margin=ratg_cfg.get("stability_margin", 0.5),
            cache_limit=ratg_cfg.get("cache_limit", 10),
            alpha=ratg_cfg.get("alpha", 1.0),
            lambda_param=ratg_cfg.get("lambda_param", 0.5)
        )
        logger.info(f"RATG-OC initialized (enabled={self.ratg_enabled}, K_max={self.governor.k_max}, tau_d={self.governor.tau_d})")

    def reset(self):
        """Reset internal caches, governor stats, and tracking history."""
        self.governor.reset()
        self.consensus_cache = TrackLevelOCRConsensus(
            tau_l=self.consensus_cache.tau_l,
            tau_c=self.consensus_cache.tau_c,
            stability_margin=self.consensus_cache.stability_margin,
            cache_limit=self.consensus_cache.cache_limit
        )
        self._last_tracks = []

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
        Runs RATG-OC frame processing routine (Algorithm 1):
          1. Compute risk r_t via Eq. (1) and decide Primary Mode vs Propagate Mode (Eq. 2)
          2. Primary Mode: Run YOLOv8 detector D(I_t), update tracker T(B, I_t), t_D <- t
             Propagate Mode: Skip D, Kalman motion update T(empty, I_t)
          3. Selective OCR: If cache unresolved AND crop sharpness h_i >= tau_L:
             Run EasyOCR O(crop), append weighted vote (Eq. 3), update consensus (Eq. 4)
          4. Evaluate violation logic V(i, s_hat) unconditionally on every frame
          5. Return updated tracks, consensus plates, and violations
        """
        if frame is None:
            return {"frame_idx": frame_idx, "camera_id": camera_id, "vehicles": [], "violations": []}

        h, w = frame.shape[:2]
        stop_line_y = getattr(self.violation_engine, "stop_line_y", 250)
        mean_cov = self.tracker.get_mean_covariance_trace()

        # 1. Risk Governor & Gating Decision (Eq. 1 & Eq. 2)
        if self.ratg_enabled:
            risk_score, factors, should_detect = self.governor.evaluate_risk(
                frame=frame,
                frame_idx=frame_idx,
                tracks=self._last_tracks,
                mean_cov_trace=mean_cov,
                stop_line_y=stop_line_y,
                consensus_cache=self.consensus_cache
            )
            mode = "PRIMARY" if should_detect else "PROPAGATE"
        else:
            should_detect = True
            mode = "PRIMARY"
            risk_score = 1.0
            factors = {"d_t": 1.0, "u_t": 0.0, "z_t": 0.0, "a_t": 1.0, "q_t": 1.0, "r_t": 1.0}

        # 2. Vehicle Detection & Multi-Object Tracking
        if should_detect:
            # Primary Mode: full detection forward pass
            detections = self.detector.detect(frame)
            tracks = self.tracker.update(detections, frame=frame)
        else:
            # Propagate Mode: bypass detector entirely, advance active Kalman tracks
            tracks = self.tracker.update([], frame=frame)

        self._last_tracks = tracks

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

            # 3. Selective OCR and Temporal Consensus (Section III-B)
            # Check velocity continuity to mitigate identity swaps
            self.consensus_cache.update_velocity_and_check_swap(track_id, bbox, frame_idx)

            plate_number, plate_conf, is_locked = self.consensus_cache.get_plate(track_id)
            ocr_invoked = False

            # Only invoke OCR if plate is unresolved and crop meets Laplacian blur threshold
            if not is_locked and vehicle_crop is not None and vehicle_crop.size > 0:
                sharpness = self.consensus_cache.compute_laplacian_sharpness(vehicle_crop)
                if sharpness >= self.consensus_cache.tau_l:
                    ocr_invoked = True
                    cand_text, cand_conf = self.anpr.read_plate(vehicle_crop)
                    if cand_text != "UNKNOWN" and cand_conf > 0:
                        plate_number, plate_conf, is_locked = self.consensus_cache.add_candidate(
                            track_id=track_id,
                            text=cand_text,
                            confidence=cand_conf,
                            crop=vehicle_crop
                        )

            # 4. Violation Evaluation (Unconditional on every frame)
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
                "plate_locked": is_locked,
                "ocr_invoked": ocr_invoked,
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

        tot_frames = max(1, self.governor.stats["total_frames"])
        primary_pct = round((self.governor.stats["primary_frames"] / tot_frames) * 100.0, 1)

        return {
            "frame_idx": frame_idx,
            "camera_id": camera_id,
            "ratg_mode": mode,
            "risk_score": round(float(risk_score), 3),
            "gating_factors": factors,
            "detector_triggered": should_detect,
            "primary_frames_pct": primary_pct,
            "vehicles": processed_vehicles,
            "violations": frame_violations,
            "violations_count": len(frame_violations)
        }
