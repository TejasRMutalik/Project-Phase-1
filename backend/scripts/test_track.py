import sys
import os
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.detection.vehicle_detector import VehicleDetector
from src.tracking.deepsort_tracker import DeepSortTracker

def main():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "default.yaml")
    detector = VehicleDetector(config_path)
    tracker = DeepSortTracker(config_path)

    sample_video = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "sample_traffic.mp4")
    cap = cv2.VideoCapture(sample_video)

    print("Running tracking test across frames 50 to 120...")
    for fidx in range(50, 121):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fidx)
        ret, frame = cap.read()
        if not ret:
            break

        dets = detector.detect(frame)
        tracks = tracker.update(dets, frame=frame)
        if tracks or dets:
            track_ids = [t['track_id'] for t in tracks]
            print(f"Frame {fidx:3d}: Detections={len(dets)} -> Track IDs={track_ids}")

    cap.release()
    print("Tracking test completed successfully.")

if __name__ == "__main__":
    main()
