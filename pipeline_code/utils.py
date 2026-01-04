import os
from dotenv import load_dotenv
import math

def gsd(lat_deg):
    return 156543.03392 * math.cos(math.radians(lat_deg)) / (2**20)
load_dotenv()
MODEL_PATH = os.getenv("MODEL_PATH", "trained_model/model.pt")
INPUT_FILE = os.getenv("INPUT_FILE", "input_data/input.xlsx")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output_data")

ZOOM_LEVEL = int(os.getenv("ZOOM_LEVEL", "20"))

SCALE = 2
IMG_SIZE = 1024
CENTER = (IMG_SIZE // 2, IMG_SIZE // 2)


YOLO_CONF = 0.25
MIN_PIXELS = 100

AREA_1200_SQFT = 1200
AREA_2400_SQFT = 2400