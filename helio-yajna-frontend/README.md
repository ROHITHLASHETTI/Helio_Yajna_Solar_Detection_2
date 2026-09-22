# Helio Yajna — Frontend

React + Vite dashboard for the rooftop solar verification system. Four views: an
audit dashboard, single-image detection, batch upload, and coordinate lookup —
all rendering the same result schema your backend returns.

## Run it

```bash
npm install
cp .env.example .env     # set VITE_API_BASE_URL to your backend
npm run dev
```

Build for production with `npm run build`; output goes to `dist/`.

## Coordinate mode: click-to-detect map

The Coordinates view (`src/components/CoordinateSearch.jsx` +
`src/components/MapPicker.jsx`) now shows a live map (Leaflet + OpenStreetMap
tiles, no API key needed). Clicking anywhere on it:

1. reads the lat/lon under the cursor,
2. fills the latitude/longitude fields,
3. immediately calls `detectByCoordinates` — no extra click needed.

The lat/lon fields stay editable below the map for a precise re-run, and the
"Fetch & verify site" button re-triggers detection with whatever is currently
in those fields. A marker with a pulsing amber ring marks the last point
checked; the map dims with a loading overlay while a request is in flight so
a second click can't queue on top of the first.

If you'd rather use satellite/aerial tiles instead of OpenStreetMap's street
map (more useful for actually eyeballing a rooftop before clicking), swap the
`TileLayer` `url` in `MapPicker.jsx` for a provider that allows hotlinking —
Esri's World Imagery layer is a common free option:
`https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`

## Wiring up your backend

Everything the app expects from your API lives in one file: **`src/api.js`**.
Four calls, each documented with the exact JSON shape it expects back:

| Function | Method | Path | Purpose |
|---|---|---|---|
| `detectSingle(file, opts)` | POST | `/api/detect/image` | multipart upload, one image |
| `detectBatch(files, opts)` | POST | `/api/detect/batch` | multipart upload, many images |
| `detectByCoordinates({lat, lon, bufferRadiusSqft})` | POST | `/api/detect/coordinates` | JSON body |
| `fetchHistory()` | GET | `/api/results` | past verification runs, for the dashboard |

If your actual routes differ, only the `ENDPOINTS` object at the top of
`src/api.js` needs to change — no component touches the URLs directly.

Every one of those calls is expected to resolve to (or an array of) this
object, matching your stated output schema:

```json
{
  "sample_id": "2",
  "lat": 25.1333,
  "lon": 71.1833,
  "has_solar": false,
  "confidence": 0.0,
  "pv_area_sqm_est": 0.0,
  "euclidean_distance_m_est": 0.0,
  "buffer_radius_sqft": 2400,
  "qc_status": "VERIFIABLE",
  "bbox_or_mask": [],
  "image_metadata": {
    "source": "Cache",
    "capture_date": "2026-09-22",
    "zoom": 20,
    "inference_mode": "not_found"
  }
}
```

`qc_status` drives the status badge color — it currently recognizes
`VERIFIABLE`, `FLAGGED`, `PENDING`, `NOT_FOUND`. Add more cases in
`src/components/StatusBadge.jsx` if your backend emits others.

`bbox_or_mask` is read as a polygon: an array of `[x, y]` points in
1280×1280 image pixel space. If your model returns a different format
(e.g. RLE-encoded masks, or a list of separate instance polygons rather
than one), convert to that shape in your API response, or extend the
overlay logic in `src/components/ResultCard.jsx`.

## CORS

Since the frontend calls your backend directly from the browser, make sure
your backend allows the frontend's origin (`http://localhost:5173` in dev).

## Structure

```
src/
  api.js                 — all backend calls, single source of truth for routes
  App.jsx                — shell: sidebar rail, top bar, mode switch
  styles.css             — design tokens + all styling
  components/
    Dashboard.jsx         — summary stats + verification history
    SingleUpload.jsx       — one image → one result
    BatchUpload.jsx        — many images → table + detail panel
    CoordinateSearch.jsx   — lat/lon → fetch tile → detect
    ResultCard.jsx         — renders the result schema + mask overlay
    StatusBadge.jsx        — qc_status → colored pill
```
