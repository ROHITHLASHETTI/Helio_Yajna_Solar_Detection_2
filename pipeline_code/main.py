import os
import cv2
import numpy as np
import pandas as pd
from ultralytics import YOLO
from dotenv import load_dotenv

from .utils import (
    MODEL_PATH,
    INPUT_FILE,
    OUTPUT_DIR,
    ZOOM_LEVEL,
    YOLO_CONF,
    CENTER
)

from .image_fetcher import fetch_image
from .inference import run_inference
from .buffer_logic import select_masks
from .area_estimation import area_and_distance
from .overlay import draw_overlay
from .json_writer import write_json
from .image_enhancer import enhance_image
from .sahi_inference import run_sahi
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

model = YOLO(MODEL_PATH)
df = pd.read_excel(INPUT_FILE)

IMG_DIR = os.path.join(OUTPUT_DIR, "artefacts", "test")
JSON_DIR = os.path.join(OUTPUT_DIR, "prediction_files", "test")

os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)
for _, row in df.iterrows():
    sid = row["sample_id"]          
    lat, lon = row["latitude"], row["longitude"]

    print(f"\n[INFO] Processing sample_id: {sid}")

    img_path = os.path.join(IMG_DIR, f"{sid}.jpg")
    fetch_image(sid, lat, lon, API_KEY, img_path)
    masks, confs = run_inference(model, img_path)
    inference_mode = "PRIMARY"

    buffer_mask, buffer_sqft, r1200, r2400 = select_masks(masks)

    inside_count = 0
    if buffer_mask is not None and masks:
        stacked = np.stack(masks)
        inside_count = np.any(stacked & buffer_mask, axis=(1,2)).sum()
    enhanced_path = None
    if inside_count == 0:
        print("[INFO] No detections inside buffer → applying image enhancement")

        img = cv2.imread(img_path)
        enhanced = enhance_image(img)

        enhanced_path = img_path.replace(".jpg", "_enhanced.jpg")
        cv2.imwrite(enhanced_path, enhanced)

        masks, confs = run_inference(model, enhanced_path)
        inference_mode = "ENHANCED"

        buffer_mask, buffer_sqft, r1200, r2400 = select_masks(masks)
        if buffer_mask is not None and masks:
            stacked = np.stack(masks)
            inside_count = np.any(stacked & buffer_mask, axis=(1,2)).sum()
        else:
            inside_count = 0

    if inside_count == 0:
        print("[INFO] Still no detections inside buffer → running SAHI slicing")

        masks, confs = run_sahi(
            MODEL_PATH,
            enhanced_path if enhanced_path else img_path,
            YOLO_CONF + 0.05
        )
        inference_mode = "SAHI"

        buffer_mask, buffer_sqft, r1200, r2400 = select_masks(masks)
    green, red = [], []
    total_area, dist, best_conf = 0.0, 0.0, 0.0

    for m, c in zip(masks, confs):
        if buffer_mask is not None and (m & buffer_mask).any():
            green.append(m)
            a, d = area_and_distance(m)
            total_area += a
            dist = d
            best_conf = max(best_conf, c)
        else:
            red.append(m)
    img = cv2.imread(img_path)
    draw_overlay(img, green, red, r1200, r2400)
    cv2.imwrite(os.path.join(IMG_DIR, f"{sid}_overlay.jpg"), img)
    if green:
        print(f"[RESULT] SOLAR DETECTED (buffer={buffer_sqft} sqft, area={round(total_area,2)} m²)")
    else:
        print("[RESULT] NO SOLAR DETECTED")

    print(f"[INFO] Inference mode used: {inference_mode}")
    json_data = {
        "sample_id": sid,
        "lat": lat,
        "lon": lon,
        "has_solar": len(green) > 0,
        "confidence": round(best_conf, 2),
        "buffer_radius_sqft": buffer_sqft,
        "pv_area_sqm_est": round(total_area, 2),
        "euclidean_distance_m_est": dist,
        "qc_status": "VERIFIABLE",
        "bbox_or_mask": "mask",
        "image_metadata": {
            "source": "Google Static Maps",
            "zoom": ZOOM_LEVEL,
            "inference_mode": inference_mode
        }
    }

    write_json(os.path.join(JSON_DIR, f"{sid}.json"), json_data)

print("\n✅ Pipeline completed successfully")
