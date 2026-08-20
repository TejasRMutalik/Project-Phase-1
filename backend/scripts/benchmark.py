"""Measures real FPS and OCR hit-rate on the sample clip - honest numbers for the report."""
import sys
import os
import time
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.pipeline.pipeline import SurveillancePipeline


def main():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "default.yaml")
    sample_video = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "sample_traffic.mp4")

    pipeline = SurveillancePipeline(config_path)
    cap = cv2.VideoCapture(sample_video)

    frame_count = 0
    vehicles_seen = 0
    plates_read = 0
    start = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        result = pipeline.process_frame(frame, frame_idx=frame_count, camera_id="BENCHMARK", db=None)
        vehicles_seen += len(result["vehicles"])
        plates_read += sum(1 for v in result["vehicles"] if v["plate_number"] != "UNKNOWN")

    elapsed = time.time() - start
    cap.release()

    fps = frame_count / elapsed if elapsed > 0 else 0
    ocr_hit_rate = (plates_read / vehicles_seen * 100) if vehicles_seen else 0

    print(f"Frames processed   : {frame_count}")
    print(f"Wall time          : {elapsed:.1f}s")
    print(f"Real pipeline FPS  : {fps:.2f}")
    print(f"Vehicles detected  : {vehicles_seen}")
    print(f"Plates read        : {plates_read}")
    print(f"OCR hit-rate       : {ocr_hit_rate:.1f}%")


if __name__ == "__main__":
    main()
