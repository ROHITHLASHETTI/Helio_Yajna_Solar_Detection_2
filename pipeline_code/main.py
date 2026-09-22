"""
Helio Yajna Solar Detection — Main Pipeline Entry Point
Upgraded with Dude-Coders' 6-stage fallback inference strategy.

Usage:
    python -m pipeline_code.main
    python -m pipeline_code.main --limit 5
    python -m pipeline_code.main --samples "1-10,20,55"
    python -m pipeline_code.main --input input_data/input.xlsx --output output_data
    python -m pipeline_code.main --initial-conf 0.20 --fallback-conf 0.15
"""
import os
import sys
import json
import argparse
import cv2
import numpy as np
import pandas as pd
from pathlib import Path
from ultralytics import YOLO
from dotenv import load_dotenv

from .image_fetcher import ImageRetriever
from .inference import run_inference_fallback
from .overlay import draw_overlay
from .utils import calculate_radius_from_area_sqft, calculate_meters_per_pixel

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# Defaults (can be overridden via CLI or env vars)
# ---------------------------------------------------------------------------
DEFAULT_MODEL_PATH    = os.getenv("MODEL_PATH",   "trained_model/weights.pt")
DEFAULT_INPUT_FILE    = os.getenv("INPUT_FILE",   "input_data/input.xlsx")
DEFAULT_OUTPUT_DIR    = os.getenv("OUTPUT_DIR",   "output_data")
DEFAULT_ZOOM          = int(os.getenv("ZOOM_LEVEL", "20"))
DEFAULT_CACHE_DIR     = "cache/images"   # shared image cache (avoids re-fetching)
DEFAULT_INITIAL_CONF  = 0.20             # Stage 1-2 threshold
DEFAULT_FALLBACK_CONF = 0.05             # Stage 3-6 threshold (lower = catch more)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_sample_ids(samples_str):
    """Parse a string like '1-10,20,55-60' into a list of ints."""
    ids = []
    for part in samples_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = map(int, part.split("-"))
            ids.extend(range(start, end + 1))
        else:
            ids.append(int(part))
    return ids


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    excel_path=DEFAULT_INPUT_FILE,
    model_path=DEFAULT_MODEL_PATH,
    output_dir=DEFAULT_OUTPUT_DIR,
    cache_dir=DEFAULT_CACHE_DIR,
    limit=None,
    sample_ids=None,
    initial_conf=DEFAULT_INITIAL_CONF,
    fallback_conf=DEFAULT_FALLBACK_CONF,
    zoom=DEFAULT_ZOOM,
):
    # --- Load model ---
    print(f"[INFO] Loading YOLO model from: {model_path}")
    model = YOLO(model_path)

    # --- Load data ---
    print(f"[INFO] Reading input from: {excel_path}")
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"[ERROR] Cannot read Excel file: {e}")
        sys.exit(1)

    # Column normalisation
    if "sampleid" in df.columns:
        df.rename(columns={"sampleid": "sample_id"}, inplace=True)

    required = ["sample_id", "latitude", "longitude"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"[ERROR] Missing columns: {missing}")
        sys.exit(1)

    # Filter rows
    if sample_ids:
        df["sample_id"] = (df["sample_id"].astype(str)
                           .str.replace(r"\.0$", "", regex=True))
        str_ids = [str(s) for s in sample_ids]
        df = df[df["sample_id"].isin(str_ids)]
        print(f"[INFO] Filtering to {len(df)} sample(s): {sample_ids}")
    elif limit:
        df = df.head(limit)
        print(f"[INFO] Limiting to first {limit} samples.")

    # --- Output directories ---
    img_dir  = os.path.join(output_dir, "artefacts", "test")
    json_dir = os.path.join(output_dir, "prediction_files", "test")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)

    # --- Image retriever (with caching) ---
    api_key   = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_API_KEY")
    retriever = ImageRetriever(api_key=api_key, cache_dir=cache_dir)

    all_results = []

    print(f"\n[INFO] Starting pipeline — {len(df)} site(s) to process.\n")

    for _, row in df.iterrows():
        sid = row["sample_id"]
        lat  = float(row["latitude"])
        lon  = float(row["longitude"])

        formatted_sid = str(int(float(str(sid).replace(".0", ""))))
        print(f"\n[INFO] Processing sample_id: {formatted_sid}")

        # 1. Fetch satellite image (cached)
        img_path, img_meta = retriever.get_image(lat, lon, zoom=zoom)

        # 2. Run 6-stage fallback inference
        result = run_inference_fallback(
            model, img_path, lat,
            initial_conf=initial_conf,
            fallback_conf=fallback_conf,
            zoom=zoom,
        )

        # 3. Print result
        if result["has_solar"]:
            print(f"[RESULT] SOLAR DETECTED  "
                  f"(buffer={result['buffer_radius_sqft']} sqft, "
                  f"area={result['pv_area_sqm_est']} m²)")
        else:
            print("[RESULT] NO SOLAR DETECTED")
        print(f"[INFO] Inference mode used: {result['detection_method']}")

        # 4. Save annotated overlay image
        img_cv = cv2.imread(img_path)
        if img_cv is not None:
            final_bbox   = result["bbox"]
            all_boxes    = result["all_boxes"]
            all_confs    = result["all_confidences"]
            center       = result["center"]
            radius_px    = result["radius_pixels"]

            green_boxes = [final_bbox] if result["has_solar"] and final_bbox else []
            red_boxes   = [
                b for b in all_boxes
                if not (result["has_solar"] and final_bbox and
                        b[0] == final_bbox[0] and b[1] == final_bbox[1] and
                        b[2] == final_bbox[2] and b[3] == final_bbox[3])
            ]

            draw_overlay(
                img_cv,
                green_boxes=green_boxes,
                red_boxes=red_boxes,
                radius_pixels=radius_px,
                sample_id=formatted_sid,
                has_solar=result["has_solar"],
                detection_method=result["detection_method"],
                buffer_size=result["buffer_radius_sqft"],
                confidence=result["confidence"],
            )
            overlay_path = os.path.join(img_dir, f"{formatted_sid}_overlay.jpg")
            cv2.imwrite(overlay_path, img_cv)

        # 5. Build JSON record
        clean_meta = {
            "source": img_meta.get("source", "Unknown"),
            "capture_date": img_meta.get("capture_date", "Unknown"),
            "zoom": zoom,
            "inference_mode": result["detection_method"],
        }

        record = {
            "sample_id": formatted_sid,
            "lat": lat,
            "lon": lon,
            "has_solar": result["has_solar"],
            "confidence": result["confidence"],
            "pv_area_sqm_est": result["pv_area_sqm_est"],
            "euclidean_distance_m_est": result["euclidean_distance_m_est"],
            "buffer_radius_sqft": result["buffer_radius_sqft"],
            "qc_status": result["qc_status"],
            "bbox_or_mask": [list(result["bbox"])] if result["has_solar"] and result["bbox"] else [],
            "image_metadata": clean_meta,
        }
        all_results.append(record)

        # Per-site JSON (Helio compatibility)
        site_json = os.path.join(json_dir, f"{formatted_sid}.json")
        with open(site_json, "w") as f:
            json.dump(record, f, indent=2)

    # 6. Save consolidated results.json
    results_json_path = os.path.join(json_dir, "results.json")
    with open(results_json_path, "w") as f:
        json.dump(all_results, f, indent=2)

    # --- Summary ---
    detected = sum(1 for r in all_results if r["has_solar"])
    print(f"\n{'='*55}")
    print(f"✅ Pipeline completed successfully")
    print(f"   Detected : {detected}/{len(all_results)} sites have solar panels")
    print(f"   Images   : {img_dir}")
    print(f"   JSON     : {results_json_path}")
    print(f"{'='*55}\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Helio Yajna — Solar Panel Detection Pipeline"
    )
    parser.add_argument("--input",        type=str,   default=DEFAULT_INPUT_FILE,   help="Path to input .xlsx file")
    parser.add_argument("--model",        type=str,   default=DEFAULT_MODEL_PATH,   help="Path to YOLO model weights")
    parser.add_argument("--output",       type=str,   default=DEFAULT_OUTPUT_DIR,   help="Output directory")
    parser.add_argument("--cache-dir",    type=str,   default=DEFAULT_CACHE_DIR,    help="Image cache directory")
    parser.add_argument("--limit",        type=int,   default=None,                 help="Process only first N samples")
    parser.add_argument("--samples",      type=str,   default=None,                 help="Sample IDs or ranges e.g. '1-10,20,55'")
    parser.add_argument("--initial-conf", type=float, default=DEFAULT_INITIAL_CONF, help="Confidence threshold for stages 1-2 (default 0.20)")
    parser.add_argument("--fallback-conf",type=float, default=DEFAULT_FALLBACK_CONF,help="Confidence threshold for crop stages 3-6 (default 0.05)")
    parser.add_argument("--zoom",         type=int,   default=DEFAULT_ZOOM,         help="Google Maps zoom level (default 20)")
    args = parser.parse_args()

    sample_ids = parse_sample_ids(args.samples) if args.samples else None

    run_pipeline(
        excel_path    = args.input,
        model_path    = args.model,
        output_dir    = args.output,
        cache_dir     = args.cache_dir,
        limit         = args.limit,
        sample_ids    = sample_ids,
        initial_conf  = args.initial_conf,
        fallback_conf = args.fallback_conf,
        zoom          = args.zoom,
    )