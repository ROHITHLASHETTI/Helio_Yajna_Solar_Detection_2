import io, requests
from PIL import Image
from .utils import ZOOM_LEVEL, SCALE, IMG_SIZE

def fetch_image(sample_id, lat, lon, api_key, out_path):
    url = "https://maps.googleapis.com/maps/api/staticmap"
    params = {
        "center": f"{lat},{lon}",
        "zoom": ZOOM_LEVEL,
        "scale": SCALE,
        "size": f"{IMG_SIZE}x{IMG_SIZE}",
        "maptype": "satellite",
        "key": api_key,
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    img.save(out_path, "JPEG", quality=95)