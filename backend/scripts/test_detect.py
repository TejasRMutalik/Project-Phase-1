"""
test_detect.py  —  M0 sanity check
Runs YOLOv8n on the first frame of the sample traffic clip and prints
real bounding boxes to the terminal.

Run from the backend/ directory:
    python scripts/test_detect.py

Done when: bounding boxes with class names and confidence scores print
           without errors.
"""

import os
import sys

# ── 1. Locate the sample clip ────────────────────────────────────────────────
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
SAMPLE_VIDEO = os.path.join(ASSETS_DIR, "sample_traffic.mp4")

if not os.path.exists(SAMPLE_VIDEO):
    print("[ERROR] Sample clip not found.")
    print(f"        Expected at: {SAMPLE_VIDEO}")
    print("        Run:  python scripts/fetch_sample.py  first.")
    sys.exit(1)

# ── 2. Check OpenCV ──────────────────────────────────────────────────────────
try:
    import cv2
except ImportError:
    print("[ERROR] opencv-python not installed.  Run:  pip install opencv-python")
    sys.exit(1)

# ── 3. Check ultralytics ─────────────────────────────────────────────────────
try:
    from ultralytics import YOLO
except ImportError:
    print("[ERROR] ultralytics not installed.  Run:  pip install ultralytics")
    sys.exit(1)

# ── 4. Load model ────────────────────────────────────────────────────────────
WEIGHTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "weights")
WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "yolov8n.pt")

print("[M0] Loading YOLOv8n weights...")
print(f"     Model path : {WEIGHTS_PATH}")
print("     (ultralytics will auto-download if the file is missing)\n")

os.makedirs(WEIGHTS_DIR, exist_ok=True)
model = YOLO(WEIGHTS_PATH)   # auto-downloads yolov8n.pt on first run

# COCO vehicle class IDs that match configs/default.yaml
VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}

# ── 5. Grab the first frame ──────────────────────────────────────────────────
cap = cv2.VideoCapture(SAMPLE_VIDEO)
if not cap.isOpened():
    print(f"[ERROR] Could not open video: {SAMPLE_VIDEO}")
    sys.exit(1)

ret, frame = cap.read()
cap.release()

if not ret:
    print("[ERROR] Could not read first frame from sample clip.")
    sys.exit(1)

h, w = frame.shape[:2]
print(f"[M0] Frame grabbed  — size: {w}x{h}")

# ── 6. Run inference ─────────────────────────────────────────────────────────
print("[M0] Running YOLOv8n inference on frame 0...\n")
results = model(frame, verbose=False)[0]

# ── 7. Parse & print detections ──────────────────────────────────────────────
boxes = results.boxes
detections_found = 0

print(f"{'#':<4} {'class':<14} {'conf':>6}   {'bbox (x1,y1,x2,y2)'}")
print("-" * 60)

for i, box in enumerate(boxes):
    cls_id   = int(box.cls[0])
    conf     = float(box.conf[0])
    x1, y1, x2, y2 = [int(v) for v in box.xyxy[0]]
    cls_name = model.names.get(cls_id, f"cls_{cls_id}")

    # Highlight vehicle classes
    tag = " ← VEHICLE" if cls_id in VEHICLE_CLASSES else ""
    print(f"{i:<4} {cls_name:<14} {conf:>6.2f}   ({x1}, {y1}, {x2}, {y2}){tag}")
    if cls_id in VEHICLE_CLASSES:
        detections_found += 1

print("-" * 60)
print(f"\n[M0] Total objects detected : {len(boxes)}")
print(f"[M0] Vehicle-class hits     : {detections_found}")

if detections_found > 0:
    print("\n[✅ M0 PASS] Real bounding boxes confirmed. YOLOv8 pipeline is live.")
else:
    print("\n[⚠️  M0 WARN] No vehicles detected on frame 0.")
    print("             Try a different video clip, or check the sample content.")
