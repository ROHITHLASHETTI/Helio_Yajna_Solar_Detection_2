Helio Yajna – Solar Panel Detection

Hackathon Submission | Team HELIO_YAJNA

🔹 What This Project Does (For Evaluators)

This system detects rooftop solar panels from satellite imagery using a YOLOv8 Instance Segmentation model.

Input
An Excel file containing site coordinates (Latitude, Longitude).

Processing

Fetches satellite images (Google Static Maps)

Runs segmentation-based solar detection

Applies governance buffer logic (1200 sqft → 2400 sqft)

Uses fallback strategies (image enhancement, SAHI slicing)

Output

Annotated satellite images

One JSON prediction per site

The entire pipeline is Dockerized, CPU-only, and fully reproducible.

🔹 What Evaluators Need Before Running
1️. Software Requirement

Docker Desktop (Windows / Linux / macOS)

2️. API Requirement

A Google Maps Static API Key
(must have Static Maps API enabled)

🔹 Input Data Format (Mandatory)

Evaluators must provide an Excel (.xlsx) file with the following columns:

Column	Description
sample_id	Unique site identifier
latitude	Latitude (WGS84)
longitude	Longitude (WGS84)

📁 File location (inside project folder):

input_data/input.xlsx

🔹 Environment Configuration (One-Time Setup)

Create a file named .env in the project root.

MODEL_PATH=trained_model/weights.pt
INPUT_FILE=/data/input.xlsx
OUTPUT_DIR=/app/output_data
ZOOM_LEVEL=20
GSD=0.15
GOOGLE_API_KEY=YOUR_GOOGLE_MAPS_API_KEY


⚠️ Notes for Evaluators:

Do not add quotes around the API key

.env is read automatically by Docker

🔹 How to Execute (Primary Evaluation Instructions)
Step 1️⃣ Build the Docker Image

Run this once from the project root:

docker build -t helio-yajna-solar-detection .

Step 2️⃣ Run the Pipeline
▶ Windows (PowerShell)
docker run --env-file .env `
  -v ${PWD}\input_data:/data `
  -v ${PWD}\output_data:/app/output_data `
  helio-yajna-solar-detection

▶ Linux / macOS
docker run --env-file .env \
  -v $(pwd)/input_data:/data \
  -v $(pwd)/output_data:/app/output_data \
  helio-yajna-solar-detection

🔹 What Happens During Execution

For each row in the Excel file:

Satellite image is downloaded

Solar panel segmentation is performed

Buffer logic is applied:

1200 sqft checked first

2400 sqft checked if required

Final decision is made:

SOLAR DETECTED / NO SOLAR DETECTED

Outputs are saved automatically

🔹 Console Output Example (What Evaluators Will See)
[INFO] Processing sample_id: 1
[INFO] No detections inside buffer → applying image enhancement
[INFO] Still no detections → running SAHI slicing
[RESULT] SOLAR DETECTED (buffer=1200 sqft, area=24.1 m²)
[INFO] Inference mode used: SAHI

🔹 Output Files Generated
1️⃣ Annotated Images
output_data/artefacts/test/<sample_id>_overlay.jpg


Green regions → panels inside buffer

Red outlines → panels outside buffer

Buffer circles drawn for interpretability

2️⃣ JSON Prediction per Site
output_data/prediction_files/test/<sample_id>.json


Example:

{
  "sample_id": 1234,
  "lat": 12.9716,
  "lon": 77.5946,
  "has_solar": true,
  "confidence": 0.92,
  "buffer_radius_sqft": 1200,
  "pv_area_sqm_est": 23.5,
  "euclidean_distance_m_est": 0,
  "qc_status": "VERIFIABLE",
  "bbox_or_mask": "mask",
  "image_metadata": {
    "source": "Google Static Maps",
    "zoom": 20,
    "inference_mode": "PRIMARY"
  }
}

🔹 Key Design Decisions (For Judges)

CPU-only execution (no GPU dependency)

No hardcoded input paths

No secrets baked into image

External input via volume mount

Deterministic and reproducible pipeline

🔹 Common Issues & Fixes
❌ Google API Error (403)

Ensure Static Maps API is enabled

Ensure API key is correct (no quotes)

❌ Input file not found

Ensure input_data/input.xlsx exists

Ensure Docker volume mount path is correct

❌ Docker build slow

First build installs ML dependencies (expected)

Subsequent builds are fast due to caching