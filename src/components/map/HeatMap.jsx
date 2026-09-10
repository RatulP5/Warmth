import {
  AttributionControl,
  GeoJSON,
  MapContainer,
  TileLayer,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "./HeatMap.css";
import wardBoundariesText from "../../data/kolkata-wards.geojson?raw";
import {
  mapLayers,
  layerRisk,
  riskColors,
  riskOrder,
} from "../../data/wards.js";

const rawWardBoundaries = JSON.parse(wardBoundariesText);

function flipGeometryCoordinates(geometry) {
  if (geometry.type === "GeometryCollection") {
    return {
      ...geometry,
      geometries: geometry.geometries.map(flipGeometryCoordinates),
    };
  }

  function flipCoordinates(coordinates) {
    if (typeof coordinates[0] === "number") {
      const [latitude, longitude, ...rest] = coordinates;
      return [longitude, latitude, ...rest];
    }

    return coordinates.map(flipCoordinates);
  }

  return {
    ...geometry,
    coordinates: flipCoordinates(geometry.coordinates),
  };
}

const wardBoundaries = {
  ...rawWardBoundaries,
  features: rawWardBoundaries.features.map((feature) => ({
    ...feature,
    geometry: flipGeometryCoordinates(feature.geometry),
  })),
};
const dayRiskShift = [0, 1, 0, -1, -2];

function wardNumber(feature) {
  return Number(
    String(feature.properties.WARD || feature.properties.Name || "").trim(),
  );
}

export function MapLayerSelector({ layer, onChange }) {
  return (
    <div className="layer-selector">
      {mapLayers.map(([key, label]) => (
        <button
          onClick={() => onChange(key)}
          className={layer === key ? "selected" : ""}
          key={key}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

export function MapLegend({ layer }) {
  const label = mapLayers.find(([key]) => key === layer)?.[1];
  return (
    <div className="map-legend">
      <span>{label}</span>
      {Object.entries(riskColors).map(([risk, color]) => (
        <span key={risk}>
          <i style={{ background: color }} />
          {risk}
        </span>
      ))}
    </div>
  );
}

export default function HeatMap({
  wards,
  layer,
  selectedWard,
  onWardSelect,
  day = 0,
}) {
  const wardsByNumber = new globalThis.Map(
    wards.map((ward) => [ward.id, ward]),
  );
  const getJoinedWard = (feature) => wardsByNumber.get(wardNumber(feature));
  const getRisk = (ward) => {
    const baseRisk = layerRisk(ward, layer);
    if (layer !== "riskScore") return baseRisk;
    return riskOrder[
      Math.max(0, Math.min(3, riskOrder.indexOf(baseRisk) + dayRiskShift[day]))
    ];
  };
  const style = (feature) => {
    const ward = getJoinedWard(feature);
    if (!ward)
      return {
        fillColor: "#cbd5d8",
        fillOpacity: 0.35,
        color: "#ffffff",
        weight: 0.6,
      };
    const selected = ward.id === selectedWard?.id;
    return {
      fillColor: riskColors[getRisk(ward)],
      fillOpacity: selected ? 0.92 : 0.72,
      color: selected ? "#102e37" : "#ffffff",
      weight: selected ? 3 : 0.8,
    };
  };
  const onEachFeature = (feature, leafletLayer) => {
    const ward = getJoinedWard(feature);
    if (!ward) return;
    leafletLayer.bindTooltip(
      `<strong>Ward ${ward.id}</strong><br/>${ward.name.replace(`Ward ${ward.id} · `, "")}<br/><b>${ward.riskLevel} risk · ${ward.riskScore}/100</b><br/>WBGT ${ward.wbgt}°C · UTCI ${ward.utci}°C`,
      { sticky: true, className: "ward-tooltip" },
    );
    leafletLayer.on({
      mouseover: (event) =>
        event.target.setStyle({ weight: 2.5, fillOpacity: 0.92 }),
      mouseout: (event) => event.target.setStyle(style(feature)),
      click: () => onWardSelect(ward),
    });
  };
  return (
    <div className="leaflet-map-wrap">
      <MapContainer
        center={[22.5726, 88.3639]}
        zoom={11.7}
        scrollWheelZoom={false}
        className="kolkata-leaflet-map"
      >
        <TileLayer
          attribution="&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <AttributionControl prefix={false} />
        <GeoJSON
          key={`${layer}-${day}-${selectedWard?.id || "none"}`}
          data={wardBoundaries}
          style={style}
          onEachFeature={onEachFeature}
        />
      </MapContainer>
      <div className="boundary-attribution">
        Ward boundaries:{" "}
        <a
          href="https://bharatlas.com/view/wards_kolkata"
          target="_blank"
          rel="noreferrer"
        >
          OpenCity / Oorvani Foundation via Bharatlas
        </a>
        , ODbL-1.0.
      </div>
    </div>
  );
}
