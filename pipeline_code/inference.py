from ultralytics import YOLO
import numpy as np
import cv2

from .utils import YOLO_CONF, MIN_PIXELS, IMG_SIZE


def run_inference(model, image_path):
    results = model.predict(
        source=image_path,
        imgsz=IMG_SIZE,
        conf=YOLO_CONF,
        iou=0.5,
        verbose=False
    )

    masks = []
    confs = []

    if len(results) == 0:
        return masks, confs

    r = results[0]
    if r.masks is None or r.boxes is None:
        return masks, confs

    for i, m in enumerate(r.masks.data):
        raw_mask = (m.cpu().numpy() > 0.3).astype("uint8")
        mask = cv2.resize(
            raw_mask,
            (IMG_SIZE, IMG_SIZE),
            interpolation=cv2.INTER_NEAREST
        )
        if mask.sum() < MIN_PIXELS:
            continue

        masks.append(mask)
        confs.append(float(r.boxes.conf[i]))

    return masks, confs