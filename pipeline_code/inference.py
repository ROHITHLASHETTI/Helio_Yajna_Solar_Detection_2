"""
6-stage fallback solar panel inference engine.
Fully aligned with Dude-Coders' approach including all fixes:

Key fixes applied vs previous port:
  - imgsz=1024 set explicitly (YOLO defaults to 640 otherwise — kills small panels)
  - fallback_conf lowered to 0.05 for crop stages (Dude-Coders backend uses 0.05)
  - Rescue Step added: catches high-confidence off-center panels missed by buffer logic
  - enh_boxes/enh_confs initialised before use (prevents NameError when solar found early)

Fallback order:
  1. Initial full-image inference        → check 1200 sqft buffer
  2. Saturation-enhanced inference       → check 1200 sqft buffer
  3. Crop-to-buffer + re-infer          → check 1200 sqft buffer
  4. Saturated crop + re-infer          → check 1200 sqft buffer
  5. Initial full-image boxes            → check 2400 sqft buffer
  6. Saturation-enhanced boxes           → check 2400 sqft buffer
  [R] Rescue: nearest high-conf box     → within 2× radius_2400
"""
import cv2
import numpy as np

from .utils import (
    calculate_meters_per_pixel,
    calculate_radius_from_area_sqft,
    calculate_intersection_area,
    crop_buffer_region,
    run_inference_on_crop,
)

MAX_PANEL_AREA_SQM = 1000.0   # reject implausibly giant boxes


# ---------------------------------------------------------------------------
# Image enhancement
# ---------------------------------------------------------------------------

def enhance_saturation(image, factor=1.5):
    """Boost HSV saturation to make solar panels more visible."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * factor, 0, 255).astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


# ---------------------------------------------------------------------------
# Buffer overlap helper
# ---------------------------------------------------------------------------

def find_best_panel_in_buffer(boxes, confidences, center, radius_pixels,
                               meters_per_pixel=None):
    """
    Return (best_idx, best_overlap) for the box with the largest
    intersection area with the buffer circle.
    Giant-box false positives (>1000 sqm) are rejected.
    """
    best_overlap = 0
    best_idx = -1

    for i, box in enumerate(boxes):
        if meters_per_pixel is not None:
            x1, y1, x2, y2 = box
            area_sqm = (x2 - x1) * (y2 - y1) * (meters_per_pixel ** 2)
            if area_sqm > MAX_PANEL_AREA_SQM:
                continue   # skip giant false-positive boxes

        overlap = calculate_intersection_area(box, center, radius_pixels)
        if overlap > best_overlap:
            best_overlap = overlap
            best_idx = i

    return best_idx, best_overlap


# ---------------------------------------------------------------------------
# Main 6-stage + rescue fallback
# ---------------------------------------------------------------------------

def run_inference_fallback(model, image_path, lat,
                            initial_conf=0.20,
                            fallback_conf=0.05,   # low threshold for crop stages
                            zoom=20):
    """
    Run the full 6-stage + rescue fallback on a single satellite image.

    Returns a dict:
        has_solar, confidence, pv_area_sqm_est, euclidean_distance_m_est,
        buffer_radius_sqft, qc_status, bbox, detection_method,
        all_boxes, all_confidences, center, radius_pixels
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    h, w       = img.shape[:2]
    center     = (w // 2, h // 2)
    img_size   = max(h, w)   # use actual image dimension for YOLO imgsz

    mpp        = calculate_meters_per_pixel(lat, zoom=zoom)
    radius_1200 = calculate_radius_from_area_sqft(1200, mpp)
    radius_2400 = calculate_radius_from_area_sqft(2400, mpp)

    # -----------------------------------------------------------------------
    # Stage 1 — Initial full-image inference
    # -----------------------------------------------------------------------
    results = model.predict(img, conf=initial_conf, augment=True,
                             imgsz=img_size, save=False, verbose=False)
    boxes       = results[0].boxes.xyxy.tolist() if results[0].boxes else []
    confidences = results[0].boxes.conf.tolist() if results[0].boxes else []

    print(f"  Initial detection: {len(boxes)} panel(s) found")

    # initialise enhanced results early so rescue step can always access them
    enh_boxes = []
    enh_confs = []

    final_has_solar   = False
    final_buffer_size = 2400
    final_bbox        = []
    final_confidence  = 0.0
    detection_method  = "not_found"

    # Stage 1 → 1200 buffer
    best, _ = find_best_panel_in_buffer(boxes, confidences, center,
                                         radius_1200, mpp)
    if best != -1:
        final_has_solar   = True
        final_buffer_size = 1200
        final_bbox        = boxes[best]
        final_confidence  = confidences[best]
        detection_method  = "initial"
        print(f"  -> Found in 1200 sqft buffer (Initial)! Conf: {final_confidence:.3f}")

    else:
        # -----------------------------------------------------------------------
        # Stage 2 — Saturation-enhanced, 1200 buffer
        # -----------------------------------------------------------------------
        print("  -> Not in 1200 (Initial). Trying SATURATED 1200...")
        img_sat = enhance_saturation(img, factor=1.5)
        res_sat = model.predict(img_sat, conf=fallback_conf, augment=True,
                                 imgsz=img_size, save=False, verbose=False)
        enh_boxes = res_sat[0].boxes.xyxy.tolist() if res_sat[0].boxes else []
        enh_confs = res_sat[0].boxes.conf.tolist() if res_sat[0].boxes else []

        best, _ = find_best_panel_in_buffer(enh_boxes, enh_confs, center,
                                             radius_1200, mpp)
        if best != -1:
            final_has_solar   = True
            final_buffer_size = 1200
            final_bbox        = enh_boxes[best]
            final_confidence  = enh_confs[best]
            detection_method  = "saturated_1200"
            boxes.extend(enh_boxes)
            confidences.extend(enh_confs)
            print(f"  -> Found in 1200 sqft buffer (Saturated)! Conf: {final_confidence:.3f}")

        else:
            # -----------------------------------------------------------------------
            # Stage 3 — Crop to 1200 buffer, re-infer (lower conf)
            # -----------------------------------------------------------------------
            print("  -> Not in 1200 (Saturated). Trying CROPPED 1200...")
            cropped, offset, _ = crop_buffer_region(img, center, radius_1200,
                                                     padding=30)
            crop_boxes, crop_confs = run_inference_on_crop(model, cropped,
                                                            offset,
                                                            conf=fallback_conf)
            best, _ = find_best_panel_in_buffer(crop_boxes, crop_confs, center,
                                                 radius_1200, mpp)
            if best != -1:
                final_has_solar   = True
                final_buffer_size = 1200
                final_bbox        = crop_boxes[best]
                final_confidence  = crop_confs[best]
                detection_method  = "crop_1200"
                boxes.extend(crop_boxes)
                confidences.extend(crop_confs)
                print(f"  -> Found in 1200 sqft buffer (Cropped)! Conf: {final_confidence:.3f}")

            else:
                # -----------------------------------------------------------------------
                # Stage 4 — Saturated crop, 1200 buffer
                # -----------------------------------------------------------------------
                print("  -> Not in 1200 (Cropped). Trying SATURATED CROP 1200...")
                cropped_sat = enhance_saturation(cropped, factor=1.5)
                sc_boxes, sc_confs = run_inference_on_crop(model, cropped_sat,
                                                            offset,
                                                            conf=fallback_conf)
                best, _ = find_best_panel_in_buffer(sc_boxes, sc_confs, center,
                                                     radius_1200, mpp)
                if best != -1:
                    final_has_solar   = True
                    final_buffer_size = 1200
                    final_bbox        = sc_boxes[best]
                    final_confidence  = sc_confs[best]
                    detection_method  = "crop_sat_1200"
                    boxes.extend(sc_boxes)
                    confidences.extend(sc_confs)
                    print(f"  -> Found in 1200 sqft buffer (Sat+Crop)! Conf: {final_confidence:.3f}")

                else:
                    # -----------------------------------------------------------------------
                    # Stage 5 — Initial boxes → 2400 buffer
                    # -----------------------------------------------------------------------
                    print("  -> Not found in any 1200 method. Checking 2400 (Initial)...")
                    best, _ = find_best_panel_in_buffer(boxes, confidences,
                                                         center, radius_2400, mpp)
                    if best != -1:
                        final_has_solar   = True
                        final_buffer_size = 2400
                        final_bbox        = boxes[best]
                        final_confidence  = confidences[best]
                        detection_method  = "initial_2400"
                        print(f"  -> Found in 2400 sqft buffer (Initial)! Conf: {final_confidence:.3f}")

                    else:
                        # -----------------------------------------------------------------------
                        # Stage 6 — Saturated boxes → 2400 buffer
                        # -----------------------------------------------------------------------
                        print("  -> Checking 2400 (Saturated)...")
                        best, _ = find_best_panel_in_buffer(enh_boxes, enh_confs,
                                                             center, radius_2400, mpp)
                        if best != -1:
                            final_has_solar   = True
                            final_buffer_size = 2400
                            final_bbox        = enh_boxes[best]
                            final_confidence  = enh_confs[best]
                            detection_method  = "saturated_2400"
                            boxes.extend(enh_boxes)
                            confidences.extend(enh_confs)
                            print(f"  -> Found in 2400 sqft buffer (Saturated)! Conf: {final_confidence:.3f}")
                        else:
                            print("  -> NOT FOUND in any buffer/method")

    # ---------------------------------------------------------------------------
    # Rescue Step — off-center high-confidence detection
    # From Dude-Coders backend/inference_service.py
    # Catches panels that sit just outside the buffer but are clearly real.
    # ---------------------------------------------------------------------------
    if not final_has_solar and boxes:
        rescue_threshold_px = radius_2400 * 2.0
        best_rescue_idx = -1
        min_dist        = float("inf")

        for i, box in enumerate(boxes):
            bx1, by1, bx2, by2 = box
            cx_box = (bx1 + bx2) / 2
            cy_box = (by1 + by2) / 2
            dist   = np.sqrt((cx_box - center[0]) ** 2 + (cy_box - center[1]) ** 2)

            # Must be confident (>0.40) and within 2× the outer buffer radius
            if confidences[i] > 0.40 and dist < min_dist:
                min_dist        = dist
                best_rescue_idx = i

        if best_rescue_idx != -1 and min_dist < rescue_threshold_px:
            final_has_solar   = True
            final_buffer_size = 2400
            final_bbox        = boxes[best_rescue_idx]
            final_confidence  = confidences[best_rescue_idx]
            detection_method  = "rescued_off_center"
            print(f"  -> RESCUED off-center panel! dist={min_dist:.0f}px, "
                  f"Conf: {final_confidence:.3f}")

    # ---------------------------------------------------------------------------
    # Area & distance
    # ---------------------------------------------------------------------------
    final_pv_area_sqm = 0.0
    final_dist_m      = 0.0

    if final_has_solar and final_bbox:
        bx1, by1, bx2, by2 = final_bbox
        final_pv_area_sqm   = (bx2 - bx1) * (by2 - by1) * (mpp ** 2)
        cx_box  = (bx1 + bx2) / 2
        cy_box  = (by1 + by2) / 2
        dist_px = np.sqrt((cx_box - center[0]) ** 2 + (cy_box - center[1]) ** 2)
        final_dist_m = dist_px * mpp

    # ---------------------------------------------------------------------------
    # QC Status  (Dude-Coders logic)
    # ---------------------------------------------------------------------------
    if final_has_solar:
        qc_status = "VERIFIABLE" if final_confidence > 0.70 else "NOT_VERIFIABLE"
    else:
        qc_status = "VERIFIABLE"   # exhaustive search = verified absent

    return {
        "has_solar":                 bool(final_has_solar),
        "confidence":                round(float(final_confidence), 4),
        "pv_area_sqm_est":           round(final_pv_area_sqm, 2),
        "euclidean_distance_m_est":  round(final_dist_m, 2),
        "buffer_radius_sqft":        final_buffer_size,
        "qc_status":                 qc_status,
        "bbox":                      final_bbox,
        "detection_method":          detection_method,
        "all_boxes":                 boxes,
        "all_confidences":           confidences,
        "center":                    center,
        "radius_pixels":             calculate_radius_from_area_sqft(
                                         final_buffer_size, mpp),
    }