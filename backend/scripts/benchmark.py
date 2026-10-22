"""
Benchmark comparing Baseline Pipeline vs RATG-OC (Proposed) matching Table I of the research paper:
  - Throughput (frame/s)
  - Mean latency (ms/frame)
  - P95 latency (ms/frame)
  - Peak memory (GB)
  - Detector invocations (% frames)
  - OCR calls (% track-frames)
  - Plates resolved / locked
"""
import sys
import os
import time
import argparse
import psutil
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.pipeline.pipeline import SurveillancePipeline


def run_benchmark(sample_video: str, config_path: str, enable_ratg: bool, max_frames: int = None) -> dict:
    pipeline = SurveillancePipeline(config_path)
    pipeline.ratg_enabled = enable_ratg

    cap = cv2.VideoCapture(sample_video)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video source: {sample_video}")

    frame_count = 0
    detector_invocations = 0
    ocr_calls = 0
    track_frames_total = 0
    plates_read = 0
    plates_locked = 0

    latencies = []
    process = psutil.Process(os.getpid())
    peak_memory_mb = 0

    start_wall = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        if max_frames and frame_count > max_frames:
            break

        t0 = time.time()
        result = pipeline.process_frame(frame, frame_idx=frame_count, camera_id="BENCHMARK", db=None)
        t_frame = time.time() - t0
        latencies.append(t_frame)

        if result.get("detector_triggered", True):
            detector_invocations += 1

        vehicles = result.get("vehicles", [])
        track_frames_total += len(vehicles)
        for v in vehicles:
            if v.get("ocr_invoked", False) or not enable_ratg:
                ocr_calls += 1
            if v.get("plate_number", "UNKNOWN") != "UNKNOWN":
                plates_read += 1
            if v.get("plate_locked", False):
                plates_locked += 1

        mem = process.memory_info().rss / (1024 * 1024)
        if mem > peak_memory_mb:
            peak_memory_mb = mem

    wall_time = time.time() - start_wall
    cap.release()

    fps = frame_count / wall_time if wall_time > 0 else 0
    mean_lat_ms = (np.mean(latencies) * 1000.0) if latencies else 0.0
    p95_lat_ms = (np.percentile(latencies, 95) * 1000.0) if latencies else 0.0
    peak_mem_gb = peak_memory_mb / 1024.0

    det_invoc_pct = (detector_invocations / max(1, frame_count)) * 100.0
    ocr_calls_pct = (ocr_calls / max(1, track_frames_total)) * 100.0 if track_frames_total else 0.0

    return {
        "frames": frame_count,
        "wall_time": wall_time,
        "throughput_fps": fps,
        "mean_latency_ms": mean_lat_ms,
        "p95_latency_ms": p95_lat_ms,
        "peak_memory_gb": peak_mem_gb,
        "detector_invocations_pct": det_invoc_pct,
        "ocr_calls_pct": ocr_calls_pct,
        "total_vehicles_tracked": track_frames_total,
        "plates_read": plates_read,
        "plates_locked": plates_locked
    }


def main():
    parser = argparse.ArgumentParser(description="RATG-OC Table I Benchmark Runner")
    parser.add_argument("--frames", type=int, default=None, help="Limit number of frames to benchmark (default: all)")
    parser.add_argument("--mode", choices=["both", "ratg", "baseline"], default="both", help="Execution mode")
    args = parser.parse_args()

    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "default.yaml")
    sample_video = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "sample_traffic.mp4")

    print("================================================================================")
    print("                RATG-OC TRAFFIC SURVEILLANCE BENCHMARK                          ")
    print("================================================================================")
    print(f"Video Source : {sample_video}")
    print(f"Max Frames   : {args.frames or 'Full Video'}\n")

    results = {}

    if args.mode in ["both", "baseline"]:
        print("[1/2] Benchmarking Baseline Pipeline (RATG disabled, 100% detector calls)...")
        results["Baseline Pipeline"] = run_benchmark(sample_video, config_path, enable_ratg=False, max_frames=args.frames)
        print("  -> Baseline complete.")

    if args.mode in ["both", "ratg"]:
        print("[2/2] Benchmarking RATG-OC (Proposed: Adaptive Risk Gating + OCR Consensus)...")
        results["RATG-OC (Proposed)"] = run_benchmark(sample_video, config_path, enable_ratg=True, max_frames=args.frames)
        print("  -> RATG-OC complete.\n")

    print("\n" + "=" * 80)
    print("TABLE I: EXPERIMENTAL BENCHMARK COMPARISON")
    print("=" * 80)
    header = f"{'Metric':<34}"
    for name in results:
        header += f" {name:>20}"
    print(header)
    print("-" * 80)

    rows = [
        ("Throughput (frame/s)", "throughput_fps", "{:.1f}"),
        ("Mean latency (ms/frame)", "mean_latency_ms", "{:.1f}"),
        ("P95 latency (ms/frame)", "p95_latency_ms", "{:.1f}"),
        ("Peak memory (GB)", "peak_memory_gb", "{:.2f}"),
        ("Detector invocations (% frames)", "detector_invocations_pct", "{:.1f}"),
        ("OCR calls (% track-frames)", "ocr_calls_pct", "{:.1f}"),
        ("Track-frames evaluated", "total_vehicles_tracked", "{:d}"),
        ("Plates read count", "plates_read", "{:d}"),
        ("Plates locked count", "plates_locked", "{:d}"),
    ]

    for label, key, fmt in rows:
        row_str = f"{label:<34}"
        for name in results:
            val = results[name][key]
            row_str += f" {fmt.format(val):>20}"
        print(row_str)

    print("=" * 80)


if __name__ == "__main__":
    main()
