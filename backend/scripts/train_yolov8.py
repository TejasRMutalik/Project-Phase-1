"""Fine-tune YOLOv8n on the converted IDD dataset.

See docs/MODEL_TRAINING_PLAN.md steps 4-6. Replaces the previous placeholder,
which logged a fabricated training loop and exited without training anything.
"""
import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def train_custom_model(data_yaml, epochs, batch_size, imgsz=640, weights="yolov8n.pt"):
    try:
        from ultralytics import YOLO
    except ImportError:
        sys.exit("ultralytics not installed. Run: pip install ultralytics")

    try:
        import torch
    except ImportError:
        sys.exit("torch not installed. Run: pip install ultralytics")

    if torch.cuda.is_available():
        device = 0
        logger.info("CUDA device: %s", torch.cuda.get_device_name(0))
        vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
        logger.info("VRAM: %.1f GB", vram_gb)
        if vram_gb < 6 and batch_size > 8:
            # 4 GB (GTX 1650 Ti) will OOM at batch 16 / imgsz 640.
            logger.warning(
                "batch=%d is likely to OOM on %.1f GB. Consider --batch 8.",
                batch_size, vram_gb,
            )
    else:
        device = "cpu"
        logger.warning(
            "No CUDA device found - training on CPU. This is impractically slow "
            "for 40k images; check that a CUDA build of torch is installed."
        )

    logger.info("Dataset:  %s", data_yaml)
    logger.info("Epochs=%s  Batch=%s  imgsz=%s  base=%s", epochs, batch_size, imgsz, weights)

    # Transfer learning from the COCO-pretrained checkpoint, not from scratch.
    model = YOLO(weights)
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        batch=batch_size,
        imgsz=imgsz,
        device=device,
    )
    logger.info("Done. Weights and results.csv under: %s", results.save_dir)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="dataset/traffic_data.yaml")
    parser.add_argument("--epochs", type=int, default=100)
    # Default lowered from 16: this machine has 4 GB VRAM.
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--weights", default="yolov8n.pt")
    args = parser.parse_args()

    train_custom_model(args.data, args.epochs, args.batch, args.imgsz, args.weights)
