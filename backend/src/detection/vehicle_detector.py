import os
import cv2
import numpy as np
import logging
import yaml

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

logger = logging.getLogger(__name__)

class VehicleDetector:
    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.model = None
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        self.conf_threshold = 0.3 # Default threshold (or from config)
        self.iou_threshold = 0.45
        self.allowed_classes = [2, 3, 5, 7] # car, motorcycle, bus, truck
        self.weights_path = "weights/yolov8n.pt"

        self._load_config()
        self._load_model()

    def _load_config(self):
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    cfg = yaml.safe_load(f)
                model_cfg = cfg.get("model", {})
                self.weights_path = model_cfg.get("yolo_weights", self.weights_path)
                self.conf_threshold = model_cfg.get("confidence_threshold", self.conf_threshold)
                self.iou_threshold = model_cfg.get("iou_threshold", self.iou_threshold)
                self.allowed_classes = model_cfg.get("classes", self.allowed_classes)
                logger.info(f"Loaded detector config from {self.config_path}")
            except Exception as e:
                logger.warning(f"Error loading config file {self.config_path}: {e}")

    def _load_model(self):
        # Resolve weights path relative to backend directory if relative
        if not os.path.isabs(self.weights_path):
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.weights_path = os.path.join(backend_dir, self.weights_path)

        logger.info(f"Loading YOLOv8 weights from {self.weights_path}...")
        if YOLO and os.path.exists(self.weights_path):
            self.model = YOLO(self.weights_path)
            logger.info("YOLOv8 model loaded successfully.")
        elif YOLO:
            logger.warning(f"Weights file not found at {self.weights_path}, loading default 'yolov8n.pt'...")
            self.model = YOLO("yolov8n.pt")
        else:
            logger.warning("ultralytics not installed. Running in mock mode.")

    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Apply CLAHE preprocessing to improve contrast for detection."""
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        cl = self.clahe.apply(l_channel)
        limg = cv2.merge((cl, a, b))
        return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    def detect(self, frame: np.ndarray) -> list:
        """
        Run inference on frame.
        Returns list of detections: [[x1, y1, x2, y2, confidence, class_id], ...]
        """
        if self.model is None or frame is None:
            return []

        processed_frame = self.preprocess(frame)
        results = self.model(processed_frame, conf=self.conf_threshold, iou=self.iou_threshold, verbose=False)

        detections = []
        if results and len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                if cls_id in self.allowed_classes:
                    x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
                    detections.append([x1, y1, x2, y2, conf, cls_id])

        return detections
