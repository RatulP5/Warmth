import { useRef, useEffect } from "react";
import "./OperationsPages.css";
import { gsap } from "gsap";
import {
  LineChart,
  Line,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import { analyticsData } from "../data/analytics.js";
export default function Analytics() {
  const ref = useRef();
  useEffect(() => {
    const ctx = gsap.context(
      () =>
        gsap.from(".chart-card", {
          opacity: 0,
          y: 16,
          stagger: 0.12,
          duration: 0.5,
        }),
      ref,
    );
    return () => ctx.revert();
  }, []);
  return (
    <div className="page analytics-page" ref={ref}>
      <div className="analytics-filter">
        <select>
          <option>2025</option>
          <option>2024</option>
        </select>
        <select>
          <option>Full season</option>
          <option>May</option>
        </select>
        <select>
          <option>All wards</option>
          <option>Ward 37</option>
        </select>
        <select>
          <option>Health risk</option>
          <option>Thermal stress</option>
        </select>
      </div>
      <div className="analytics-grid">
        <Chart
          title="Temperature & thermal stress"
          lines={[
            ["temperature", "#e76f22"],
            ["wbgt", "#c9423a"],
            ["utci", "#7c5cc4"],
          ]}
        />
        <Chart
          title="Health impacts"
          lines={[
            ["mortality", "#c9423a"],
            ["hospitalization", "#d99d18"],
          ]}
        />
      </div>
      <section className="section-card intervention">
        <div className="section-heading">
          <div>
            <p>INTERVENTION COVERAGE</p>
            <h2>High-risk wards and response assets</h2>
          </div>
          <span>Operational access assessment</span>
        </div>
        <div className="asset-grid">
          <Stat
            label="High-risk wards"
            value="29"
            note="8 require immediate action"
          />
          <Stat
            label="Cooling centres"
            value="18"
            note="6 wards outside 15-min access"
          />
          <Stat
            label="Hospitals"
            value="42"
            note="Emergency capacity monitored"
          />
          <Stat label="Water points" value="126" note="14 priority additions" />
        </div>
        <p className="access-alert">
          <b>Access gap:</b> Wards 12, 37, 68, 72, 81 and 93 show high heat risk
          with poor cooling-centre access.
        </p>
      </section>
    </div>
  );
}
function Chart({ title, lines }) {
  return (
    <section className="section-card chart-card">
      <div className="section-heading">
        <div>
          <p>HISTORICAL TREND</p>
          <h2>{title}</h2>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={270}>
        <LineChart data={analyticsData}>
          <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
          <XAxis dataKey="month" />
          <YAxis />
          <Tooltip />
          <Legend />
          {lines.map(([key, color]) => (
            <Line
              type="monotone"
              dataKey={key}
              stroke={color}
              strokeWidth={2.5}
              dot={false}
              key={key}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </section>
  );
}
function Stat({ label, value, note }) {
  return (
    <div>
      <span>{label}</span>
      <b>{value}</b>
      <small>{note}</small>
    </div>
  );
}
