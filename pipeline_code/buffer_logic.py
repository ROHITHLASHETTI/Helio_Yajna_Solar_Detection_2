import cv2
import numpy as np
from math import sqrt, pi
from .utils import IMG_SIZE, CENTER,gsd

AREA_1200_SQFT = 1200
AREA_2400_SQFT = 2400

BUFFER_CACHE = {}
def create_buffer(radius_px):
    key = int(radius_px)
    if key in BUFFER_CACHE:
        return BUFFER_CACHE[key]
    mask = np.zeros((IMG_SIZE, IMG_SIZE), dtype="uint8")
    cv2.circle(mask, CENTER, int(radius_px), 1, -1)
    BUFFER_CACHE[key] = mask
    return mask
def select_masks(masks,lat):
    r1200_px = sqrt((AREA_1200_SQFT * 0.092903) / pi) / gsd(lat)
    r2400_px = sqrt((AREA_2400_SQFT * 0.092903) / pi) / gsd(lat)

    buffer_1200 = create_buffer(r1200_px)
    buffer_2400 = create_buffer(r2400_px)

    if not masks:
        return None, 0, r1200_px, r2400_px

    for m in masks:
        if (m & buffer_1200).any():
            return buffer_1200, AREA_1200_SQFT, r1200_px, r2400_px

    for m in masks:
        if (m & buffer_2400).any():
            return buffer_2400, AREA_2400_SQFT, r1200_px, r2400_px

    return None, 0, r1200_px, r2400_px