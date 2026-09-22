"""
High-quality satellite image retrieval from Google Maps Static API.
Key fix: scale=2 produces 1280x1280px (2x resolution) instead of 640x640px.
Without scale=2, small solar panels are invisible. This was the root cause
of missed detections in the original port.

MD5-based disk cache avoids redundant API calls across runs.
"""
import requests
import os
import hashlib
import cv2
import numpy as np
from PIL import Image
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Google Maps Static API caps size at 640x640 per tile.
# scale=2 doubles pixel density → effective 1280x1280 at the same geo coverage.
# This is CRITICAL for detecting small rooftop solar panels.
FETCH_SIZE   = "640x640"   # API tile size (max allowed)
FETCH_SCALE  = 2            # scale=2 → 1280x1280 actual pixels
FETCH_ZOOM   = 20           # street-level zoom for rooftop detail
FETCH_FORMAT = "JPEG"       # lossless would be PNG but JPEG saves space; q=95


class ImageRetriever:
    """
    Fetches high-resolution satellite images from Google Maps Static API.

    Parameters
    ----------
    api_key    : Google Maps API key (reads GOOGLE_MAPS_API_KEY env var if None)
    cache_dir  : Directory for MD5-cached images (avoids repeat API calls)
    use_mock   : Force mock grey image (for unit tests)
    """

    def __init__(self, api_key=None, cache_dir="cache/images", use_mock=False):
        self.api_key   = (api_key
                          or os.getenv("GOOGLE_MAPS_API_KEY")
                          or os.getenv("GOOGLE_API_KEY"))
        self.cache_dir = cache_dir
        self.use_mock  = use_mock
        os.makedirs(self.cache_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_image(self, lat, lon, zoom=FETCH_ZOOM,
                  size=FETCH_SIZE, scale=FETCH_SCALE, maptype="satellite"):
        """
        Return (filepath, metadata_dict) for a satellite image at (lat, lon).

        Images are cached on disk by MD5 of the request parameters.
        scale=2 is the key parameter that doubles pixel resolution.
        """
        # Unique cache key includes scale so changing scale busts old cache
        params_str = f"{lat}_{lon}_{zoom}_{size}_scale{scale}_{maptype}"
        filename   = hashlib.md5(params_str.encode()).hexdigest() + ".jpg"
        filepath   = os.path.join(self.cache_dir, filename)

        # --- Cache hit ---
        if os.path.exists(filepath):
            print(f"  [CACHE] Loaded from disk: {filename}")
            return filepath, self._meta(filepath, "Cache",
                                        datetime.now().strftime("%Y-%m-%d"))

        if self.use_mock:
            return self._mock(filepath), self._meta(filepath, "Mock",
                                                    datetime.now().strftime("%Y-%m-%d"))

        if not self.api_key:
            print("  [WARN] No GOOGLE_MAPS_API_KEY. Using grey mock image.")
            return self._mock(filepath), self._meta(filepath, "Mock (no key)",
                                                    datetime.now().strftime("%Y-%m-%d"))

        # --- Fetch from Google Maps Static API ---
        url    = "https://maps.googleapis.com/maps/api/staticmap"
        params = {
            "center":  f"{lat},{lon}",
            "zoom":    zoom,
            "size":    size,       # 640x640 — API max per tile
            "scale":   scale,      # ×2 → 1280×1280 effective pixels
            "maptype": maptype,
            "key":     self.api_key,
        }

        try:
            resp = requests.get(url, params=params, timeout=20)
            resp.raise_for_status()

            img_pil = Image.open(BytesIO(resp.content)).convert("RGB")

            # Apply CLAHE contrast enhancement to improve panel visibility
            img_enhanced = self._enhance_contrast(img_pil)
            img_enhanced.save(filepath, "JPEG", quality=95)

            actual_w, actual_h = img_enhanced.size
            print(f"  [FETCH] {actual_w}×{actual_h}px satellite image saved.")
            return filepath, self._meta(filepath, "Google Maps Static API",
                                        datetime.now().strftime("%Y-%m-%d"))

        except Exception as exc:
            print(f"  [WARN] API fetch failed: {exc}. Using mock image.")
            return self._mock(filepath), self._meta(filepath, "Mock (fallback)",
                                                    datetime.now().strftime("%Y-%m-%d"))

    # ------------------------------------------------------------------
    # Image quality enhancement (applied once at fetch time)
    # ------------------------------------------------------------------

    def _enhance_contrast(self, pil_img):
        """
        Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to the
        luminance channel. Improves visibility of low-contrast solar panels
        against similar-coloured rooftops without blowing out colours.
        """
        img_bgr  = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        lab      = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        l, a, b  = cv2.split(lab)

        clahe    = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_clahe  = clahe.apply(l)

        lab_out  = cv2.merge([l_clahe, a, b])
        bgr_out  = cv2.cvtColor(lab_out, cv2.COLOR_LAB2BGR)
        rgb_out  = cv2.cvtColor(bgr_out, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb_out)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _mock(self, filepath):
        """Grey placeholder image (1280×1280) for testing without API key."""
        img = Image.new("RGB", (1280, 1280), color=(73, 109, 137))
        img.save(filepath, "JPEG")
        return filepath

    def _meta(self, filepath, source, date):
        return {"filepath": filepath, "source": source, "capture_date": date}


# ---------------------------------------------------------------------------
# Convenience wrapper kept for any legacy callers
# ---------------------------------------------------------------------------

def fetch_image(sample_id, lat, lon, api_key, out_path):
    """One-shot fetch and save to an explicit path."""
    retriever = ImageRetriever(api_key=api_key)
    src_path, _ = retriever.get_image(lat, lon)
    if src_path != out_path:
        import shutil
        shutil.copy2(src_path, out_path)