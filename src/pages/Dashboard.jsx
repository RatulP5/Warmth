import { useEffect, useRef, useState } from "react";
import "./Dashboard.css";
import { gsap } from "gsap";
import { wards } from "../data/wards.js";
import RiskSummary from "../components/dashboard/RiskSummary.jsx";
import Forecast from "../components/dashboard/Forecast.jsx";
import RiskDrivers from "../components/dashboard/RiskDrivers.jsx";
import ActionRecommendations from "../components/dashboard/ActionRecommendations.jsx";
import HeatMap, {
  MapLayerSelector,
  MapLegend,
} from "../components/map/HeatMap.jsx";
import WardPanel from "../components/ward/WardPanel.jsx";
export default function Dashboard() {
  const [ward, setWard] = useState(null);
  const [layer, setLayer] = useState("riskScore");
  const [day, setDay] = useState(0);
  const pageRef = useRef();
  const firstLayer = useRef(true);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const ctx = gsap.context(
      () =>
        gsap.fromTo(
          [".map-command-title", ".map-frame"],
          { opacity: 0, y: 18 },
          {
            opacity: 1,
            y: 0,
            stagger: 0.1,
            duration: 0.65,
            ease: "power3.out",
          },
        ),
      pageRef,
    );
    return () => ctx.revert();
  }, []);
  useEffect(() => {
    if (firstLayer.current) {
      firstLayer.current = false;
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    gsap.fromTo(
      ".leaflet-overlay-pane",
      { opacity: 0.35 },
      { opacity: 1, duration: 0.28, ease: "power1.out" },
    );
  }, [layer]);
  return (
    <div className="climate-page" ref={pageRef}>
      <section className="map-command">
        <div className="map-command-title">
          <div>
            <span>LIVE CITY HEAT RISK</span>
            <h1>See heat before it becomes harm.</h1>
          </div>
          <p>Kolkata · 141 wards · Forecast day {day + 1}</p>
        </div>
        <div className="map-frame">
          <HeatMap
            wards={wards}
            layer={layer}
            selectedWard={ward}
            onWardSelect={setWard}
            day={day}
          />
          <div className="map-overlay overlay-top">
            <MapLayerSelector layer={layer} onChange={setLayer} />
          </div>
          <div className="map-overlay overlay-bottom">
            <MapLegend layer={layer} />
            <RiskSummary />
          </div>
          <div className="map-instruction">
            Select a ward for operational intelligence
          </div>
          <WardPanel ward={ward} onClose={() => setWard(null)} />
        </div>
      </section>
      <Forecast selectedDay={day} onSelect={setDay} />
      <section className="lower-intelligence">
        <RiskDrivers ward={ward || wards[36]} />
        <ActionRecommendations risk={(ward || wards[36]).riskLevel} />
      </section>
    </div>
  );
}
