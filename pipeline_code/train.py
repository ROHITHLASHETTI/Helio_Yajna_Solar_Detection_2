#!/usr/bin/env python3
"""
YOLOv12 Training Script v2 - Improved with Hard Negative Mining

Key improvements over v1:
1. Uses images from FN (false negative) samples for hard negative mining
2. Higher image resolution (1024) for better small panel detection
3. More aggressive augmentation for varied appearances
4. Focus on panels that look different from Roboflow training data

Run: CUDA_VISIBLE_DEVICES=1 python src/train_yolov12_v2.py
"""
import os
import json
import glob
import random
import yaml
import sys
import shutil
from pathlib import Path
from ultralytics import YOLO
from ultralytics import settings

# Try to import mlflow (optional)
try:
    import mlflow
    MLFLOW_AVAILABLE = True
    settings.update({'mlflow': True})
except ImportError:
    MLFLOW_AVAILABLE = False
    print("Warning: mlflow not installed, logging disabled")

class Logger(object):
    def __init__(self, log_file):
        self.terminal = sys.stdout
        self.log = open(log_file, "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()


def prepare_combined_dataset(
    base_dir='data_segmented',
    cache_dir='cache',
    fn_ids_file='outputs/misclassification_analysis/fn_sample_ids.txt',
    oversample_factor=5,
    include_fn_images=True
):
    """
    Creates a combined training set:
    1. Original annotated data from Roboflow (with oversampling)
    2. Hard negative mining from FN samples (images where solar was missed)
    """
    base_path = Path(base_dir)
    images_dir = base_path / 'images'
    labels_dir = base_path / 'labels'
    cache_path = Path(cache_dir)
    
    train_lines = []
    pos_count = 0
    neg_count = 0
    
    # Get all annotated images
    all_images = sorted(list(images_dir.glob('*.*')))
    
    print(f"Scanning {len(all_images)} annotated images...")
    
    for img_path in all_images:
        label_path = labels_dir / (img_path.stem + '.txt')
        
        has_solar = False
        if label_path.exists():
            with open(label_path, 'r') as f:
                content = f.read().strip()
                if content:
                    has_solar = True
                    pos_count += 1
        
        # Add original image
        train_lines.append(str(img_path.absolute()))
        
        # Oversample positives
        if has_solar:
            for _ in range(oversample_factor - 1):
                train_lines.append(str(img_path.absolute()))
        else:
            neg_count += 1
    
    print(f"  Positive samples: {pos_count}")
    print(f"  Negative samples: {neg_count}")
    
    # Add False Negative images for hard negative mining
    fn_images_added = 0
    if include_fn_images and Path(fn_ids_file).exists():
        print(f"\nAdding FN images from {fn_ids_file} for hard negative mining...")
        
        # Create hard_negatives folder
        hard_neg_dir = base_path / 'hard_negatives'
        hard_neg_dir.mkdir(exist_ok=True)
        hard_neg_labels_dir = base_path / 'labels_hard_neg'
        hard_neg_labels_dir.mkdir(exist_ok=True)
        
        with open(fn_ids_file, 'r') as f:
            fn_ids = [int(float(x.strip())) for x in f.read().split(',') if x.strip()]
        
        print(f"  Found {len(fn_ids)} FN sample IDs")
        
        for sample_id in fn_ids[:100]:  # Limit to first 100 FN samples
            # Check if cached image exists
            cached_patterns = [
                cache_path / f"satellite_{sample_id}_*.jpg",
                cache_path / f"*_{sample_id}_*.jpg",
            ]
            
            for pattern in cached_patterns:
                matches = list(cache_path.glob(pattern.name))
                if matches:
                    # Copy to hard_negatives folder
                    src_img = matches[0]
                    dst_img = hard_neg_dir / f"fn_{sample_id}.jpg"
                    
                    if not dst_img.exists():
                        shutil.copy(src_img, dst_img)
                    
                    # Create empty label file (no annotations - model needs to learn these look different)
                    empty_label = hard_neg_labels_dir / f"fn_{sample_id}.txt"
                    empty_label.touch()
                    
                    # Add to training (as negative examples)
                    train_lines.append(str(dst_img.absolute()))
                    fn_images_added += 1
                    break
        
        print(f"  Added {fn_images_added} FN images as hard negatives")
    
    total = len(train_lines)
    print(f"\nTotal training images: {total}")
    print(f"  Original (oversampled): {total - fn_images_added}")
    print(f"  Hard negatives: {fn_images_added}")
    
    # Create new txt file
    txt_path = base_path / 'train_v2.txt'
    with open(txt_path, 'w') as f:
        f.write('\n'.join(train_lines))
    
    # Create new yaml
    new_yaml_path = base_path / 'data_v2.yaml'
    
    data_config = {
        'path': str(base_path.absolute()),
        'train': str(txt_path.absolute()),
        'val': str(images_dir.absolute()),
        'nc': 1,
        'names': ['solarpanel']
    }
    
    with open(new_yaml_path, 'w') as f:
        yaml.dump(data_config, f)
    
    return str(new_yaml_path)


def train(resume=False, epochs=150, model_size='yolo12x'):
    """
    Train YOLOv12/v11 model with improved settings.
    
    Args:
        resume: Resume from last checkpoint
        epochs: Number of training epochs
        model_size: Model size (yolo11x, yolo11l, yolo12x, etc.)
    """
    # Setup Logging
    log_dir = Path('outputs/training/yolov12_v2')
    log_dir.mkdir(parents=True, exist_ok=True)
    sys.stdout = Logger(log_dir / 'training_log.txt')
    sys.stderr = sys.stdout
    
    # Setup MLflow (if available)
    if MLFLOW_AVAILABLE:
        mlflow.set_tracking_uri("file:./mlruns")
        mlflow.set_experiment("Ideathon_Solar_Panel_v2")
    
    print("="*60)
    print("Solar Panel Detection Training v2")
    print("="*60)
    print(f"Model: {model_size}")
    print(f"Epochs: {epochs}")
    print(f"Resume: {resume}")
    print("="*60)
    
    # Prepare dataset with hard negative mining
    print("\n[1/3] Preparing combined dataset...")
    yaml_path = prepare_combined_dataset(
        base_dir='data_segmented',
        cache_dir='cache',
        fn_ids_file='outputs/misclassification_analysis/fn_sample_ids.txt',
        oversample_factor=5,
        include_fn_images=True
    )
    
    # Initialize model
    print(f"\n[2/3] Loading {model_size} model...")
    try:
        model = YOLO(f'{model_size}.pt')
    except Exception as e:
        print(f"Error loading {model_size}.pt: {e}")
        print("Falling back to yolo11m.pt...")
        model = YOLO('yolo11m.pt')
    
    # Enable MLflow autologging (if available)
    if MLFLOW_AVAILABLE:
        mlflow.autolog()
    
    print(f"\n[3/3] Starting training...")
    
    # Training with improved settings
    model.train(
        data=yaml_path,
        epochs=epochs,
        imgsz=1024,             # Higher resolution for small panels
        batch=-1,               # AutoBatch for optimal GPU utilization
        project='outputs/training',
        name='yolov12_v2',
        exist_ok=True,
        resume=resume,
        
        # Heavy Augmentations for diverse panel appearances
        mosaic=1.0,             # Always use mosaic
        mixup=0.5,              # Mixup images
        
        # Color Jitter (Heavy for varied satellite imagery)
        hsv_h=0.02,             # Hue variation
        hsv_s=0.8,              # Saturation variation (important for panel colors)
        hsv_v=0.5,              # Value/brightness variation
        
        # Geometric (Satellite images have no fixed orientation)
        degrees=180.0,          # Full rotation
        translate=0.15,         # Translation
        scale=0.6,              # Scaling +/- 60%
        shear=3.0,              # Shear
        perspective=0.001,      # Perspective transformation
        
        # Flips (Satellite images can be any orientation)
        flipud=0.5,             # Vertical flip
        fliplr=0.5,             # Horizontal flip
        
        # Copy-paste augmentation
        copy_paste=0.5,         # Higher copy-paste for panel duplication
        
        # Early stopping patience
        patience=50,            # Stop if no improvement for 50 epochs
        
        # Other optimizations
        amp=True,               # Mixed precision
        workers=8,              # Dataloader workers
        cache=True,             # Cache images for faster training
        
        # Validation
        val=True,
        plots=True,
        save=True,
    )
    
    print("\n" + "="*60)
    print("Training Complete!")
    print(f"Best model saved to: outputs/training/yolov12_v2/weights/best.pt")
    print("="*60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train YOLOv12/v11 for solar panel detection v2")
    parser.add_argument('--resume', action='store_true', help="Resume from last checkpoint")
    parser.add_argument('--epochs', type=int, default=150, help="Number of epochs")
    parser.add_argument('--model', type=str, default='yolo11x', 
                        help="Model size (yolo11x, yolo11l, yolo12x, etc.)")
    args = parser.parse_args()
    
    train(resume=args.resume, epochs=args.epochs, model_size=args.model)
