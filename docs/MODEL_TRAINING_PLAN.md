# Model Training Plan — YOLOv8 Fine-Tune

Status as of 2026-08-20: **in progress.** Dataset downloaded
(`D:\idd-detection.tar.gz`, 22.8 GB) and extracting into `backend/dataset/`.
`backend/scripts/train_yolov8.py` is still the fake placeholder described in
`BACKEND_FIX_PLAN.md` section 04.

### Corrections applied 2026-08-20 (supersede the original draft)

1. **Class ids are contiguous `0-4`, not the COCO ids.** The original draft
   reused `pipeline.py`'s `CLASS_NAME_MAP` ids (`car=2 … truck=7`) with
   `nc: 4`. That is invalid: a YOLO label's class field is a 0-indexed offset
   into `names`, so id `7` under `nc: 4` is out of range. `CLASS_NAME_MAP`
   must be rewritten at deploy time regardless — a fine-tuned checkpoint emits
   its own indices, not COCO's.
2. **Training runs on this machine.** It has an NVIDIA GTX 1650 Ti (4 GB).
   The "no GPU here, use the separate laptop" premise in Step 5 is dropped.
   4 GB VRAM means **`--batch 8`**, not 16.
3. **`JPEGImages/` nests two levels deep**, not one, and per-sequence frame
   numbering repeats — see Step 1.
4. `backend/dataset/` and `backend/runs/` are now gitignored (`dataset/*`
   with `traffic_data.yaml` re-included). Without this a 40k-file dataset
   lands in `git status`.

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

1. **Extract** `D:\idd-detection.tar.gz` into `backend/dataset/`.
   Layout **confirmed** by listing the archive (not guessed):
   ```
   IDD_Detection/
     JPEGImages/<quality>/<drive-sequence>/NNNNNNN.jpg
     Annotations/<quality>/<drive-sequence>/NNNNNNN.xml
     train.txt
     val.txt
     test.txt        no annotations — not usable for training
   ```
   Note **two** nesting levels under `JPEGImages/`, e.g.
   `JPEGImages/highquality_16k/BLR-2018-06-19-06-21-44_part_26/0000899.jpg`.
   The original draft assumed one.

   **Frame numbers restart in every sequence folder**, so `0000899.jpg` exists
   many times over. Flattening into a single `images/train/` therefore
   collides and would silently discard most of the set. Every file must be
   renamed to its path with separators folded in, e.g.
   `highquality_16k__BLR-2018-06-19-06-21-44_part_26__0000899.jpg`, and the
   label `.txt` must carry the identical stem.

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
   0–1. Use **contiguous ids** (see Correction 1) — `autorickshaw` **is**
   included, giving 5 classes:

   | id | name |
   |----|------|
   | 0  | car |
   | 1  | motorcycle |
   | 2  | bus |
   | 3  | truck |
   | 4  | autorickshaw |

   ```python
   # backend/scripts/convert_idd_to_yolo.py (to be written)
   import xml.etree.ElementTree as ET

   CLASS_MAP = {"car": 0, "motorcycle": 1, "bus": 2, "truck": 3, "autorickshaw": 4}

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
   The `images`/`labels` names are load-bearing: Ultralytics derives each
   label path from its image path by string-replacing `/images/` → `/labels/`.
   IDD's own `JPEGImages`/`Annotations` names will not work.

   Use **hardlinks**, not copies — a copy would duplicate ~23 GB for no gain.
   On Windows, `New-Item -ItemType HardLink` needs no admin rights (unlike
   symlinks, which require Developer Mode); the extract and the repo are both
   on `D:`, and hardlinks are same-volume-only, so this works.

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
nc: 5
names: ["car", "motorcycle", "bus", "truck", "autorickshaw"]
```
`names` order **must** match the id table in Step 1.4 exactly — the list index
*is* the class id. Reordering this list silently relabels the whole dataset.
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

## Step 5 — Run training

Runs on this machine — GTX 1650 Ti, 4 GB (Correction 2). Install the CUDA
build of torch explicitly; a plain `pip install ultralytics` can pull the
CPU-only wheel and training then silently falls back to CPU.
```bash
pip install ultralytics
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
python scripts/train_yolov8.py --data dataset/traffic_data.yaml --epochs 50 --batch 8
```
`--batch 8` because of the 4 GB VRAM ceiling. If it still OOMs, drop to 4
before reducing `imgsz` — smaller images cost more mAP than smaller batches.
Expect this to run for many hours; use `nohup`/background and check
`runs/detect/train/results.csv` for progress.

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
`vehicle_detector.py` already loads whatever path the config points to, but
**one code change is required**: `CLASS_NAME_MAP` in
`src/pipeline/pipeline.py` still holds COCO ids and must be replaced with the
fine-tuned model's contiguous ids, or every detection gets mislabelled:
```python
CLASS_NAME_MAP = {
    0: "Car", 1: "Motorcycle", 2: "Bus", 3: "Truck", 4: "Autorickshaw",
}
```
Note this makes `pipeline.py` incompatible with the stock `yolov8n.pt` — the
two id schemes cannot both be live. Swap the weights and the map together.

## Step 8 — Re-benchmark

Rerun `scripts/benchmark.py` on the sample clip, compare FPS / detection
count / OCR hit-rate against the existing baseline (3.62 FPS, 339 vehicles
across 377 frames, 0% OCR hit-rate — see `BACKEND_FIX_PLAN.md` section 05).

## Out of scope here

Helmet classifier training is a separate task — needs its own labeled
head-region dataset, not part of this vehicle-detection fine-tune. Tracked
in `BACKEND_FIX_PLAN.md` section 06.
