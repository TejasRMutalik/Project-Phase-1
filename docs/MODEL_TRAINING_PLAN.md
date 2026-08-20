# Model Training Plan — YOLOv8 Fine-Tune

Status as of 2026-08-20: not started. `backend/scripts/train_yolov8.py` is still the
fake placeholder described in `BACKEND_FIX_PLAN.md` section 04. This doc is the
step-by-step execution plan for when the GPU laptop is available.

## Why fine-tune

Current `weights/yolov8n.pt` is stock COCO-pretrained, never trained on this
project's domain (Indian traffic, project's own camera footage). No measured
mAP/precision/recall — report's 91%/84%/78% numbers are aspirational, not real.

## Dataset

**Download: `IDD Detection` (22.8 GB)** from `idd.insaan.iiit.ac.in`
(IIIT Hyderabad, IDD — Indian Driving Dataset). 40,000 images, VOC-XML
bounding-box annotations, released 2018.

Rejected alternatives and why:
- `IDD Segmentation` variants — pixel masks, wrong annotation type for YOLO.
- `IDD 117k - Detection` (5-part, 72 GB total) — 3x the size, overkill for a
  first fine-tune pass with no GPU yet; revisit if 22.8 GB run underperforms.
- `IDD Lite` — too subsampled for a real fine-tune, useful only for
  architecture-search sanity checks.
- `IDD Multimodal`, `IDD Temporal`, `IDD-3D`, `IDD-AW`, `IDD-X`, `FGVD`,
  `MTSVD`, `I2WDD` — different tasks (stereo/LIDAR, adverse weather,
  behavior/3D, traffic signs) or not vehicle detection.

## Step 1 — Get dataset, convert to YOLO format

1. **Extract** the downloaded `IDD_Detection.tar.gz` into `backend/dataset/`.
   Expected layout (confirm against actual extracted folder — IDD's release
   layout has varied by year):
   ```
   IDD_Detection/
     JPEGImages/     images, organized by drive-sequence subfolders
     Annotations/    matching VOC XML files, same subfolder structure
     train.txt
     val.txt
     test.txt        no annotations — not usable for training
   ```

2. **Spot-check one file pair.** Pick one entry from `train.txt`, open both the
   `.jpg` and its `.xml`. Confirm the XML has `<object><name>...</name>
   <bndbox>` tags as expected before writing a conversion script against it.

3. **Confirm exact class name strings** used in the annotations:
   ```bash
   grep -rhoP '(?<=<name>)[^<]+' IDD_Detection/Annotations/ | sort -u
   ```
   Need exact spelling (e.g. `motorcycle` vs `two-wheeler`,
   `autorickshaw` vs `auto-rickshaw`) — a mismatch silently drops every box
   for that class during conversion.

4. **Convert VOC XML → YOLO txt.** One `.txt` per image, one line per box:
   `<class_id> <x_center/w> <y_center/h> <box_w/w> <box_h/h>`, all normalized
   0–1. Reuse the class-id mapping already in `pipeline.py`'s
   `CLASS_NAME_MAP` for consistency (`car=2, motorcycle=3, bus=5, truck=7`);
   add a new id (e.g. `8`) for `autorickshaw` if included.

   ```python
   # backend/scripts/convert_idd_to_yolo.py (to be written)
   import xml.etree.ElementTree as ET

   CLASS_MAP = {"car": 2, "motorcycle": 3, "bus": 5, "truck": 7, "autorickshaw": 8}

   def convert_one(xml_path, out_txt_path):
       tree = ET.parse(xml_path)
       root = tree.getroot()
       w = int(root.find("size/width").text)
       h = int(root.find("size/height").text)
       lines = []
       for obj in root.findall("object"):
           name = obj.find("name").text
           if name not in CLASS_MAP:
               continue
           cls_id = CLASS_MAP[name]
           box = obj.find("bndbox")
           xmin, ymin = float(box.find("xmin").text), float(box.find("ymin").text)
           xmax, ymax = float(box.find("xmax").text), float(box.find("ymax").text)
           xc, yc = ((xmin + xmax) / 2) / w, ((ymin + ymax) / 2) / h
           bw, bh = (xmax - xmin) / w, (ymax - ymin) / h
           lines.append(f"{cls_id} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
       with open(out_txt_path, "w") as f:
           f.write("\n".join(lines))
   ```
   Run over every entry in `train.txt` and `val.txt`.

5. **Arrange into YOLO folder layout**:
   ```
   backend/dataset/
     images/train/   images/val/
     labels/train/   labels/val/
   ```
   Copy (or symlink, to save space on a 22.8 GB set) images per split;
   write converted labels into the matching `labels/` folder.

6. **Sanity check.**
   - `ls images/train | wc -l` vs `ls labels/train | wc -l` — counts should
     line up (images with zero valid boxes still need an empty `.txt`, YOLO
     accepts that).
   - Draw boxes back onto 5–10 random images to eyeball alignment before
     trusting the full conversion.

## Step 2 — `data.yaml`

```yaml
train: dataset/images/train
val: dataset/images/val
nc: 4   # 5 if autorickshaw included
names: ["car", "motorcycle", "bus", "truck"]   # add "autorickshaw" if used
```
Save as `backend/dataset/traffic_data.yaml` — matches the default path already
hardcoded in `train_yolov8.py`'s argparse.

## Step 3 — Own footage (optional second pass)

Once the IDD-based fine-tune works, label the project's own camera clips
(LabelImg / Roboflow / CVAT) for domain-specific angle/lighting/plate
distance. Merge into the same `images/`/`labels/` split.

## Step 4 — Fix `train_yolov8.py`

Currently fake (`# Fake import to simulate YOLO`, `# Fake training loop`).
Replace with a real call:
```python
def train_custom_model(data_yaml, epochs, batch_size):
    model = YOLO("yolov8n.pt")   # transfer learning, not from scratch
    model.train(data=data_yaml, epochs=epochs, batch=batch_size, imgsz=640)
```
Keep the existing argparse interface as-is.

## Step 5 — Run on GPU machine

CPU-only training on the current dev machine was ruled out as impractical
(see `BACKEND_FIX_PLAN.md` section 04). Run on the separate GPU laptop:
```bash
pip install ultralytics
python scripts/train_yolov8.py --data dataset/traffic_data.yaml --epochs 50 --batch 16
```

## Step 6 — Validate

Ultralytics auto-reports mAP50/precision/recall on the val split after
training (`runs/detect/train/results.csv`, `weights/best.pt`). Use these
real numbers to replace the report's aspirational 91%/84%/78%.

## Step 7 — Deploy

Copy `best.pt` into `backend/weights/`, update `default.yaml`:
```yaml
model:
  yolo_weights: "weights/best.pt"
```
No other code change needed — `vehicle_detector.py` already loads whatever
path the config points to.

## Step 8 — Re-benchmark

Rerun `scripts/benchmark.py` on the sample clip, compare FPS / detection
count / OCR hit-rate against the existing baseline (3.62 FPS, 339 vehicles
across 377 frames, 0% OCR hit-rate — see `BACKEND_FIX_PLAN.md` section 05).

## Out of scope here

Helmet classifier training is a separate task — needs its own labeled
head-region dataset, not part of this vehicle-detection fine-tune. Tracked
in `BACKEND_FIX_PLAN.md` section 06.
