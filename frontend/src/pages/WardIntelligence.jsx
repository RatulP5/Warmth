import { useSearchParams } from "react-router-dom";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { analyticsData } from "../data/analytics.js";
import { getWard, riskColors, wards } from "../data/wards.js";
import RiskDrivers from "../components/dashboard/RiskDrivers.jsx";
import ActionRecommendations from "../components/dashboard/ActionRecommendations.jsx";
export default function WardIntelligence() {
  const [params, setParams] = useSearchParams();
  const ward = getWard(params.get("ward") || 37);
  const setWard = (e) => setParams({ ward: e.target.value });
  const thermal = [
    ["Temperature", "39°C"],
    ["Humidity", `${ward.humidity}%`],
    ["Wind speed", `${ward.wind} m/s`],
    ["Solar radiation", `${ward.solar} W/m²`],
  ];
  const stress = [
    ["WBGT", `${ward.wbgt}°C`],
    ["UTCI", `${ward.utci}°C`],
    ["Heat Index", `${ward.heatIndex}°C`],
  ];
  return (
    <div className="page intelligence-page">
      <section className="intelligence-top">
        <div>
          <p>SELECTED AREA</p>
          <select value={ward.id} onChange={setWard}>
            {wards.map((w) => (
              <option value={w.id} key={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        </div>
        <div className="risk-status">
          <span style={{ background: riskColors[ward.riskLevel] }}>
            {ward.riskLevel}
          </span>
          <b>{ward.riskScore}/100</b>
          <small>Current health-risk score</small>
        </div>
        <div className="confidence">
          <span>MODEL CONFIDENCE</span>
          <b>87%</b>
          <i>
            <em />
          </i>
          <small>High confidence · updated 12 min ago</small>
        </div>
      </section>
      <div className="metrics-layout">
        <MetricBlock title="Thermal conditions" items={thermal} />
        <MetricBlock title="Human thermal stress" items={stress} />
        <MetricBlock
          title="Environmental factors"
          items={[
            ["Land surface temperature", `${ward.surfaceTemp}°C`],
            ["Vegetation cover", `${ward.vegetation}%`],
            ["Built-up area", `${ward.builtUp}%`],
            ["Outdoor exposure", `${ward.outdoorExposure}%`],
          ]}
        />
        <MetricBlock
          title="Vulnerability indicators"
          items={[
            ["Elderly population", `${ward.elderly}%`],
            [
              "Population density",
              `${ward.density.toLocaleString("en-IN")}/km²`,
            ],
            ["Healthcare accessibility", `${ward.healthAccess}/100`],
            ["Population exposed", ward.population],
          ]}
        />
      </div>
      <section className="section-card chart-card">
        <div className="section-heading">
          <div>
            <p>FORECAST</p>
            <h2>5-day thermal stress projection</h2>
          </div>
          <span>Peak: Tomorrow</span>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={analyticsData.slice(3, 8)}>
            <defs>
              <linearGradient id="heat" x1="0" x2="0" y1="0" y2="1">
                <stop stopColor="#e76f22" stopOpacity=".36" />
                <stop offset="1" stopColor="#e76f22" stopOpacity="0" />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip />
            <Area
              dataKey="utci"
              stroke="#e76f22"
              fill="url(#heat)"
              strokeWidth={2}
            />
            <Area
              dataKey="wbgt"
              stroke="#c9423a"
              fill="transparent"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </section>
      <div className="insight-grid">
        <RiskDrivers ward={ward} />
        <ActionRecommendations risk={ward.riskLevel} />
      </div>
    </div>
  );
}
function MetricBlock({ title, items }) {
  return (
    <section className="metric-block">
      <h3>{title}</h3>
      {items.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <b>{value}</b>
        </div>
      ))}
    </section>
  );
}
