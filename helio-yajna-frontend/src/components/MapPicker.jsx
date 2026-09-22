import { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Custom pulsing marker (amber, matches the "solar" accent) instead of
// Leaflet's default pin — also sidesteps the broken-default-icon-path
// issue bundlers hit with Leaflet's marker images.
const pulseIcon = L.divIcon({
  className: 'map-pulse-icon',
  html: '<span class="map-pulse-ring"></span><span class="map-pulse-dot"></span>',
  iconSize: [20, 20],
  iconAnchor: [10, 10],
})

function ClickCapture({ onPick, disabled }) {
  useMapEvents({
    click(e) {
      if (disabled) return
      onPick(e.latlng.lat, e.latlng.lng)
    },
  })
  return null
}

function Recenter({ position }) {
  const map = useMap()
  useEffect(() => {
    if (position) {
      map.flyTo(position, Math.max(map.getZoom(), 14), { duration: 0.6 })
    }
  }, [position?.[0], position?.[1]])
  return null
}

const INDIA_CENTER = [22.9734, 78.6569]

export default function MapPicker({ lat, lon, onPick, disabled }) {
  const hasPosition = lat !== '' && lon !== '' && !Number.isNaN(Number(lat)) && !Number.isNaN(Number(lon))
  const position = hasPosition ? [Number(lat), Number(lon)] : null

  return (
    <div className="map-frame">
      <MapContainer
        center={position || INDIA_CENTER}
        zoom={position ? 15 : 5}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ClickCapture onPick={onPick} disabled={disabled} />
        {position && (
          <>
            <Marker position={position} icon={pulseIcon} />
            <Recenter position={position} />
          </>
        )}
      </MapContainer>
      {disabled && (
        <div className="map-overlay">
          <span className="spinner" />
          Running detection…
        </div>
      )}
    </div>
  )
}
