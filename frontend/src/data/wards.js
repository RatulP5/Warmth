export const riskOrder = ["Low", "Moderate", "High", "Extreme"];
export const riskColors = {
  Low: "#2f9e6e",
  Moderate: "#d99d18",
  High: "#e76f22",
  Extreme: "#c9423a",
};
export const mapLayers = [
  ["riskScore", "Overall Health Risk"],
  ["wbgt", "WBGT"],
  ["utci", "UTCI"],
  ["mortalityRisk", "Mortality Risk"],
  ["hospitalizationRisk", "Hospitalization Risk"],
  ["surfaceTemp", "Land Surface Temperature"],
  ["vegetation", "Vegetation"],
  ["vulnerability", "Vulnerability"],
];
const wardNames = [
  "Burrabazar",
  "Jorasanko",
  "Maniktala",
  "Beliaghata",
  "Entally",
  "Park Circus",
  "Topsia",
  "Tangra",
  "Garden Reach",
  "Metiabruz",
  "Khidirpur",
  "Alipore",
  "Bhowanipore",
  "Kalighat",
  "Tollygunge",
  "Jadavpur",
  "Kasba",
  "Ballygunge",
  "Salt Lake Fringe",
  "Ultadanga",
];
export const wards = Array.from({ length: 141 }, (_, index) => {
  const id = index + 1;
  const riskLevel =
    id <= 8 ? "Extreme" : id <= 29 ? "High" : id <= 63 ? "Moderate" : "Low";
  const riskScore =
    riskLevel === "Extreme"
      ? 84 + (id % 13)
      : riskLevel === "High"
        ? 65 + (id % 14)
        : riskLevel === "Moderate"
          ? 42 + (id % 17)
          : 18 + (id % 19);
  return {
    id,
    name: `Ward ${id} · ${wardNames[index % wardNames.length]}`,
    riskLevel,
    riskScore,
    wbgt: +(27.8 + riskScore / 18).toFixed(1),
    utci: +(33 + riskScore / 7).toFixed(1),
    heatIndex: Math.round(36 + riskScore / 4),
    mortalityRisk: Math.min(96, Math.round(riskScore * 0.78)),
    hospitalizationRisk: Math.min(94, Math.round(riskScore * 0.7)),
    surfaceTemp: +(33 + riskScore / 12).toFixed(1),
    vegetation: Math.max(9, Math.round(74 - riskScore * 0.55)),
    vulnerability: Math.min(94, Math.round(28 + riskScore * 0.62)),
    population: (19500 + ((id * 731) % 51000)).toLocaleString("en-IN"),
    humidity: 54 + (id % 20),
    wind: +(1.4 + (id % 9) * 0.3).toFixed(1),
    solar: 690 + (id % 120),
    builtUp: 54 + ((id * 3) % 39),
    outdoorExposure: 38 + ((id * 7) % 52),
    elderly: 7 + (id % 14),
    density: 28000 + ((id * 913) % 33000),
    healthAccess: 38 + ((id * 11) % 50),
  };
});
export const getWard = (id) =>
  wards.find((ward) => ward.id === Number(id)) || wards[36];
export function layerValue(ward, layer) {
  return ward[layer] ?? ward.riskScore;
}
export function layerRisk(ward, layer) {
  const value = layerValue(ward, layer);
  if (layer === "vegetation")
    return value < 25
      ? "Extreme"
      : value < 40
        ? "High"
        : value < 58
          ? "Moderate"
          : "Low";
  const normalized = ["wbgt", "utci", "surfaceTemp"].includes(layer)
    ? (value - (layer === "wbgt" ? 27 : layer === "utci" ? 33 : 33)) * 8
    : value;
  return normalized >= 80
    ? "Extreme"
    : normalized >= 60
      ? "High"
      : normalized >= 40
        ? "Moderate"
        : "Low";
}
