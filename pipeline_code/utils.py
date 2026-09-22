"""
Geometry and visualization utilities for solar panel detection.
Adapted from Dude-Coders approach for Helio Yajna pipeline.
"""
import numpy as np
import cv2
import math
import os
import tempfile


# ---------------------------------------------------------------------------
# Geo / pixel geometry
# ---------------------------------------------------------------------------

def gsd(lat_deg):
    """Ground sampling distance (meters/pixel) at zoom 20. Legacy alias."""
    return calculate_meters_per_pixel(lat_deg, zoom=20)


def calculate_meters_per_pixel(lat, zoom=20):
    """
    Calculate meters per pixel at a given latitude and zoom level.
    Based on Google Maps Mercator projection.
    """
    return 156543.03392 * np.cos(np.radians(lat)) / (2 ** zoom)


def calculate_radius_from_area_sqft(area_sqft, meters_per_pixel):
    """
    Calculate the radius in pixels for a given area in square feet.
    Area = pi * r^2  =>  r = sqrt(Area / pi)
    """
    area_sqm = area_sqft * 0.092903          # sqft -> sqm
    radius_meters = np.sqrt(area_sqm / np.pi)
    return radius_meters / meters_per_pixel  # pixels


def calculate_box_area_pixels(box):
    """Return pixel area of a bounding box [x1, y1, x2, y2]."""
    w = max(0, box[2] - box[0])
    h = max(0, box[3] - box[1])
    return w * h


def calculate_intersection_area(box, circle_center, circle_radius):
    """
    Calculate the approximate intersection area between a bounding box
    and a circle using mask-based approach.
    """
    x1, y1, x2, y2 = map(int, box)
    cx, cy = map(int, circle_center)
    r = int(circle_radius)

    min_x = min(x1, cx - r)
    min_y = min(y1, cy - r)
    max_x = max(x2, cx + r)
    max_y = max(y2, cy + r)

    w = max_x - min_x + 1
    h = max_y - min_y + 1

    if w <= 0 or h <= 0:
        return 0

    box_mask = np.zeros((h, w), dtype=np.uint8)
    circle_mask = np.zeros((h, w), dtype=np.uint8)

    cv2.rectangle(box_mask, (x1 - min_x, y1 - min_y), (x2 - min_x, y2 - min_y), 1, -1)
    cv2.circle(circle_mask, (cx - min_x, cy - min_y), r, 1, -1)

    return int(np.sum(cv2.bitwise_and(box_mask, circle_mask)))


# ---------------------------------------------------------------------------
# Spotlight / overlay visualization
# ---------------------------------------------------------------------------

def create_spotlight_overlay(image, center, radius,
                              boxes_inside=None, boxes_outside=None,
                              boxes_in_buffer_not_selected=None,
                              active_box=None):
    """
    Create a spotlight effect: darken everything outside the buffer circle.
    - Green boxes: selected (detected inside buffer)
    - Red boxes: rejected candidates (outside buffer)
    - Yellow circle: buffer boundary
    """
    overlay = image.copy()
    mask = np.zeros(image.shape[:2], dtype=np.uint8)

    cx, cy = map(int, center)
    r = int(radius)

    cv2.circle(mask, (cx, cy), r, 255, -1)
    inverse_mask = cv2.bitwise_not(mask)

    darkened = cv2.addWeighted(overlay, 0.3, np.zeros_like(overlay), 0.7, 0)

    img_masked = cv2.bitwise_and(image, image, mask=mask)
    dark_masked = cv2.bitwise_and(darkened, darkened, mask=inverse_mask)
    final_image = cv2.add(img_masked, dark_masked)

    # Buffer circle outline (yellow)
    cv2.circle(final_image, (cx, cy), r, (0, 255, 255), 2)

    # Red: rejected / outside
    if boxes_outside:
        for box in boxes_outside:
            x1, y1, x2, y2 = map(int, box)
            overlay_box = final_image.copy()
            cv2.rectangle(overlay_box, (x1, y1), (x2, y2), (0, 0, 255), -1)
            cv2.addWeighted(overlay_box, 0.3, final_image, 0.7, 0, final_image)
            cv2.rectangle(final_image, (x1, y1), (x2, y2), (0, 0, 255), 2)

    # Green: selected
    if boxes_inside:
        for box in boxes_inside:
            x1, y1, x2, y2 = map(int, box)
            overlay_box = final_image.copy()
            cv2.rectangle(overlay_box, (x1, y1), (x2, y2), (0, 255, 0), -1)
            cv2.addWeighted(overlay_box, 0.3, final_image, 0.7, 0, final_image)
            cv2.rectangle(final_image, (x1, y1), (x2, y2), (0, 255, 0), 3)

            label = "SELECTED"
            if active_box and isinstance(active_box, (float, np.floating)):
                label = f"SOLAR: {active_box:.2f}"
            cv2.putText(final_image, label, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    return final_image


# ---------------------------------------------------------------------------
# Crop / re-infer helpers
# ---------------------------------------------------------------------------

def crop_buffer_region(image, center, radius, padding=10):
    """
    Crop the image to a square bounding box around the buffer circle.

    Returns:
        cropped_image, crop_offset (x, y), crop_bounds (x1, y1, x2, y2)
    """
    h, w = image.shape[:2]
    cx, cy = map(int, center)
    r = int(radius) + padding

    x1 = max(0, cx - r)
    y1 = max(0, cy - r)
    x2 = min(w, cx + r)
    y2 = min(h, cy + r)

    cropped_image = image[y1:y2, x1:x2].copy()
    return cropped_image, (x1, y1), (x1, y1, x2, y2)


def map_boxes_to_original(boxes, crop_offset):
    """Map bounding boxes from cropped-image coords back to original coords."""
    offset_x, offset_y = crop_offset
    return [
        [b[0] + offset_x, b[1] + offset_y, b[2] + offset_x, b[3] + offset_y]
        for b in boxes
    ]


def run_inference_on_crop(model, cropped_image, crop_offset, conf=0.10):
    """
    Run YOLO inference on a cropped image region in memory and return boxes mapped
    back to the original image coordinate space.
    """
    results = model.predict(cropped_image, conf=conf, augment=False,
                            save=False, verbose=False)
    result = results[0]
    crop_boxes = result.boxes.xyxy.tolist() if result.boxes else []
    confidences = result.boxes.conf.tolist() if result.boxes else []
    mapped_boxes = map_boxes_to_original(crop_boxes, crop_offset)
    return mapped_boxes, confidences


# ---------------------------------------------------------------------------
# NMS
# ---------------------------------------------------------------------------

def apply_nms(boxes, confidences, iou_threshold=0.5):
    """Apply Non-Maximum Suppression to remove overlapping detections."""
    if not boxes:
        return [], []

    boxes_np = np.array(boxes)
    confs_np = np.array(confidences)
    indices = np.argsort(confs_np)[::-1]

    keep = []
    while len(indices) > 0:
        current = indices[0]
        keep.append(current)
        if len(indices) == 1:
            break
        remaining = indices[1:]
        ious = np.array([calculate_iou(boxes_np[current], boxes_np[i]) for i in remaining])
        indices = remaining[ious < iou_threshold]

    return [boxes[i] for i in keep], [confidences[i] for i in keep]


def calculate_iou(box1, box2):
    """Intersection over Union between two [x1,y1,x2,y2] boxes."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection
    return intersection / union if union > 0 else 0


# ---------------------------------------------------------------------------
# Legacy constants kept for any remaining references
# ---------------------------------------------------------------------------
IMG_SIZE = 1024
CENTER = (IMG_SIZE // 2, IMG_SIZE // 2)
ZOOM_LEVEL = 20
SCALE = 2
YOLO_CONF = 0.20
MIN_PIXELS = 100
AREA_1200_SQFT = 1200
AREA_2400_SQFT = 2400