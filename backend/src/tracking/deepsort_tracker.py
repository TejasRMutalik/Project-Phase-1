import os
import logging
import yaml
import numpy as np

try:
    from deep_sort_realtime.deepsort_tracker import DeepSort
except ImportError:
    DeepSort = None

logger = logging.getLogger(__name__)

class DeepSortTracker:
    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.max_age = 30
        self.n_init = 2 # 2 consecutive frames to confirm track
        self.nn_budget = 100

        self._load_config()
        self._init_tracker()

    def _load_config(self):
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    cfg = yaml.safe_load(f)
                tracker_cfg = cfg.get("tracker", {})
                self.max_age = tracker_cfg.get("max_age", self.max_age)
                self.n_init = tracker_cfg.get("n_init", self.n_init)
                self.nn_budget = tracker_cfg.get("nn_budget", self.nn_budget)
                logger.info(f"Loaded tracker config from {self.config_path}")
            except Exception as e:
                logger.warning(f"Error loading tracker config from {self.config_path}: {e}")

    def _init_tracker(self):
        if DeepSort:
            logger.info("Initializing DeepSORT tracker instance...")
            self.tracker = DeepSort(
                max_age=self.max_age,
                n_init=self.n_init,
                nn_budget=self.nn_budget,
                embedder="mobilenet",
                embedder_gpu=False
            )
        else:
            logger.warning("deep_sort_realtime not installed. Falling back to mock tracker.")
            self.tracker = None
            self.next_id = 1

    def update(self, detections: list, frame: np.ndarray = None) -> list:
        """
        Updates tracker with new detections.
        Input detections format: [[x1, y1, x2, y2, conf, class_id], ...]
        Returns active tracks list:
          [{"track_id": int/str, "bbox": [x1, y1, x2, y2], "class_id": int, "confidence": float}, ...]
        """
        active_tracks = []

        if self.tracker:
            formatted_dets = []
            if detections:
                for det in detections:
                    x1, y1, x2, y2, conf, cls_id = det
                    w = max(1.0, x2 - x1)
                    h = max(1.0, y2 - y1)
                    formatted_dets.append(([x1, y1, w, h], conf, str(int(cls_id))))

            tracks = self.tracker.update_tracks(formatted_dets, frame=frame)

            for track in tracks:
                # Include confirmed or updated active tracks
                if not track.is_confirmed() and not track.is_tentative():
                    continue

                track_id = track.track_id
                ltrb = track.to_ltrb() # left, top, right, bottom
                cls_id = int(track.get_det_class()) if track.get_det_class() is not None else 0
                active_tracks.append({
                    "track_id": track_id,
                    "bbox": [float(ltrb[0]), float(ltrb[1]), float(ltrb[2]), float(ltrb[3])],
                    "class_id": cls_id,
                    "confidence": track.det_conf if track.det_conf is not None else 1.0
                })
        else:
            # Fallback mock tracking
            if detections:
                for det in detections:
                    x1, y1, x2, y2, conf, cls_id = det
                    active_tracks.append({
                        "track_id": getattr(self, 'next_id', 1),
                        "bbox": [x1, y1, x2, y2],
                        "class_id": int(cls_id),
                        "confidence": float(conf)
                    })
                    self.next_id = getattr(self, 'next_id', 1) + 1

        return active_tracks
