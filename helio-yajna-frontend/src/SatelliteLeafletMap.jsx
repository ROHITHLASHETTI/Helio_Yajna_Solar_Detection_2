import { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// 3D Red Ball Pin Icon for selected rooftop
const pinSvg = encodeURIComponent(`
<svg width="40" height="60" viewBox="0 0 60 90" fill="none" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="30" cy="85" rx="8" ry="3" fill="black" fill-opacity="0.3"/>
    <rect x="27" y="30" width="6" height="55" fill="#C0C0C0" stroke="#808080" stroke-width="1"/>
    <circle cx="30" cy="30" r="20" fill="url(#grad1)" stroke="#A00000" stroke-width="1"/>
    <defs>
        <radialGradient id="grad1" cx="35%" cy="35%" r="65%">
            <stop offset="0%" stop-color="#FF5555" />
            <stop offset="100%" stop-color="#CC0000" />
        </radialGradient>
    </defs>
</svg>
`)

const selectedPinIcon = L.icon({
  iconUrl: `data:image/svg+xml;charset=UTF-8,${pinSvg}`,
  iconSize: [40, 60],
  iconAnchor: [20, 60],
  popupAnchor: [0, -60],
})

// User Location Blue Dot
const userLocationSvg = encodeURIComponent(`
<svg width="36" height="36" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="20" cy="20" r="18" fill="#4285F4" fill-opacity="0.25"/>
    <circle cx="20" cy="20" r="9" fill="white"/>
    <circle cx="20" cy="20" r="7" fill="#4285F4"/>
</svg>
`)

const userLocationIcon = L.icon({
  iconUrl: `data:image/svg+xml;charset=UTF-8,${userLocationSvg}`,
  iconSize: [36, 36],
  iconAnchor: [18, 18],
})

// Teardrop marker helper for bulk results
function createBulkIcon(hasSolar, isSelected) {
  const color = hasSolar ? '#4ade80' : '#ef4444'
  const stroke = isSelected ? '#ffffff' : '#000000'
  const svg = encodeURIComponent(`
    <svg width="28" height="38" viewBox="0 0 24 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 2C7.03 2 3 6.03 3 11C3 17.5 12 30 12 30C12 30 21 17.5 21 11C21 6.03 16.97 2 12 2Z" fill="${color}" stroke="${stroke}" stroke-width="${isSelected ? 2 : 1}"/>
      <circle cx="12" cy="11" r="4" fill="white"/>
    </svg>
  `)
  return L.icon({
    iconUrl: `data:image/svg+xml;charset=UTF-8,${svg}`,
    iconSize: isSelected ? [34, 46] : [28, 38],
    iconAnchor: isSelected ? [17, 46] : [14, 38],
  })
}

function MapController({ center, zoom, flyTarget, onMapReady }) {
  const map = useMap()

  useEffect(() => {
    if (onMapReady) {
      onMapReady(map)
    }
  }, [map, onMapReady])

  useEffect(() => {
    if (flyTarget) {
      map.flyTo([flyTarget.lat, flyTarget.lng], Math.max(map.getZoom(), 18), {
        duration: 1.2,
      })
    }
  }, [flyTarget, map])

  return null
}

function MapEventsHandler({ onMapClick }) {
  useMapEvents({
    click(e) {
      if (onMapClick) {
        onMapClick({
          latLng: {
            lat: () => e.latlng.lat,
            lng: () => e.latlng.lng,
          },
        })
      }
    },
  })
  return null
}

export default function SatelliteLeafletMap({
  center = { lat: 17.2608, lng: 78.3072 },
  zoom = 18,
  selectedLocation,
  userLocation,
  bulkResults = [],
  filterMode = 'all',
  onMapClick,
  onBulkSelect,
  flyTarget,
  onMapInstance,
}) {
  const mapRef = useRef(null)

  const isSameLoc = (a, b) => {
    if (!a || !b) return false
    const aLat = a.lat
    const aLng = a.lng || a.lon
    const bLat = b.lat
    const bLng = b.lng || b.lon
    return Math.abs(aLat - bLat) < 0.0001 && Math.abs(aLng - bLng) < 0.0001
  }

  const filteredBulk = bulkResults.filter((res) => {
    if (filterMode === 'solar') return res.has_solar
    if (filterMode === 'no-solar') return !res.has_solar
    return true
  })

  return (
    <div className="w-full h-full relative" style={{ background: '#0a0a0a' }}>
      <MapContainer
        center={[center.lat, center.lng]}
        zoom={zoom}
        style={{ width: '100%', height: '100%' }}
        zoomControl={false}
        attributionControl={false}
        ref={mapRef}
      >
        {/* Esri World Imagery (High-Resolution Satellite Imagery) */}
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          maxZoom={20}
          maxNativeZoom={19}
        />

        {/* Labels & Roads Overlay */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png"
          subdomains="abcd"
          maxZoom={20}
          opacity={0.85}
        />

        <MapEventsHandler onMapClick={onMapClick} />
        <MapController
          center={center}
          zoom={zoom}
          flyTarget={flyTarget}
          onMapReady={onMapInstance}
        />

        {/* User Location */}
        {userLocation && (
          <Marker
            position={[userLocation.lat, userLocation.lng]}
            icon={userLocationIcon}
            zIndexOffset={100}
          />
        )}

        {/* Selected Location Pin */}
        {selectedLocation && (
          <Marker
            position={[selectedLocation.lat, selectedLocation.lng]}
            icon={selectedPinIcon}
            zIndexOffset={500}
          />
        )}

        {/* Bulk Markers */}
        {filteredBulk.map((res, idx) => {
          const lat = res.lat
          const lng = res.lng || res.lon
          const isSelected = selectedLocation && isSameLoc({ lat, lng }, selectedLocation)
          return (
            <Marker
              key={`bulk-leaflet-${idx}`}
              position={[lat, lng]}
              icon={createBulkIcon(res.has_solar, isSelected)}
              eventHandlers={{
                click: () => {
                  if (onBulkSelect) {
                    onBulkSelect(res)
                  }
                },
              }}
              zIndexOffset={isSelected ? 450 : 200}
            />
          )
        })}
      </MapContainer>
    </div>
  )
}
