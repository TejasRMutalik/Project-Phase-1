import sys
import os
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.pipeline.pipeline import SurveillancePipeline
from db.session import init_db, SessionLocal
from db.models import VehicleDetection, Violation

def main():
    print("Initializing database tables...")
    init_db()

    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "default.yaml")
    pipeline = SurveillancePipeline(config_path)

    sample_video = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "sample_traffic.mp4")
    cap = cv2.VideoCapture(sample_video)

    db = SessionLocal()

    print("Running pipeline processing over frames 50 to 100 with DB persistence...")
    for fidx in range(50, 101):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fidx)
        ret, frame = cap.read()
        if not ret:
            break

        res = pipeline.process_frame(frame, frame_idx=fidx, camera_id="CAM-01", db=db)
        if res["vehicles"]:
            print(f"Frame {fidx:3d}: {len(res['vehicles'])} vehicles tracked, {res['violations_count']} violations saved.")

    cap.release()

    # Query DB to verify rows created
    det_count = db.query(VehicleDetection).count()
    viol_count = db.query(Violation).count()
    print(f"\nPipeline run completed.")
    print(f"Total VehicleDetections in DB: {det_count}")
    print(f"Total Violations in DB       : {viol_count}")

    db.close()

if __name__ == "__main__":
    main()
