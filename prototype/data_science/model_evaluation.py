"""
VisionGuard — Model Evaluation & Validation Script (Colab-Ready)
=================================================================
Areeba's Day 2-3 Tasks: Run model.val() for Confusion Matrices, PR curves, mAP

This script is designed to run on Google Colab OR locally:
  - Violence Classifier evaluation
  - Fire v2 model evaluation & comparison against v1
  - Weapon Detection model evaluation
  - Generates Confusion Matrix, PR curves, mAP50, mAP50-95

Usage (Colab):
  # Upload this script, then run:
  !python model_evaluation.py --model /content/drive/MyDrive/violence_classifier_best.pt --data /content/dataset/ --task classify
  !python model_evaluation.py --model /content/drive/MyDrive/fire_smoke_best_v2.pt --data /content/fire_dataset/ --task detect

Usage (Local):
  python model_evaluation.py --model prototype/models/violence_classifier_best.pt --data path/to/val_dataset --task classify
  python model_evaluation.py --model prototype/models/fire_smoke_best.pt --data path/to/fire_dataset --task detect
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ModelEvaluation")


def evaluate_model(model_path: str, data_path: str, task: str = "detect",
                   output_dir: str = "./eval_results", img_size: int = 640,
                   device: str = "auto", batch_size: int = 16) -> dict:
    """
    Run YOLO model validation and generate comprehensive metrics.
    
    Args:
        model_path: Path to .pt model weights
        data_path: Path to dataset (YOLO format for detect, folder structure for classify)
        task: "detect" for object detection, "classify" for classification
        output_dir: Directory to save evaluation results
        img_size: Input image size (640 for detection, 224 for classification)
        device: "auto", "0" for GPU, "cpu"
        batch_size: Validation batch size
    
    Returns:
        Dictionary containing all evaluation metrics
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        logger.error("ultralytics not installed! Install: pip install ultralytics")
        sys.exit(1)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Auto-detect device
    if device == "auto":
        import torch
        device = 0 if torch.cuda.is_available() else "cpu"
    
    # Auto-detect image size for classifiers
    if task == "classify" and img_size == 640:
        img_size = 224
    
    logger.info("=" * 60)
    logger.info("  VisionGuard Model Evaluation")
    logger.info("=" * 60)
    logger.info(f"  Model:    {model_path}")
    logger.info(f"  Dataset:  {data_path}")
    logger.info(f"  Task:     {task}")
    logger.info(f"  ImgSize:  {img_size}")
    logger.info(f"  Device:   {device}")
    logger.info("=" * 60)
    
    # Load model
    model = YOLO(model_path)
    model_name = Path(model_path).stem
    
    # Run validation
    logger.info("Running model.val() — this may take a few minutes...")
    
    results = model.val(
        data=data_path,
        imgsz=img_size,
        batch=batch_size,
        device=device,
        split="val",           # Use validation split
        save_json=True,        # Save COCO-format results
        save_hybrid=False,
        conf=0.25,             # Confidence threshold for validation
        iou=0.6,               # IoU threshold for NMS
        plots=True,            # Generate confusion matrix, PR curves, etc.
        project=output_dir,
        name=f"{model_name}_eval",
    )
    
    # ─── Extract Metrics ───
    metrics = {
        "model_name": model_name,
        "model_path": str(model_path),
        "dataset_path": str(data_path),
        "task": task,
        "timestamp": datetime.now().isoformat(),
        "device": str(device),
        "img_size": img_size,
    }
    
    if task == "detect":
        # Object detection metrics
        metrics["mAP50"] = float(results.box.map50) if hasattr(results, 'box') else None
        metrics["mAP50_95"] = float(results.box.map) if hasattr(results, 'box') else None
        metrics["precision"] = float(results.box.mp) if hasattr(results, 'box') else None
        metrics["recall"] = float(results.box.mr) if hasattr(results, 'box') else None
        
        # Per-class metrics
        if hasattr(results, 'box') and hasattr(results.box, 'maps'):
            per_class = {}
            class_names = results.names if hasattr(results, 'names') else {}
            for i, map_val in enumerate(results.box.maps):
                cls_name = class_names.get(i, f"class_{i}")
                per_class[cls_name] = {
                    "mAP50": float(results.box.ap50[i]) if hasattr(results.box, 'ap50') else None,
                    "mAP50_95": float(map_val),
                }
            metrics["per_class"] = per_class
    
    elif task == "classify":
        # Classification metrics
        metrics["top1_accuracy"] = float(results.top1) if hasattr(results, 'top1') else None
        metrics["top5_accuracy"] = float(results.top5) if hasattr(results, 'top5') else None
    
    # ─── Print Results ───
    print(f"\n{'═' * 60}")
    print(f"  📊 EVALUATION RESULTS: {model_name}")
    print(f"{'═' * 60}")
    
    if task == "detect":
        print(f"  mAP@50:          {metrics.get('mAP50', 'N/A')}")
        print(f"  mAP@50-95:       {metrics.get('mAP50_95', 'N/A')}")
        print(f"  Precision (avg):  {metrics.get('precision', 'N/A')}")
        print(f"  Recall (avg):     {metrics.get('recall', 'N/A')}")
        
        if "per_class" in metrics:
            print(f"\n  Per-Class Breakdown:")
            print(f"  {'─' * 45}")
            for cls_name, cls_metrics in metrics["per_class"].items():
                print(f"    {cls_name:20s}  mAP50={cls_metrics['mAP50']:.4f}  mAP50-95={cls_metrics['mAP50_95']:.4f}")
    
    elif task == "classify":
        print(f"  Top-1 Accuracy:   {metrics.get('top1_accuracy', 'N/A')}")
        print(f"  Top-5 Accuracy:   {metrics.get('top5_accuracy', 'N/A')}")
    
    print(f"\n  Results saved to: {output_dir}/{model_name}_eval/")
    print(f"  → Confusion Matrix:  confusion_matrix.png")
    print(f"  → PR Curve:          PR_curve.png")
    print(f"  → F1 Curve:          F1_curve.png")
    print(f"{'═' * 60}\n")
    
    # Save metrics JSON
    metrics_path = os.path.join(output_dir, f"{model_name}_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    logger.info(f"Metrics saved to: {metrics_path}")
    
    return metrics


def compare_models(metrics_v1: dict, metrics_v2: dict):
    """
    Compare two model versions and print improvement analysis.
    Designed for Fire v2 vs v1 comparison (Day 3 task).
    """
    print(f"\n{'═' * 60}")
    print(f"  📊 MODEL COMPARISON: v1 vs v2")
    print(f"{'═' * 60}")
    
    def compare_metric(name, v1_val, v2_val):
        if v1_val is None or v2_val is None:
            return
        diff = v2_val - v1_val
        sign = "+" if diff > 0 else ""
        emoji = "✅" if diff > 0 else "⚠️" if diff == 0 else "❌"
        print(f"  {emoji} {name:20s}  v1={v1_val:.4f}  v2={v2_val:.4f}  ({sign}{diff:.4f})")
    
    print(f"  v1: {metrics_v1.get('model_name', 'unknown')}")
    print(f"  v2: {metrics_v2.get('model_name', 'unknown')}")
    print(f"  {'─' * 45}")
    
    if metrics_v1.get("task") == "detect":
        compare_metric("mAP@50", metrics_v1.get("mAP50"), metrics_v2.get("mAP50"))
        compare_metric("mAP@50-95", metrics_v1.get("mAP50_95"), metrics_v2.get("mAP50_95"))
        compare_metric("Precision", metrics_v1.get("precision"), metrics_v2.get("precision"))
        compare_metric("Recall", metrics_v1.get("recall"), metrics_v2.get("recall"))
    elif metrics_v1.get("task") == "classify":
        compare_metric("Top-1 Accuracy", metrics_v1.get("top1_accuracy"), metrics_v2.get("top1_accuracy"))
        compare_metric("Top-5 Accuracy", metrics_v1.get("top5_accuracy"), metrics_v2.get("top5_accuracy"))
    
    print(f"{'═' * 60}\n")


def generate_colab_notebook_code():
    """
    Print ready-to-paste Colab code for model evaluation.
    Copy this output directly into a Google Colab notebook.
    """
    colab_code = '''
# ═══════════════════════════════════════════════════════════════
# VisionGuard — Model Evaluation Colab Notebook
# Paste each cell block into a separate Colab cell
# ═══════════════════════════════════════════════════════════════

# ── CELL 1: Setup ──────────────────────────────────────────────
!pip install -q ultralytics
from google.colab import drive
drive.mount('/content/drive')

# ── CELL 2: Evaluate Violence Classifier ──────────────────────
from ultralytics import YOLO

violence_model = YOLO('/content/drive/MyDrive/violence_classifier_best.pt')
violence_results = violence_model.val(
    data='/content/drive/MyDrive/violence_dataset/',
    imgsz=224,
    batch=32,
    device=0,
    plots=True,
    project='/content/eval_results',
    name='violence_eval',
)
print(f"Violence Classifier — Top-1 Accuracy: {violence_results.top1:.4f}")
print(f"Violence Classifier — Top-5 Accuracy: {violence_results.top5:.4f}")

# ── CELL 3: Evaluate Fire v2 Model ───────────────────────────
fire_v2_model = YOLO('/content/drive/MyDrive/fire_smoke_best_v2.pt')
fire_v2_results = fire_v2_model.val(
    data='/content/drive/MyDrive/fire_dataset/data.yaml',
    imgsz=640,
    batch=16,
    device=0,
    plots=True,
    project='/content/eval_results',
    name='fire_v2_eval',
)
print(f"Fire v2 — mAP@50: {fire_v2_results.box.map50:.4f}")
print(f"Fire v2 — mAP@50-95: {fire_v2_results.box.map:.4f}")
print(f"Fire v2 — Precision: {fire_v2_results.box.mp:.4f}")
print(f"Fire v2 — Recall: {fire_v2_results.box.mr:.4f}")

# ── CELL 4: Evaluate Fire v1 (Baseline Comparison) ───────────
fire_v1_model = YOLO('/content/drive/MyDrive/fire_smoke_best.pt')
fire_v1_results = fire_v1_model.val(
    data='/content/drive/MyDrive/fire_dataset/data.yaml',
    imgsz=640,
    batch=16,
    device=0,
    plots=True,
    project='/content/eval_results',
    name='fire_v1_eval',
)
print(f"Fire v1 — mAP@50: {fire_v1_results.box.map50:.4f}")
print(f"Fire v1 — mAP@50-95: {fire_v1_results.box.map:.4f}")

# ── CELL 5: v1 vs v2 Comparison ──────────────────────────────
print("\\n" + "═" * 50)
print("  FIRE MODEL COMPARISON: v1 vs v2")
print("═" * 50)
v1_map = fire_v1_results.box.map50
v2_map = fire_v2_results.box.map50
improvement = v2_map - v1_map
print(f"  v1 mAP@50: {v1_map:.4f}")
print(f"  v2 mAP@50: {v2_map:.4f}")
print(f"  Improvement: {'+' if improvement > 0 else ''}{improvement:.4f}")
print("═" * 50)

# ── CELL 6: Evaluate Weapon Detection Model ───────────────────
weapon_model = YOLO('/content/drive/MyDrive/weapon_detection_best.pt')
weapon_results = weapon_model.val(
    data='/content/drive/MyDrive/weapon_dataset/data.yaml',
    imgsz=640,
    batch=16,
    device=0,
    plots=True,
    project='/content/eval_results',
    name='weapon_eval',
)
print(f"Weapon — mAP@50: {weapon_results.box.map50:.4f}")
print(f"Weapon — Precision: {weapon_results.box.mp:.4f}")
print(f"Weapon — Recall: {weapon_results.box.mr:.4f}")

# ── CELL 7: Download All Results ──────────────────────────────
import shutil
shutil.make_archive('/content/eval_results_all', 'zip', '/content/eval_results')
from google.colab import files
files.download('/content/eval_results_all.zip')
print("✅ All evaluation results downloaded!")
'''
    print(colab_code)
    return colab_code


def main():
    parser = argparse.ArgumentParser(
        description="VisionGuard Model Evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--model", type=str, help="Path to .pt model weights")
    parser.add_argument("--data", type=str, help="Path to validation dataset")
    parser.add_argument("--task", choices=["detect", "classify"], default="detect",
                       help="Task type: detect or classify")
    parser.add_argument("--output", type=str, default="./eval_results",
                       help="Output directory for results")
    parser.add_argument("--imgsz", type=int, default=640,
                       help="Input image size")
    parser.add_argument("--device", type=str, default="auto",
                       help="Device: auto, 0, cpu")
    parser.add_argument("--batch", type=int, default=16,
                       help="Batch size")
    parser.add_argument("--compare", nargs=2, metavar=("V1_JSON", "V2_JSON"),
                       help="Compare two metrics JSON files")
    parser.add_argument("--colab-code", action="store_true",
                       help="Print ready-to-paste Colab notebook code")
    
    args = parser.parse_args()
    
    if args.colab_code:
        generate_colab_notebook_code()
        return
    
    if args.compare:
        with open(args.compare[0]) as f:
            v1 = json.load(f)
        with open(args.compare[1]) as f:
            v2 = json.load(f)
        compare_models(v1, v2)
        return
    
    if not args.model or not args.data:
        parser.print_help()
        print("\nError: --model and --data are required for evaluation.")
        sys.exit(1)
    
    evaluate_model(
        model_path=args.model,
        data_path=args.data,
        task=args.task,
        output_dir=args.output,
        img_size=args.imgsz,
        device=args.device,
        batch_size=args.batch,
    )


if __name__ == "__main__":
    main()
