import { ArrowUpRight, X } from "lucide-react";
import "./WardPanel.css";
import { useLayoutEffect, useRef } from "react";
import { gsap } from "gsap";
import { riskColors } from "../../data/wards.js";
export default function WardPanel({ ward, onClose }) {
  const panelRef = useRef();
  useLayoutEffect(() => {
    if (!ward || window.matchMedia("(prefers-reduced-motion: reduce)").matches)
      return;
    const ctx = gsap.context(
      () =>
        gsap.fromTo(
          panelRef.current,
          { x: 36, opacity: 0 },
          { x: 0, opacity: 1, duration: 0.38, ease: "power3.out" },
        ),
      panelRef,
    );
    return () => ctx.revert();
  }, [ward]);
  if (!ward) return null;
  const metrics = [
    ["Thermal stress", `${ward.riskScore}/100`],
    ["WBGT", `${ward.wbgt} deg C`],
    ["UTCI", `${ward.utci} deg C`],
    ["Heat index", `${ward.heatIndex} deg C`],
    ["Population exposed", ward.population],
    ["Peak-risk", "Tomorrow"],
  ];
  return (
    <aside
      className="ward-drawer"
      ref={panelRef}
      aria-label="Ward intelligence"
    >
      <button
        className="drawer-close"
        onClick={onClose}
        aria-label="Close ward intelligence"
      >
        <X size={18} />
      </button>
      <p>SELECTED WARD</p>
      <h2>{ward.name}</h2>
      <span
        className="drawer-risk"
        style={{ background: riskColors[ward.riskLevel] }}
      >
        {ward.riskLevel} RISK
      </span>
      <div className="drawer-score">
        <b>{ward.riskScore}</b>
        <span>
          health risk
          <br />
          score / 100
        </span>
      </div>
      <div className="drawer-metrics">
        {metrics.map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <b>{value}</b>
          </div>
        ))}
      </div>
      <section>
        <h3>Primary risk drivers</h3>
        <ul>
          <li>Built-up density {ward.builtUp}%</li>
          <li>Vegetation cover {ward.vegetation}%</li>
          <li>Vulnerability score {ward.vulnerability}/100</li>
        </ul>
      </section>
      <button className="drawer-action">
        Open full intelligence <ArrowUpRight size={15} />
      </button>
    </aside>
  );
}
