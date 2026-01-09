☀️ Helio Yajna – Solar Panel Detection

Hackathon Submission | Team HELIO_YAJNA

🔍 Project Overview (For Evaluators)

Helio Yajna is a fully Dockerized, CPU-only, reproducible pipeline that detects rooftop solar panels from satellite imagery using segmentation-based computer vision and governance-aware buffer logic

The system is designed for fair evaluation, no GPU dependency, and one-command execution.

📥 Input

An Excel (.xlsx) file containing site coordinates:

Column Name	Description
sample_id	Unique site identifier
latitude	Latitude (WGS84)
longitude	Longitude (WGS84)

📁 Mandatory path (inside project folder):

input_data/input.xlsx

⚙️ Processing Pipeline

For each site in the Excel file:

Fetches satellite imagery using Google Static Maps

Runs solar panel instance segmentation

Applies governance buffer logic:

1200 sqft checked first

2400 sqft checked if required

Uses fallback strategies if needed:

Image enhancement

SAHI slicing

Produces a final decision:

SOLAR DETECTED

NO SOLAR DETECTED

📤 Output
1️⃣ Annotated Satellite Images
output_data/artefacts/test/<sample_id>_overlay.jpg


Legend

🟢 Green → Panels inside buffer

🔴 Red → Panels outside buffer

⭕ Buffer circles drawn for interpretability

2️⃣ JSON Prediction (One per Site)
output_data/prediction_files/test/<sample_id>.json


Example

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

🧩 What Evaluators Need (Before Running)
1️⃣ Software Requirement

Docker Desktop
(Windows / Linux / macOS)

2️⃣ API Requirement

Google Maps Static API Key

Static Maps API must be enabled in Google Cloud Console

🔐 Environment Configuration (One-Time Setup)

Create a file named .env in the project root:

MODEL_PATH=trained_model/weights.pt
INPUT_FILE=/data/input.xlsx
OUTPUT_DIR=/app/output_data
ZOOM_LEVEL=20
GOOGLE_API_KEY=YOUR_GOOGLE_MAPS_API_KEY


⚠️ Important Notes

Do NOT add quotes around the API key

.env is read automatically by Docker

No secrets are baked into the image

▶️ How to Execute (Evaluation Instructions)
Step 1️⃣ Clone the Repository
git clone https://github.com/ROHITHLASHETTI/Helio_Yajna_Solar_Detection_2
cd Helio_Yajna_Solar_Detection_2

✅ Option A — Quick Run (Recommended for Judges)

Use the pre-built Docker image (no build required):

▶ Windows (PowerShell)
docker run --env-file .env `
  -v "${PWD}/input_data:/data" `
  -v "${PWD}/output_data:/app/output_data" `
  rohithlashetti03/helio_yajna_solar_detection_2:v2

▶ Linux / macOS
docker run --env-file .env \
  -v $(pwd)/input_data:/data \
  -v $(pwd)/output_data:/app/output_data \
  rohithlashetti03/helio_yajna_solar_detection_2:v2

🛠 Option B — Build & Run Locally
Step 1️⃣ Build the Docker Image
docker build -t helio-yajna-solar-detection .

Step 2️⃣ Run the Pipeline
▶ Windows (PowerShell)
docker run --env-file .env `
  -v "${PWD}/input_data:/data" `
  -v "${PWD}/output_data:/app/output_data" `
  helio-yajna-solar-detection

▶ Linux / macOS
docker run --env-file .env \
  -v $(pwd)/input_data:/data \
  -v $(pwd)/output_data:/app/output_data \
  helio-yajna-solar-detection

🖥️ Console Output (What Evaluators Will See)
[INFO] Processing sample_id: 1
[INFO] No detections inside buffer → applying image enhancement
[INFO] Still no detections → running SAHI slicing
[RESULT] SOLAR DETECTED (buffer=1200 sqft, area=24.1 m²)
[INFO] Inference mode used: SAHI

🧠 Key Design Decisions (For Judges)

✅ CPU-only execution (no GPU dependency)

✅ Fully Dockerized & reproducible

✅ No hardcoded input paths

✅ External data via volume mounts

✅ No secrets inside the image

✅ Deterministic pipeline

✅ Governance-aware buffer logic

✅ Robust fallback inference strategies

❗ Common Issues & Fixes
❌ Google API Error (403)

Ensure Static Maps API is enabled

Ensure API key is correct

Ensure no quotes in .env

❌ Input File Not Found

Confirm file exists at:

input_data/input.xlsx


Confirm volume mounts are correct

❌ Docker Build Is Slow

First build installs ML dependencies (expected)

Subsequent builds are fast due to Docker caching