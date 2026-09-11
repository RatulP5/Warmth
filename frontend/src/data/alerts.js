export const initialAlerts = [
  {
    id: 1,
    severity: "Extreme",
    ward: 37,
    title: "Peak impact expected Friday",
    reasons: ["High WBGT", "High vulnerability", "Low vegetation"],
    actions: [
      "Activate cooling centre",
      "Increase water availability",
      "Notify field teams",
    ],
  },
  {
    id: 2,
    severity: "Extreme",
    ward: 12,
    title: "Severe heat stress conditions",
    reasons: ["Heat index above 45°C", "High built-up density"],
    actions: ["Deploy water points", "Issue public advisory"],
  },
  {
    id: 3,
    severity: "High",
    ward: 68,
    title: "Outdoor worker exposure elevated",
    reasons: ["Low wind speed", "High outdoor exposure"],
    actions: ["Shift work hours", "Inspect hydration points"],
  },
  {
    id: 4,
    severity: "Moderate",
    ward: 102,
    title: "Vulnerable population monitoring",
    reasons: ["Moderate WBGT", "Elderly population"],
    actions: ["Coordinate health outreach"],
  },
];
