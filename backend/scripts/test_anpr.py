import sys
import os
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.detection.vehicle_detector import VehicleDetector
from src.anpr.plate_recogniser import PlateRecogniser

def main():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "default.yaml")
    detector = VehicleDetector(config_path)
    anpr = PlateRecogniser(config_path)

    sample_video = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "sample_traffic.mp4")
    cap = cv2.VideoCapture(sample_video)

    print("Testing ANPR extraction on vehicle crops...")
    for fidx in [60, 100, 200]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, fidx)
        ret, frame = cap.read()
        if not ret:
            continue

        dets = detector.detect(frame)
        print(f"Frame {fidx}: {len(dets)} vehicle detections")
        for idx, det in enumerate(dets):
            x1, y1, x2, y2, conf, cls_id = det
            h, w = frame.shape[:2]
            crop = frame[int(max(0, y1)):int(min(h, y2)), int(max(0, x1)):int(min(w, x2))]
            plate, p_conf = anpr.read_plate(crop)
            print(f"  Vehicle {idx+1} (Class {cls_id}, Conf {conf:.2f}) -> Plate: '{plate}' (OCR Conf: {p_conf:.2f})")

    cap.release()
    print("ANPR test completed successfully.")

if __name__ == "__main__":
    main()
