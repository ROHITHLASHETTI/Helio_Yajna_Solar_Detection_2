import cv2
import numpy as np
from sahi.models.ultralytics import UltralyticsDetectionModel
from sahi.predict import get_sliced_prediction
from .utils import IMG_SIZE


def run_sahi(model_path, image_path, conf):
    model = UltralyticsDetectionModel(
        model_path=model_path,
        confidence_threshold=conf,
        device="cpu"
    )

    result = get_sliced_prediction(
        image=image_path,
        detection_model=model,
        slice_height=640,         
        slice_width=640,
        overlap_height_ratio=0.1,
        overlap_width_ratio=0.1
    )
    masks, confs = [], []

    for obj in result.object_prediction_list:
        if obj.mask is None:
            continue
        raw_mask = obj.mask.bool_mask.astype("uint8")
        mask = cv2.resize(
            raw_mask,
            (IMG_SIZE, IMG_SIZE),
            interpolation=cv2.INTER_NEAREST
        )
        masks.append(mask)
        confs.append(obj.score.value)

    return masks, confs
