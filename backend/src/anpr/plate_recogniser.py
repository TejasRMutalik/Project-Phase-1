import os
import re
import cv2
import numpy as np
import logging
import yaml

try:
    import easyocr
except ImportError:
    easyocr = None

logger = logging.getLogger(__name__)

class PlateRecogniser:
    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.reader = None
        self.conf_threshold = 0.4
        self.languages = ['en']

        self._load_config()
        self._initialize_ocr()

    def _load_config(self):
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    cfg = yaml.safe_load(f)
                anpr_cfg = cfg.get("anpr", {})
                self.conf_threshold = anpr_cfg.get("confidence_threshold", self.conf_threshold)
                self.languages = anpr_cfg.get("ocr_language", self.languages)
                logger.info(f"Loaded ANPR config from {self.config_path}")
            except Exception as e:
                logger.warning(f"Error loading ANPR config from {self.config_path}: {e}")

    def _initialize_ocr(self):
        if easyocr:
            logger.info("Initializing EasyOCR pipeline...")
            try:
                # Lazy loading reader
                self.reader = easyocr.Reader(self.languages, gpu=False)
                logger.info("EasyOCR initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize EasyOCR Reader: {e}")
                self.reader = None
        else:
            logger.warning("easyocr not installed. ANPR running in fallback mode.")

    def locate_plate(self, vehicle_crop: np.ndarray) -> np.ndarray:
        """
        Localizes license plate within a vehicle image crop using OpenCV contour analysis.
        Returns plate image crop or lower portion of vehicle if contour localization fails.
        """
        if vehicle_crop is None or vehicle_crop.size == 0:
            return None

        h, w = vehicle_crop.shape[:2]
        gray = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2GRAY)
        bfilter = cv2.bilateralFilter(gray, 11, 17, 17)
        edged = cv2.Canny(bfilter, 30, 200)

        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

        plate_crop = None
        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.018 * perimeter, True)

            # License plates are 4-sided rectangles
            if len(approx) == 4:
                x, y, cw, ch = cv2.boundingRect(approx)
                aspect_ratio = cw / float(ch) if ch > 0 else 0
                # License plate typical aspect ratio between 2.0 and 6.0
                if 1.8 <= aspect_ratio <= 6.5 and cw * ch > 200:
                    plate_crop = vehicle_crop[y:y+ch, x:x+cw]
                    break

        # Fallback: crop bottom 40% of the vehicle where plate usually resides
        if plate_crop is None:
            plate_crop = vehicle_crop[int(h * 0.6):, :]

        return plate_crop

    def compute_crop_sharpness(self, image: np.ndarray) -> float:
        """Compute Laplacian variance sharpness on image crop (h_ij in RATG-OC Eq. 3)."""
        if image is None or image.size == 0:
            return 0.0
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    def clean_plate_text(self, text: str) -> str:
        """Clean and normalize OCR output string (e.g. uppercase, alphanumeric)."""
        if not text:
            return "UNKNOWN"
        cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
        return cleaned if len(cleaned) >= 4 else "UNKNOWN"

    def read_plate(self, vehicle_crop: np.ndarray) -> tuple:
        """
        Runs OCR on vehicle crop.
        Returns tuple: (plate_number: str, confidence: float)
        """
        plate_crop = self.locate_plate(vehicle_crop)
        if plate_crop is None or plate_crop.size == 0:
            return ("UNKNOWN", 0.0)

        if not self.reader:
            return ("UNKNOWN", 0.0)

        try:
            results = self.reader.readtext(plate_crop)
            if results:
                best_match = max(results, key=lambda res: res[2]) # pick highest confidence
                bbox, text, conf = best_match
                cleaned_text = self.clean_plate_text(text)
                if conf >= self.conf_threshold and cleaned_text != "UNKNOWN":
                    return (cleaned_text, float(conf))
                return ("UNKNOWN", float(conf))
        except Exception as e:
            logger.warning(f"Error during EasyOCR readtext: {e}")

        return ("UNKNOWN", 0.0)

