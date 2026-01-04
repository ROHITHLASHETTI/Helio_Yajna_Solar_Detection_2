import cv2
import numpy as np
from .utils import CENTER
def draw_overlay(
    img,
    green_masks,
    red_masks,
    radius_1200_px,
    radius_2400_px
):
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    for m in red_masks:
        if m.shape[:2] != (h, w):
            m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)

        contours, _ = cv2.findContours(
            m.astype("uint8"),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        cv2.drawContours(img, contours, -1, (0, 0, 255), 2)
    for m in green_masks:
        if m.shape[:2] != (h, w):
            m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)

        overlay = np.zeros_like(img)
        overlay[:, :, 1] = m * 255
        img[:] = cv2.addWeighted(img, 1.0, overlay, 0.4, 0)
    if radius_2400_px > 0:
        cv2.circle(
            img,
            center,
            int(radius_2400_px),
            (0, 165, 255),  # ORANGE
            2
        )

    if radius_1200_px > 0:
        cv2.circle(
            img,
            center,
            int(radius_1200_px),
            (0, 255, 255),  # YELLOW
            2
        )