import os
import math
import time
import logging
import cv2
import numpy as np
import yaml

logger = logging.getLogger(__name__)

class ViolationEngine:
    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.speed_limit = 40.0 # km/h
        self.pixels_per_meter = 10.0
        self.stop_line_y = 250 # Y pixel coordinate of stop line
        self.fps = 30.0
        self.track_history = {} # track_id -> (last_centroid_x, last_centroid_y, last_frame_idx)

        # No real signal hardware - RED/GREEN is simulated on a wall-clock timer.
        self.signal_red_seconds = 10.0
        self.signal_green_seconds = 10.0
        self._signal_cycle_start = time.time()
        self.helmet_edge_density_threshold = 0.12

        self._load_config()

    def _load_config(self):
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    cfg = yaml.safe_load(f)
                viol_cfg = cfg.get("violations", {})
                self.speed_limit = viol_cfg.get("speed_limit_kmh", self.speed_limit)
                self.pixels_per_meter = viol_cfg.get("pixels_per_meter", self.pixels_per_meter)
                self.stop_line_y = viol_cfg.get("stop_line_y", self.stop_line_y)
                self.signal_red_seconds = viol_cfg.get("signal_red_seconds", self.signal_red_seconds)
                self.signal_green_seconds = viol_cfg.get("signal_green_seconds", self.signal_green_seconds)
                self.helmet_edge_density_threshold = viol_cfg.get(
                    "helmet_edge_density_threshold", self.helmet_edge_density_threshold
                )

                cam_cfg = cfg.get("camera", {})
                self.fps = cam_cfg.get("fps", self.fps)
                logger.info(f"Loaded violation engine config from {self.config_path}")
            except Exception as e:
                logger.warning(f"Error loading violation engine config from {self.config_path}: {e}")

    def calculate_speed(self, track_id: str, bbox: list, frame_idx: int) -> float:
        """
        Calculates speed in km/h based on centroid displacement between frames.
        bbox: [x1, y1, x2, y2]
        """
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0

        if track_id not in self.track_history:
            self.track_history[track_id] = (cx, cy, frame_idx)
            return 0.0

        last_cx, last_cy, last_fidx = self.track_history[track_id]
        frame_diff = frame_idx - last_fidx
        self.track_history[track_id] = (cx, cy, frame_idx)

        if frame_diff <= 0:
            return 0.0

        pixel_dist = math.sqrt((cx - last_cx)**2 + (cy - last_cy)**2)
        meters = pixel_dist / max(1.0, self.pixels_per_meter)
        seconds = frame_diff / max(1.0, self.fps)
        speed_mps = meters / seconds if seconds > 0 else 0
        speed_kmh = speed_mps * 3.6

        return round(speed_kmh, 1)

    def check_overspeed(self, speed_kmh: float) -> bool:
        """Check if vehicle exceeds configured speed limit."""
        return speed_kmh > self.speed_limit

    def check_signal_jump(self, bbox: list, light_status: str) -> bool:
        """Check if vehicle centroid or bottom edge crosses stop line during RED light."""
        cy = (bbox[1] + bbox[3]) / 2.0
        bottom_y = bbox[3]

        if light_status == "RED":
            # Vehicle moving past stop line
            if bottom_y >= self.stop_line_y and cy <= self.stop_line_y + 100:
                return True
        return False

    def get_current_light_status(self) -> str:
        """Simulated RED/GREEN signal state on a wall-clock timer (no real hardware)."""
        cycle = self.signal_red_seconds + self.signal_green_seconds
        elapsed = (time.time() - self._signal_cycle_start) % cycle
        return "RED" if elapsed < self.signal_red_seconds else "GREEN"

    def check_helmet(self, class_id: int, vehicle_crop: np.ndarray = None) -> bool:
        """
        Head-region edge-density heuristic for motorcycle riders (class_id == 3).
        A helmet's shell is a smooth, low-texture surface compared to bare hair/skin,
        so low Canny edge density in the top of the crop is treated as "helmet present".
        This is a stopgap for the real head-region CNN classifier planned for Phase-2
        (needs labeled training data + GPU) - not a substitute for it.
        """
        if class_id != 3:
            return True
        if vehicle_crop is None or vehicle_crop.size == 0:
            # No evidence to flag a violation on - don't guess.
            return True

        h, w = vehicle_crop.shape[:2]
        head_region = vehicle_crop[0:max(1, int(h * 0.3)), :]
        if head_region.size == 0:
            return True

        gray = cv2.cvtColor(head_region, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.count_nonzero(edges)) / edges.size

        return edge_density < self.helmet_edge_density_threshold

    def evaluate(self, track_info: dict, frame_idx: int, light_status: str = None, vehicle_crop: np.ndarray = None) -> tuple:
        """
        Evaluates all rules for a single tracked vehicle.
        Returns tuple: (violations_list: list, speed_kmh: float)
        """
        track_id = str(track_info.get("track_id"))
        bbox = track_info.get("bbox", [0, 0, 0, 0])
        class_id = track_info.get("class_id", 0)

        if light_status is None:
            light_status = self.get_current_light_status()

        speed_kmh = self.calculate_speed(track_id, bbox, frame_idx)
        violations = []

        if self.check_overspeed(speed_kmh):
            violations.append("OVERSPEED")

        if self.check_signal_jump(bbox, light_status):
            violations.append("SIGNAL_JUMP")

        if not self.check_helmet(class_id, vehicle_crop):
            violations.append("NO_HELMET")

        return (violations, speed_kmh)
