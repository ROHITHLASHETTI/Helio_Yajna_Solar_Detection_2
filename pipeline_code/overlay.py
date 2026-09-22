"""
Visualization overlay using spotlight effect.
Adapted from Dude-Coders for Helio Yajna pipeline.
"""
import cv2
from .utils import create_spotlight_overlay


def draw_overlay(img, green_boxes, red_boxes, radius_pixels, sample_id="",
                 has_solar=False, detection_method="", buffer_size=0, confidence=0.0):
    """
    Draw a spotlight overlay on the image:
      - Darkens region outside the buffer circle
      - Green semi-transparent boxes for detected (inside buffer)
      - Red semi-transparent boxes for rejected candidates
      - Text annotation with detection result

    Returns the annotated image (modifies in-place and returns it).
    """
    center = (img.shape[1] // 2, img.shape[0] // 2)

    annotated = create_spotlight_overlay(
        img, center, radius_pixels,
        boxes_inside=green_boxes,
        boxes_outside=red_boxes,
        active_box=float(confidence) if has_solar else None,
    )

    # Text overlay
    color = (0, 255, 0) if has_solar else (0, 0, 255)
    method_tag = f" [{detection_method.upper()}]" if detection_method not in ("initial", "") else ""
    cv2.putText(
        annotated,
        f"ID: {sample_id}  Solar: {has_solar}  Buffer: {buffer_size} sqft{method_tag}",
        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
    )
    cv2.putText(
        annotated,
        f"Conf: {confidence:.3f}  Method: {detection_method}",
        (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1,
    )

    # Copy back into original array
    img[:] = annotated
    return img