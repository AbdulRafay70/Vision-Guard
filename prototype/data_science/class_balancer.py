"""
VisionGuard — Class Balancer & Dataset Equalizer
==================================================
Areeba's Day 2 Task: Class-balance the Weapon dataset

Analyzes class distribution and balances minority classes through:
  1. Oversampling (duplicate + augment minority class images)
  2. Undersampling (randomly remove majority class images)
  3. Hybrid (oversample minority, undersample majority)

Supports YOLO-format datasets with corresponding .txt label files.

Usage:
  python class_balancer.py --dataset "path/to/weapon_dataset" --strategy oversample
  python class_balancer.py --dataset "path/to/dataset" --strategy hybrid --output balanced_dataset
  python class_balancer.py --dataset "path/to/dataset" --analyze-only
"""

import os
import sys
import cv2
import random
import shutil
import argparse
import logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ClassBalancer")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# Try importing albumentations for smart oversampling
try:
    import albumentations as A
    AUGMENT_AVAILABLE = True
    oversample_transform = A.Compose([
        A.HorizontalFlip(p=0.5),
        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.4),
        A.ShiftScaleRotate(shift_limit=0.05, scale_limit=0.1, rotate_limit=10, p=0.3),
        A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=15, val_shift_limit=10, p=0.3),
    ], bbox_params=A.BboxParams(format="yolo", label_fields=["class_labels"], min_visibility=0.3))
except ImportError:
    AUGMENT_AVAILABLE = False
    oversample_transform = None


def analyze_dataset(dataset_dir: str) -> dict:
    """
    Analyze class distribution across YOLO label files.
    
    Returns:
        Dictionary mapping class_id -> list of (image_path, label_path) tuples
    """
    class_files = defaultdict(list)  # class_id -> [(img_path, label_path), ...]
    class_counts = defaultdict(int)
    
    # Look for images and their corresponding labels
    for root, dirs, files in os.walk(dataset_dir):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in IMAGE_EXTENSIONS:
                continue
            
            img_path = os.path.join(root, file)
            label_path = os.path.splitext(img_path)[0] + ".txt"
            
            if not os.path.exists(label_path):
                # Try looking in parallel labels directory
                labels_dir = root.replace("images", "labels")
                label_path = os.path.join(labels_dir, os.path.splitext(file)[0] + ".txt")
            
            if not os.path.exists(label_path):
                continue
            
            # Read label to find classes present
            try:
                with open(label_path, "r") as f:
                    classes_in_image = set()
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) == 5:
                            cls = int(float(parts[0]))
                            classes_in_image.add(cls)
                            class_counts[cls] += 1
                    
                    for cls in classes_in_image:
                        class_files[cls].append((img_path, label_path))
            except Exception:
                continue
    
    return {
        "class_files": dict(class_files),
        "class_counts": dict(class_counts),
    }


def print_analysis(analysis: dict, classes_txt: str = None):
    """Print formatted class distribution analysis."""
    class_counts = analysis["class_counts"]
    class_files = analysis["class_files"]
    
    # Try to load class names
    class_names = {}
    if classes_txt and os.path.exists(classes_txt):
        with open(classes_txt, "r") as f:
            for i, line in enumerate(f):
                class_names[i] = line.strip()
    
    print(f"\n{'═' * 60}")
    print(f"  📊 CLASS DISTRIBUTION ANALYSIS")
    print(f"{'═' * 60}")
    
    if not class_counts:
        print(f"  ⚠️  No labeled images found!")
        print(f"{'═' * 60}\n")
        return
    
    total_annotations = sum(class_counts.values())
    max_count = max(class_counts.values())
    min_count = min(class_counts.values())
    
    print(f"  Total annotations: {total_annotations:,}")
    print(f"  Total classes:     {len(class_counts)}")
    print(f"  Max class count:   {max_count:,}")
    print(f"  Min class count:   {min_count:,}")
    print(f"  Imbalance ratio:   {max_count / max(min_count, 1):.1f}x")
    print(f"  {'─' * 50}")
    
    for cls_id in sorted(class_counts.keys()):
        count = class_counts[cls_id]
        images = len(class_files.get(cls_id, []))
        bar_len = int((count / max_count) * 30)
        bar = "█" * bar_len + "░" * (30 - bar_len)
        pct = (count / total_annotations) * 100
        name = class_names.get(cls_id, f"class_{cls_id}")
        
        status = "✅" if count >= max_count * 0.5 else "⚠️ LOW"
        print(f"  Class {cls_id} ({name:15s}): {count:6,} annot | {images:5,} imgs | {pct:5.1f}% | {bar} {status}")
    
    print(f"{'═' * 60}\n")


def balance_dataset(dataset_dir: str, output_dir: str, strategy: str = "oversample",
                    target_count: int = None) -> dict:
    """
    Balance dataset classes.
    
    Args:
        dataset_dir: Source dataset directory
        output_dir: Output directory for balanced dataset
        strategy: "oversample", "undersample", or "hybrid"
        target_count: Target count per class (auto-calculated if None)
    
    Returns:
        Statistics dictionary
    """
    os.makedirs(output_dir, exist_ok=True)
    
    analysis = analyze_dataset(dataset_dir)
    class_files = analysis["class_files"]
    class_counts = analysis["class_counts"]
    
    if not class_counts:
        logger.error("No labeled data found!")
        return {}
    
    max_count = max(len(files) for files in class_files.values())
    min_count = min(len(files) for files in class_files.values())
    
    # Calculate target
    if target_count is None:
        if strategy == "oversample":
            target_count = max_count
        elif strategy == "undersample":
            target_count = min_count
        elif strategy == "hybrid":
            # Target is the median
            counts = sorted(len(f) for f in class_files.values())
            target_count = counts[len(counts) // 2]
    
    logger.info(f"Balancing strategy: {strategy}")
    logger.info(f"Target per class: {target_count:,} images")
    
    stats = {"strategy": strategy, "target_count": target_count, "classes": {}}
    
    for cls_id, files in class_files.items():
        current = len(files)
        cls_output = os.path.join(output_dir, f"class_{cls_id}")
        os.makedirs(cls_output, exist_ok=True)
        
        if current >= target_count and strategy in ("undersample", "hybrid"):
            # Undersample: randomly select target_count files
            selected = random.sample(files, target_count)
            for img_path, label_path in selected:
                base = os.path.basename(img_path)
                shutil.copy2(img_path, os.path.join(cls_output, base))
                if os.path.exists(label_path):
                    label_base = os.path.splitext(base)[0] + ".txt"
                    shutil.copy2(label_path, os.path.join(cls_output, label_base))
            
            stats["classes"][cls_id] = {
                "original": current,
                "final": target_count,
                "action": "undersampled",
            }
            
        elif current < target_count and strategy in ("oversample", "hybrid"):
            # Copy all originals first
            for img_path, label_path in files:
                base = os.path.basename(img_path)
                shutil.copy2(img_path, os.path.join(cls_output, base))
                if os.path.exists(label_path):
                    label_base = os.path.splitext(base)[0] + ".txt"
                    shutil.copy2(label_path, os.path.join(cls_output, label_base))
            
            # Oversample to reach target
            needed = target_count - current
            aug_count = 0
            
            while aug_count < needed:
                # Pick random image from this class
                img_path, label_path = random.choice(files)
                img = cv2.imread(img_path)
                if img is None:
                    continue
                
                ext = os.path.splitext(img_path)[1]
                aug_name = f"aug_{aug_count:05d}_{os.path.basename(img_path)}"
                aug_path = os.path.join(cls_output, aug_name)
                
                if AUGMENT_AVAILABLE and oversample_transform:
                    # Read labels for bbox-safe augmentation
                    bboxes, class_labels = [], []
                    if os.path.exists(label_path):
                        with open(label_path, "r") as f:
                            for line in f:
                                parts = line.strip().split()
                                if len(parts) == 5:
                                    bboxes.append([float(x) for x in parts[1:5]])
                                    class_labels.append(int(float(parts[0])))
                    
                    try:
                        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        if bboxes:
                            result = oversample_transform(
                                image=img_rgb, bboxes=bboxes, class_labels=class_labels
                            )
                            aug_img = cv2.cvtColor(result["image"], cv2.COLOR_RGB2BGR)
                            # Save augmented labels
                            aug_label_path = os.path.join(cls_output, os.path.splitext(aug_name)[0] + ".txt")
                            with open(aug_label_path, "w") as f:
                                for bbox, cls in zip(result["bboxes"], result["class_labels"]):
                                    f.write(f"{cls} {bbox[0]:.6f} {bbox[1]:.6f} {bbox[2]:.6f} {bbox[3]:.6f}\n")
                        else:
                            result = oversample_transform(image=img_rgb, bboxes=[], class_labels=[])
                            aug_img = cv2.cvtColor(result["image"], cv2.COLOR_RGB2BGR)
                    except Exception:
                        aug_img = img  # Fallback to simple copy
                else:
                    # Simple copy + random flip if no albumentations
                    aug_img = cv2.flip(img, random.choice([-1, 0, 1]))
                
                cv2.imwrite(aug_path, aug_img)
                aug_count += 1
            
            stats["classes"][cls_id] = {
                "original": current,
                "final": current + aug_count,
                "augmented": aug_count,
                "action": "oversampled",
            }
        else:
            # Already at target, just copy
            for img_path, label_path in files:
                base = os.path.basename(img_path)
                shutil.copy2(img_path, os.path.join(cls_output, base))
                if os.path.exists(label_path):
                    label_base = os.path.splitext(base)[0] + ".txt"
                    shutil.copy2(label_path, os.path.join(cls_output, label_base))
            
            stats["classes"][cls_id] = {
                "original": current,
                "final": current,
                "action": "kept_as_is",
            }
    
    # Print results
    print(f"\n{'═' * 60}")
    print(f"  📊 CLASS BALANCING RESULTS")
    print(f"{'═' * 60}")
    print(f"  Strategy: {strategy}")
    print(f"  Target:   {target_count:,} per class")
    print(f"  {'─' * 45}")
    
    for cls_id, cls_stats in sorted(stats["classes"].items()):
        action = cls_stats["action"]
        orig = cls_stats["original"]
        final = cls_stats["final"]
        print(f"  Class {cls_id}: {orig:,} → {final:,}  ({action})")
    
    print(f"\n  Output: {output_dir}")
    print(f"{'═' * 60}\n")
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="VisionGuard Class Balancer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze class distribution
  python class_balancer.py --dataset ./weapon_dataset --analyze-only

  # Oversample minority classes to match majority
  python class_balancer.py --dataset ./weapon_dataset --strategy oversample --output ./balanced

  # Hybrid: oversample minority + undersample majority
  python class_balancer.py --dataset ./weapon_dataset --strategy hybrid --output ./balanced
        """
    )
    parser.add_argument("--dataset", type=str, required=True,
                       help="Path to YOLO-format dataset")
    parser.add_argument("--output", type=str, default=None,
                       help="Output directory for balanced dataset")
    parser.add_argument("--strategy", choices=["oversample", "undersample", "hybrid"],
                       default="oversample", help="Balancing strategy")
    parser.add_argument("--target", type=int, default=None,
                       help="Target count per class (auto if not specified)")
    parser.add_argument("--analyze-only", action="store_true",
                       help="Only analyze class distribution")
    parser.add_argument("--classes-txt", type=str, default=None,
                       help="Path to classes.txt for human-readable names")
    
    args = parser.parse_args()
    
    analysis = analyze_dataset(args.dataset)
    print_analysis(analysis, args.classes_txt)
    
    if args.analyze_only:
        return
    
    if not args.output:
        args.output = args.dataset + "_balanced"
    
    balance_dataset(
        dataset_dir=args.dataset,
        output_dir=args.output,
        strategy=args.strategy,
        target_count=args.target,
    )


if __name__ == "__main__":
    main()
