"""
VisionGuard — Dataset Integrity Scanner & Cleaner
===================================================
Areeba's Day 1 Task: Corrupt file scanner using cv2.imread

This script performs three critical data quality operations:
  1. Corrupt Image Removal — Detects and deletes 0-byte / unreadable images
  2. Duplicate Image Removal — Uses MD5 hashing to find and remove exact duplicates
  3. YOLO Label Audit — Validates bounding box annotations are within [0,1] range

Usage:
  python corrupt_file_scanner.py --dataset "path/to/dataset"
  python corrupt_file_scanner.py --dataset "path/to/dataset" --dry-run
  python corrupt_file_scanner.py --dataset "path/to/dataset" --report report.json
"""

import os
import sys
import cv2
import json
import hashlib
import argparse
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("DatasetScanner")

# ═══════════════════════════════════════════════════════
# IMAGE EXTENSIONS
# ═══════════════════════════════════════════════════════
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


def compute_file_hash(file_path: str) -> str:
    """Compute MD5 hash of file bytes (fast, for deduplication)."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def scan_and_clean_images(dataset_dir: str, dry_run: bool = False) -> dict:
    """
    Scan dataset directory for corrupt/duplicate images.
    
    Args:
        dataset_dir: Root directory of the dataset
        dry_run: If True, only report issues without deleting files
    
    Returns:
        Dictionary with scan statistics and details
    """
    stats = {
        "total_images_scanned": 0,
        "corrupt_images": 0,
        "zero_byte_images": 0,
        "duplicate_images": 0,
        "valid_images": 0,
        "total_freed_bytes": 0,
        "corrupt_files": [],
        "zero_byte_files": [],
        "duplicate_files": [],
    }
    
    seen_hashes = {}  # hash -> first_seen_path
    
    logger.info("=" * 60)
    logger.info("  VisionGuard Dataset Integrity Scanner")
    logger.info("=" * 60)
    logger.info(f"  Scanning: {dataset_dir}")
    logger.info(f"  Mode: {'DRY RUN (no deletions)' if dry_run else 'LIVE (will delete bad files)'}")
    logger.info("=" * 60)
    
    for root, dirs, files in os.walk(dataset_dir):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in IMAGE_EXTENSIONS:
                continue
            
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)
            stats["total_images_scanned"] += 1
            
            # ─── Check 1: Zero-byte files ───
            if file_size == 0:
                stats["zero_byte_images"] += 1
                stats["zero_byte_files"].append(file_path)
                stats["total_freed_bytes"] += file_size
                logger.warning(f"  ❌ ZERO-BYTE: {file_path}")
                if not dry_run:
                    os.remove(file_path)
                continue
            
            # ─── Check 2: Corrupt image (cv2 cannot read) ───
            try:
                img = cv2.imread(file_path)
                if img is None or img.size == 0:
                    stats["corrupt_images"] += 1
                    stats["corrupt_files"].append(file_path)
                    stats["total_freed_bytes"] += file_size
                    logger.warning(f"  ❌ CORRUPT: {file_path}")
                    if not dry_run:
                        os.remove(file_path)
                    continue
            except Exception as e:
                stats["corrupt_images"] += 1
                stats["corrupt_files"].append(file_path)
                stats["total_freed_bytes"] += file_size
                logger.warning(f"  ❌ READ ERROR: {file_path} ({e})")
                if not dry_run:
                    os.remove(file_path)
                continue
            
            # ─── Check 3: Duplicate detection via MD5 hash ───
            file_hash = compute_file_hash(file_path)
            if file_hash in seen_hashes:
                stats["duplicate_images"] += 1
                stats["duplicate_files"].append({
                    "duplicate": file_path,
                    "original": seen_hashes[file_hash],
                })
                stats["total_freed_bytes"] += file_size
                logger.warning(f"  🔄 DUPLICATE: {file_path}")
                logger.warning(f"     Original:  {seen_hashes[file_hash]}")
                if not dry_run:
                    os.remove(file_path)
                continue
            
            seen_hashes[file_hash] = file_path
            stats["valid_images"] += 1
    
    return stats


def audit_yolo_labels(dataset_dir: str, dry_run: bool = False) -> dict:
    """
    Audit YOLO-format .txt label files for invalid bounding box annotations.
    
    Validates:
    - Each line has exactly 5 values: class_id x_center y_center width height
    - All coordinates are normalized within [0, 1]
    - class_id is a non-negative integer
    
    Returns:
        Dictionary with label audit statistics
    """
    stats = {
        "total_labels_scanned": 0,
        "labels_with_errors": 0,
        "total_invalid_lines": 0,
        "total_valid_lines": 0,
        "fixed_files": [],
        "empty_after_fix": [],
    }
    
    logger.info("\n" + "=" * 60)
    logger.info("  YOLO Label Annotation Audit")
    logger.info("=" * 60)
    
    for root, dirs, files in os.walk(dataset_dir):
        for file in files:
            if not file.endswith(".txt") or file == "classes.txt":
                continue
            
            file_path = os.path.join(root, file)
            stats["total_labels_scanned"] += 1
            
            valid_lines = []
            invalid_count = 0
            
            try:
                with open(file_path, "r") as f:
                    lines = f.readlines()
            except Exception as e:
                logger.warning(f"  ⚠️  Cannot read: {file_path} ({e})")
                continue
            
            for line_num, line in enumerate(lines, 1):
                parts = line.strip().split()
                if len(parts) != 5:
                    invalid_count += 1
                    continue
                
                try:
                    cls = int(float(parts[0]))
                    x, y, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                    
                    if cls < 0:
                        invalid_count += 1
                        continue
                    
                    if 0 <= x <= 1 and 0 <= y <= 1 and 0 <= w <= 1 and 0 <= h <= 1:
                        valid_lines.append(line)
                    else:
                        invalid_count += 1
                except (ValueError, IndexError):
                    invalid_count += 1
            
            stats["total_valid_lines"] += len(valid_lines)
            stats["total_invalid_lines"] += invalid_count
            
            if invalid_count > 0:
                stats["labels_with_errors"] += 1
                stats["fixed_files"].append({
                    "file": file_path,
                    "removed_lines": invalid_count,
                    "kept_lines": len(valid_lines),
                })
                logger.warning(f"  🔧 FIXED: {file_path} — removed {invalid_count} invalid annotations")
                
                if not dry_run:
                    with open(file_path, "w") as f:
                        f.writelines(valid_lines)
                
                if len(valid_lines) == 0:
                    stats["empty_after_fix"].append(file_path)
                    logger.warning(f"  ⚠️  WARNING: {file_path} is now EMPTY after removing invalid lines!")
    
    return stats


def analyze_class_distribution(dataset_dir: str) -> dict:
    """
    Analyze class distribution across all YOLO label files.
    Useful for identifying class imbalance before training.
    """
    class_counts = defaultdict(int)
    total_annotations = 0
    
    for root, dirs, files in os.walk(dataset_dir):
        for file in files:
            if not file.endswith(".txt") or file == "classes.txt":
                continue
            
            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) == 5:
                            cls = int(float(parts[0]))
                            class_counts[cls] += 1
                            total_annotations += 1
            except Exception:
                continue
    
    return {
        "class_counts": dict(class_counts),
        "total_annotations": total_annotations,
    }


def print_report(image_stats: dict, label_stats: dict, class_dist: dict):
    """Print a formatted summary report."""
    print(f"\n{'═' * 60}")
    print(f"  📊 DATASET INTEGRITY REPORT")
    print(f"{'═' * 60}")
    
    print(f"\n  📸 IMAGE SCAN RESULTS:")
    print(f"  {'─' * 40}")
    print(f"  Total images scanned:   {image_stats['total_images_scanned']:,}")
    print(f"  ✅ Valid images:         {image_stats['valid_images']:,}")
    print(f"  ❌ Corrupt images:       {image_stats['corrupt_images']:,}")
    print(f"  ❌ Zero-byte images:     {image_stats['zero_byte_images']:,}")
    print(f"  🔄 Duplicate images:     {image_stats['duplicate_images']:,}")
    freed_mb = image_stats['total_freed_bytes'] / (1024 * 1024)
    print(f"  💾 Space freed:          {freed_mb:.2f} MB")
    
    print(f"\n  📝 LABEL AUDIT RESULTS:")
    print(f"  {'─' * 40}")
    print(f"  Total labels scanned:   {label_stats['total_labels_scanned']:,}")
    print(f"  Labels with errors:     {label_stats['labels_with_errors']:,}")
    print(f"  Invalid lines removed:  {label_stats['total_invalid_lines']:,}")
    print(f"  Valid lines kept:       {label_stats['total_valid_lines']:,}")
    
    if label_stats['empty_after_fix']:
        print(f"  ⚠️  Empty labels after fix: {len(label_stats['empty_after_fix'])}")
    
    if class_dist['total_annotations'] > 0:
        print(f"\n  📊 CLASS DISTRIBUTION:")
        print(f"  {'─' * 40}")
        for cls_id, count in sorted(class_dist['class_counts'].items()):
            pct = (count / class_dist['total_annotations']) * 100
            bar = "█" * int(pct / 2)
            print(f"  Class {cls_id:3d}: {count:6,} ({pct:5.1f}%) {bar}")
    
    print(f"\n{'═' * 60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="VisionGuard Dataset Integrity Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python corrupt_file_scanner.py --dataset ./fire_dataset
  python corrupt_file_scanner.py --dataset ./fire_dataset --dry-run
  python corrupt_file_scanner.py --dataset ./fire_dataset --report scan_report.json
        """
    )
    parser.add_argument("--dataset", type=str, required=True,
                       help="Path to the dataset directory to scan")
    parser.add_argument("--dry-run", action="store_true",
                       help="Only report issues without deleting files")
    parser.add_argument("--report", type=str, default=None,
                       help="Save detailed JSON report to this file")
    parser.add_argument("--skip-labels", action="store_true",
                       help="Skip YOLO label audit (images only)")
    
    args = parser.parse_args()
    
    dataset_dir = os.path.abspath(args.dataset)
    if not os.path.isdir(dataset_dir):
        logger.error(f"Dataset directory not found: {dataset_dir}")
        sys.exit(1)
    
    # Run image scan
    image_stats = scan_and_clean_images(dataset_dir, dry_run=args.dry_run)
    
    # Run label audit
    label_stats = {"total_labels_scanned": 0, "labels_with_errors": 0,
                   "total_invalid_lines": 0, "total_valid_lines": 0,
                   "fixed_files": [], "empty_after_fix": []}
    if not args.skip_labels:
        label_stats = audit_yolo_labels(dataset_dir, dry_run=args.dry_run)
    
    # Analyze class distribution
    class_dist = analyze_class_distribution(dataset_dir)
    
    # Print report
    print_report(image_stats, label_stats, class_dist)
    
    # Save JSON report
    if args.report:
        report = {
            "scan_timestamp": datetime.now().isoformat(),
            "dataset_path": dataset_dir,
            "dry_run": args.dry_run,
            "image_stats": image_stats,
            "label_stats": label_stats,
            "class_distribution": class_dist,
        }
        with open(args.report, "w") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Report saved to: {args.report}")


if __name__ == "__main__":
    main()
