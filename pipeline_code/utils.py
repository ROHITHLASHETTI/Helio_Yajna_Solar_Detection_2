import os
from dotenv import load_dotenv

load_dotenv()
MODEL_PATH = os.getenv("MODEL_PATH", "trained_model/model.pt")
INPUT_FILE = os.getenv("INPUT_FILE", "input_data/input.xlsx")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output_data")

ZOOM_LEVEL = int(os.getenv("ZOOM_LEVEL", "20"))
GSD = float(os.getenv("GSD", "0.15"))

SCALE = 2
IMG_SIZE = 640
CENTER = (IMG_SIZE // 2, IMG_SIZE // 2)


YOLO_CONF = 0.10
MIN_PIXELS = 100

AREA_1200_SQFT = 1200
AREA_2400_SQFT = 2400
