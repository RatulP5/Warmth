import {
  Activity,
  BarChart3,
  BellRing,
  Building2,
  ChevronLeft,
  ChevronRight,
  Flame,
} from "lucide-react";
import { useState } from "react";
import { NavLink } from "react-router-dom";
const items = [
  ["Command Centre", Activity, "/"],
  ["Ward Intelligence", Building2, "/ward-intelligence"],
  ["Alerts & Action", BellRing, "/alerts"],
  ["Analytics", BarChart3, "/analytics"],
];
export default function Sidebar() {
  const [expanded, setExpanded] = useState(false);
  return (
    <aside className={`command-rail ${expanded ? "rail-expanded" : ""}`}>
      <div className="rail-brand">
        <span>
          <Flame size={18} />
        </span>
        <b>
          HEATSHIELD<small>INDIA</small>
        </b>
      </div>
      <nav aria-label="Operations navigation">
        {items.map(([label, Icon, to]) => (
          <NavLink
            to={to}
            className={({ isActive }) => isActive ? "rail-active" : ""}
            key={label}
            title={label}
          >
            <Icon size={18} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <button
        className="rail-toggle"
        onClick={() => setExpanded(!expanded)}
        aria-label="Toggle navigation rail"
      >
        {expanded ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
      </button>
      <div className="rail-status">
        <i /> <span>LIVE</span>
      </div>
    </aside>
  );
}
