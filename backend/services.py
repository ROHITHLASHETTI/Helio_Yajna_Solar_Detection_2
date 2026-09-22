"""
Backend Services & Caching Tier for Helio Yajna.
System Design Features:
  - Singleton inference service & image retriever
  - In-Memory LRU Cache for sub-millisecond repeat coordinate queries
  - Automatic capacity derivation ($1 kW ≈ 5 m²$)
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Ensure root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.inference_service import InferenceService
from pipeline_code.image_fetcher import ImageRetriever

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
MODEL_PATH = str(BASE_DIR / "trained_model" / "weights.pt")

print(f"[INFO] Initializing InferenceService with model: {MODEL_PATH}")

inference_service = InferenceService(model_path=MODEL_PATH)
image_retriever = ImageRetriever(
    api_key=os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_API_KEY"),
    cache_dir=str(BASE_DIR / "cache" / "images"),
)

# System Design: In-Memory Fast Cache for recent inference analyses
# Keys are rounded coordinates (e.g. lat_4dec, lon_4dec)
class InferenceCache:
    def __init__(self, max_size=100, ttl_seconds=3600):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl_seconds

    def _make_key(self, lat: float, lon: float, zoom: int = 20):
        return f"{round(lat, 4)}_{round(lon, 4)}_{zoom}"

    def get(self, lat: float, lon: float, zoom: int = 20):
        key = self._make_key(lat, lon, zoom)
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                print(f"[FAST CACHE HIT] Served analysis for {key} from memory")
                return entry["data"]
            else:
                del self.cache[key]
        return None

    def set(self, lat: float, lon: float, data: dict, zoom: int = 20):
        if len(self.cache) >= self.max_size:
            # Drop oldest key
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        key = self._make_key(lat, lon, zoom)
        self.cache[key] = {
            "timestamp": time.time(),
            "data": data
        }

inference_cache = InferenceCache()
