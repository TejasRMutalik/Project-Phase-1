"""Convert the IDD Detection release (VOC XML) into YOLO training layout.

See docs/MODEL_TRAINING_PLAN.md step 1. Two things this handles that a naive
converter gets wrong:

  * IDD frame numbers restart in every drive-sequence folder, so image stems
    are NOT globally unique. Flattening into one images/ dir on basename
    silently drops most of the set. Stems are folded to `a__b__0000899`.
  * Ultralytics locates a label by string-replacing os.sep + "images" + os.sep
    with the "labels" equivalent in the image path. The directory names
    `images`/`labels` are therefore load-bearing; IDD's own
    JPEGImages/Annotations names will not work.

Run --audit first to confirm the class-name spellings before converting.
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

# Contiguous, 0-indexed: the id IS the offset into data.yaml's `names` list.
# Must stay in sync with `names` in dataset/traffic_data.yaml and with
# CLASS_NAME_MAP in src/pipeline/pipeline.py after deploying best.pt.
CLASS_MAP = {
    "car": 0,
    "motorcycle": 1,
    "bus": 2,
    "truck": 3,
    "autorickshaw": 4,
}


def read_split(root: Path, split: str) -> list[str]:
    """Read train.txt/val.txt into a list of extension-less relative stems."""
    listing = root / f"{split}.txt"
    if not listing.is_file():
        sys.exit(f"missing split file: {listing}")
    stems = []
    for line in listing.read_text(encoding="utf-8").splitlines():
        entry = line.strip().replace("\\", "/").lstrip("/")
        if not entry:
            continue
        # Tolerate entries written with or without an extension.
        for ext in (".jpg", ".jpeg", ".png", ".xml"):
            if entry.lower().endswith(ext):
                entry = entry[: -len(ext)]
                break
        stems.append(entry)
    return stems


def flat_name(stem: str) -> str:
    """`highquality_16k/BLR-.../0000899` -> `highquality_16k__BLR-...__0000899`."""
    return stem.replace("/", "__")


def find_image(root: Path, stem: str) -> Path | None:
    for ext in (".jpg", ".jpeg", ".png"):
        candidate = root / "JPEGImages" / f"{stem}{ext}"
        if candidate.is_file():
            return candidate
    return None


def parse_boxes(xml_path: Path, stats: Counter) -> tuple[list[str], bool]:
    """Return (yolo lines, ok). Unmappable class names are counted, not fatal."""
    try:
        root_el = ET.parse(xml_path).getroot()
    except ET.ParseError:
        stats["xml_parse_error"] += 1
        return [], False

    size = root_el.find("size")
    width = height = 0
    if size is not None:
        width = int(float(size.findtext("width") or 0))
        height = int(float(size.findtext("height") or 0))
    if width <= 0 or height <= 0:
        # Some IDD XMLs carry a zeroed <size>; fall back to the real image.
        stats["size_missing_in_xml"] += 1
        return [], False

    lines = []
    for obj in root_el.findall("object"):
        name = (obj.findtext("name") or "").strip().lower()
        stats[f"name:{name}"] += 1
        if name not in CLASS_MAP:
            stats["box_dropped_unmapped_class"] += 1
            continue
        box = obj.find("bndbox")
        if box is None:
            continue
        xmin = float(box.findtext("xmin") or 0)
        ymin = float(box.findtext("ymin") or 0)
        xmax = float(box.findtext("xmax") or 0)
        ymax = float(box.findtext("ymax") or 0)

        # IDD contains boxes that run past the frame edge; YOLO needs 0-1.
        xmin, xmax = max(0.0, min(xmin, xmax)), min(float(width), max(xmin, xmax))
        ymin, ymax = max(0.0, min(ymin, ymax)), min(float(height), max(ymin, ymax))
        if xmax - xmin < 1 or ymax - ymin < 1:
            stats["box_dropped_degenerate"] += 1
            continue

        xc = ((xmin + xmax) / 2) / width
        yc = ((ymin + ymax) / 2) / height
        bw = (xmax - xmin) / width
        bh = (ymax - ymin) / height
        lines.append(f"{CLASS_MAP[name]} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
        stats["box_written"] += 1
    return lines, True


def place_image(src: Path, dst: Path, mode: str) -> None:
    if dst.exists():
        return
    if mode == "hardlink":
        try:
            os.link(src, dst)
            return
        except OSError:
            pass  # cross-volume or FS refusal -> fall through to copy
    import shutil

    shutil.copy2(src, dst)


def audit(root: Path, splits: list[str]) -> None:
    """Step 1.3 - report exact <name> spellings before trusting CLASS_MAP."""
    names = Counter()
    checked = 0
    for split in splits:
        for stem in read_split(root, split):
            xml_path = root / "Annotations" / f"{stem}.xml"
            if not xml_path.is_file():
                continue
            try:
                for obj in ET.parse(xml_path).getroot().findall("object"):
                    names[(obj.findtext("name") or "").strip()] += 1
            except ET.ParseError:
                continue
            checked += 1
    print(f"scanned {checked} annotation files\n")
    print(f"{'class name':<24} {'boxes':>9}   mapped?")
    for name, count in names.most_common():
        mark = "yes" if name.lower() in CLASS_MAP else "NO  <-- dropped"
        print(f"{name:<24} {count:>9}   {mark}")


def convert(root: Path, out: Path, splits: list[str], mode: str) -> None:
    grand = Counter()
    for split in splits:
        img_dir = out / "images" / split
        lbl_dir = out / "labels" / split
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        stats = Counter()
        seen: set[str] = set()
        for stem in read_split(root, split):
            flat = flat_name(stem)
            if flat in seen:
                stats["collision_after_flatten"] += 1
                continue
            seen.add(flat)

            img_src = find_image(root, stem)
            if img_src is None:
                stats["image_missing"] += 1
                continue
            xml_path = root / "Annotations" / f"{stem}.xml"
            if not xml_path.is_file():
                stats["annotation_missing"] += 1
                continue

            lines, ok = parse_boxes(xml_path, stats)
            if not ok:
                continue
            if not lines:
                # Valid negative/background frame; YOLO accepts an empty label.
                stats["image_with_no_kept_boxes"] += 1

            place_image(img_src, img_dir / f"{flat}{img_src.suffix}", mode)
            (lbl_dir / f"{flat}.txt").write_text("\n".join(lines), encoding="utf-8")
            stats["image_written"] += 1

        print(f"\n=== {split} ===")
        for key, val in sorted(stats.items()):
            if not key.startswith("name:"):
                print(f"  {key:<32} {val}")
        grand.update(stats)

    print("\n=== per-class boxes written ===")
    for name, cid in sorted(CLASS_MAP.items(), key=lambda kv: kv[1]):
        print(f"  {cid}  {name:<16} {grand[f'name:{name}']}")

    if grand["image_written"] == 0:
        sys.exit("\nERROR: nothing was written - check --root path and split files.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="dataset/IDD_Detection", type=Path)
    ap.add_argument("--out", default="dataset", type=Path)
    ap.add_argument("--splits", nargs="+", default=["train", "val"])
    ap.add_argument("--mode", choices=["hardlink", "copy"], default="hardlink",
                    help="hardlink avoids duplicating ~23 GB; same volume only")
    ap.add_argument("--audit", action="store_true",
                    help="report class-name spellings and exit without writing")
    args = ap.parse_args()

    if not args.root.is_dir():
        sys.exit(f"--root not found: {args.root.resolve()}")

    if args.audit:
        audit(args.root, args.splits)
    else:
        convert(args.root, args.out, args.splits, args.mode)


if __name__ == "__main__":
    main()
