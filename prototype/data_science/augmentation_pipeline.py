"""
VisionGuard — Albumentations Weather Augmentation Pipeline
============================================================
Areeba's Day 1 Task: Weather augmentation notebook for data robustness

Generates synthetic weather variations (rain, fog, shadow, brightness) to
make fire/smoke/violence models robust to real-world conditions.

Supports:
  - Rain overlay simulation
  - Fog/haze injection
  - Random shadow casting
  - Brightness & contrast variation
  - Shift, scale, rotation for viewpoint diversity
  - Class-aware balancing (oversample minority classes)

Usage:
  python augmentation_pipeline.py --input "path/to/images" --output "path/to/augmented" --multiply 3
  python augmentation_pipeline.py --input "path/to/dataset" --output "path/to/augmented" --multiply 5 --with-labels
"""

import os
import sys
import cv2
import argparse
import logging
import random
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("AugmentationPipeline")

# ═══════════════════════════════════════════════════════
# CHECK ALBUMENTATIONS AVAILABILITY
# ═══════════════════════════════════════════════════════
try:
    import albumentations as A
    ALBUMENTATIONS_AVAILABLE = True
except ImportError:
    ALBUMENTATIONS_AVAILABLE = False
    logger.warning("albumentations not installed. Install with: pip install albumentations")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


# ═══════════════════════════════════════════════════════
# AUGMENTATION TRANSFORMS
# ═══════════════════════════════════════════════════════

def get_weather_transform_pipeline():
    """
    Create the main weather augmentation pipeline.
    Designed for outdoor surveillance/CCTV datasets.
    """
    return A.Compose([
        # ── Geometric transforms ──
        A.HorizontalFlip(p=0.5),
        A.ShiftScaleRotate(
            shift_limit=0.0625,
            scale_limit=0.1,
            rotate_limit=15,
            border_mode=cv2.BORDER_REFLECT_101,
            p=0.3,
        ),
        
        # ── Brightness & Contrast (simulate day/night) ──
        A.RandomBrightnessContrast(
            brightness_limit=0.25,
            contrast_limit=0.25,
            p=0.4,
        ),
        
        # ── Weather: Rain ──
        A.RandomRain(
            brightness_coefficient=0.9,
            drop_length=20,
            drop_width=1,
            drop_color=(200, 200, 200),
            blur_value=3,
            rain_type="default",
            p=0.2,
        ),
        
        # ── Weather: Fog / Haze ──
        A.RandomFog(
            fog_coef_lower=0.1,
            fog_coef_upper=0.35,
            alpha_coef=0.1,
            p=0.2,
        ),
        
        # ── Weather: Shadows ──
        A.RandomShadow(
            shadow_roi=(0, 0.5, 1, 1),
            num_shadows_lower=1,
            num_shadows_upper=3,
            shadow_dimension=5,
            p=0.25,
        ),
        
        # ── Color Jitter (simulate different cameras) ──
        A.HueSaturationValue(
            hue_shift_limit=10,
            sat_shift_limit=20,
            val_shift_limit=15,
            p=0.3,
        ),
        
        # ── Noise & Blur (simulate low-quality CCTV) ──
        A.OneOf([
            A.GaussNoise(var_limit=(10.0, 50.0), p=1.0),
            A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.3), p=1.0),
        ], p=0.2),
        
        A.OneOf([
            A.MotionBlur(blur_limit=5, p=1.0),
            A.GaussianBlur(blur_limit=(3, 5), p=1.0),
        ], p=0.15),
        
        # ── JPEG Compression (simulate compression artifacts) ──
        A.ImageCompression(quality_lower=60, quality_upper=95, p=0.2),
    ])


def get_night_transform_pipeline():
    """Additional transforms specifically for simulating night-time conditions."""
    return A.Compose([
        A.RandomBrightnessContrast(
            brightness_limit=(-0.4, -0.1),
            contrast_limit=(-0.2, 0.1),
            p=0.8,
        ),
        A.RandomGamma(gamma_limit=(40, 80), p=0.5),
        A.GaussNoise(var_limit=(20.0, 80.0), p=0.5),
    ])


def get_bbox_safe_transform_pipeline():
    """
    Augmentation pipeline that preserves YOLO bounding box annotations.
    Uses albumentations BboxParams for coordinate transformation.
    """
    return A.Compose([
        A.HorizontalFlip(p=0.5),
        A.ShiftScaleRotate(
            shift_limit=0.05,
            scale_limit=0.1,
            rotate_limit=10,
            border_mode=cv2.BORDER_REFLECT_101,
            p=0.3,
        ),
        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.4),
        A.RandomRain(brightness_coefficient=0.9, drop_length=20, blur_value=3, p=0.15),
        A.RandomFog(fog_coef_lower=0.1, fog_coef_upper=0.3, alpha_coef=0.1, p=0.15),
        A.RandomShadow(num_shadows_lower=1, num_shadows_upper=2, p=0.2),
    ], bbox_params=A.BboxParams(
        format="yolo",
        label_fields=["class_labels"],
        min_visibility=0.3,
    ))


# ═══════════════════════════════════════════════════════
# AUGMENTATION ENGINE
# ═══════════════════════════════════════════════════════

def read_yolo_labels(label_path: str):
    """Read YOLO format labels from a .txt file."""
    bboxes = []
    class_labels = []
    
    if not os.path.exists(label_path):
        return bboxes, class_labels
    
    with open(label_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 5:
                cls = int(float(parts[0]))
                x, y, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                bboxes.append([x, y, w, h])
                class_labels.append(cls)
    
    return bboxes, class_labels


def write_yolo_labels(label_path: str, bboxes: list, class_labels: list):
    """Write YOLO format labels to a .txt file."""
    with open(label_path, "w") as f:
        for bbox, cls in zip(bboxes, class_labels):
            x, y, w, h = bbox
            f.write(f"{cls} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")


def augment_dataset(input_dir: str, output_dir: str, multiplier: int = 3,
                    with_labels: bool = False, include_night: bool = True):
    """
    Augment entire dataset with weather variations.
    
    Args:
        input_dir: Source image directory
        output_dir: Destination for augmented images
        multiplier: Number of augmented copies per image
        with_labels: Whether to also transform YOLO bounding box labels
        include_night: Include night-time simulation augmentations
    """
    if not ALBUMENTATIONS_AVAILABLE:
        logger.error("albumentations is required! Install: pip install albumentations")
        sys.exit(1)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Select pipeline
    if with_labels:
        transform = get_bbox_safe_transform_pipeline()
    else:
        transform = get_weather_transform_pipeline()
    
    night_transform = get_night_transform_pipeline() if include_night else None
    
    # Collect image files
    image_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if os.path.splitext(file)[1].lower() in IMAGE_EXTENSIONS:
                image_files.append(os.path.join(root, file))
    
    total = len(image_files)
    logger.info(f"Found {total:,} images in {input_dir}")
    logger.info(f"Generating {multiplier}x augmentations = {total * multiplier:,} new images")
    
    created = 0
    errors = 0
    
    for idx, img_path in enumerate(image_files):
        img = cv2.imread(img_path)
        if img is None:
            errors += 1
            continue
        
        # Convert BGR to RGB for albumentations
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        ext = os.path.splitext(img_path)[1]
        
        # Copy original to output
        out_original = os.path.join(output_dir, f"{base_name}{ext}")
        cv2.imwrite(out_original, img)
        
        # Copy original label if exists
        if with_labels:
            label_path = img_path.replace(ext, ".txt")
            bboxes, class_labels = read_yolo_labels(label_path)
            if os.path.exists(label_path):
                out_label = os.path.join(output_dir, f"{base_name}.txt")
                shutil.copy2(label_path, out_label)
        
        # Generate augmentations
        for i in range(multiplier):
            try:
                if with_labels and bboxes:
                    augmented = transform(
                        image=img_rgb,
                        bboxes=bboxes,
                        class_labels=class_labels,
                    )
                    aug_img = augmented["image"]
                    aug_bboxes = augmented["bboxes"]
                    aug_classes = augmented["class_labels"]
                else:
                    augmented = transform(image=img_rgb)
                    aug_img = augmented["image"]
                
                # Optionally apply night-time simulation (20% of augments)
                if night_transform and random.random() < 0.2:
                    night_result = night_transform(image=aug_img)
                    aug_img = night_result["image"]
                
                # Convert back to BGR for saving
                aug_bgr = cv2.cvtColor(aug_img, cv2.COLOR_RGB2BGR)
                
                aug_name = f"{base_name}_aug{i:02d}{ext}"
                aug_path = os.path.join(output_dir, aug_name)
                cv2.imwrite(aug_path, aug_bgr)
                
                # Save augmented labels
                if with_labels and bboxes:
                    aug_label_path = os.path.join(output_dir, f"{base_name}_aug{i:02d}.txt")
                    write_yolo_labels(aug_label_path, aug_bboxes, aug_classes)
                
                created += 1
                
            except Exception as e:
                errors += 1
                logger.debug(f"Augmentation error for {img_path} (aug {i}): {e}")
        
        # Progress
        if (idx + 1) % 100 == 0 or idx == total - 1:
            pct = ((idx + 1) / total) * 100
            logger.info(f"  Progress: {idx+1:,}/{total:,} ({pct:.1f}%) — Created: {created:,}")
    
    # Final report
    print(f"\n{'═' * 60}")
    print(f"  📊 AUGMENTATION COMPLETE")
    print(f"{'═' * 60}")
    print(f"  Original images:     {total:,}")
    print(f"  Augmented images:    {created:,}")
    print(f"  Total in output:     {total + created:,}")
    print(f"  Errors:              {errors:,}")
    print(f"  Output directory:    {output_dir}")
    print(f"{'═' * 60}\n")
    
    return {"original": total, "augmented": created, "errors": errors}


def analyze_class_balance(dataset_dir: str) -> dict:
    """
    Analyze class distribution for YOLO datasets.
    Reports per-class counts to identify imbalance.
    """
    class_counts = defaultdict(int)
    total_images_with_labels = 0
    
    for root, dirs, files in os.walk(dataset_dir):
        for file in files:
            if not file.endswith(".txt") or file == "classes.txt":
                continue
            
            label_path = os.path.join(root, file)
            try:
                with open(label_path, "r") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) == 5:
                            cls = int(float(parts[0]))
                            class_counts[cls] += 1
                total_images_with_labels += 1
            except Exception:
                continue
    
    print(f"\n{'═' * 60}")
    print(f"  📊 CLASS DISTRIBUTION ANALYSIS")
    print(f"{'═' * 60}")
    print(f"  Total labeled images: {total_images_with_labels:,}")
    print(f"  {'─' * 40}")
    
    if class_counts:
        max_count = max(class_counts.values())
        for cls_id, count in sorted(class_counts.items()):
            bar_len = int((count / max_count) * 30)
            bar = "█" * bar_len
            ratio = count / max_count
            balance = "✅" if ratio > 0.5 else "⚠️ UNDERREPRESENTED"
            print(f"  Class {cls_id:3d}: {count:6,} {bar} {balance}")
    
    print(f"{'═' * 60}\n")
    return dict(class_counts)


def main():
    parser = argparse.ArgumentParser(
        description="VisionGuard Weather Augmentation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic augmentation (3x multiply, images only)
  python augmentation_pipeline.py --input ./fire_dataset/images --output ./augmented --multiply 3

  # With YOLO label support
  python augmentation_pipeline.py --input ./dataset --output ./augmented --multiply 5 --with-labels

  # Just analyze class balance
  python augmentation_pipeline.py --input ./dataset --analyze-only
        """
    )
    parser.add_argument("--input", type=str, required=True,
                       help="Input dataset directory")
    parser.add_argument("--output", type=str, default=None,
                       help="Output directory for augmented images")
    parser.add_argument("--multiply", type=int, default=3,
                       help="Number of augmented copies per image (default: 3)")
    parser.add_argument("--with-labels", action="store_true",
                       help="Also transform YOLO bounding box labels")
    parser.add_argument("--no-night", action="store_true",
                       help="Skip night-time simulation augmentations")
    parser.add_argument("--analyze-only", action="store_true",
                       help="Only analyze class distribution (no augmentation)")
    
    args = parser.parse_args()
    
    if args.analyze_only:
        analyze_class_balance(args.input)
        return
    
    if not args.output:
        args.output = args.input + "_augmented"
    
    augment_dataset(
        input_dir=args.input,
        output_dir=args.output,
        multiplier=args.multiply,
        with_labels=args.with_labels,
        include_night=not args.no_night,
    )


if __name__ == "__main__":
    main()
