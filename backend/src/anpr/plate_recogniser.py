import logging
import cv2
import numpy as np
try:
    import easyocr
except ImportError:
    easyocr = None

logger = logging.getLogger(__name__)

class PlateRecogniser:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.reader = None
        self._initialize_ocr()

    def _initialize_ocr(self):
        logger.info("Initializing EasyOCR pipeline...")
        if easyocr:
            self.reader = easyocr.Reader(['en'], gpu=False)
        else:
            logger.warning("easyocr not installed. ANPR will run in mock mode.")

    def locate_plate(self, vehicle_crop: np.ndarray):
        """Localize the number plate within a vehicle crop."""
        gray = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2GRAY)
        bfilter = cv2.bilateralFilter(gray, 11, 17, 17)
        edged = cv2.Canny(bfilter, 30, 200)
        
        # Mocking plate contours logic
        contours, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        return None

    def read_plate(self, plate_crop: np.ndarray) -> str:
        """Run OCR on the localized plate crop."""
        if not self.reader or plate_crop is None:
            return "UNKNOWN"
        
        result = self.reader.readtext(plate_crop)
        if result:
            return result[0][-2]
        return "UNKNOWN"
