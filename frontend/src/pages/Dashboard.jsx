import { useEffect, useRef, useState } from "react";
import "./Dashboard.css";
import { gsap } from "gsap";

import { wards } from "../data/wards.js";

import RiskSummary from "../components/dashboard/RiskSummary.jsx";
import Forecast from "../components/dashboard/Forecast.jsx";
import DashboardHeading from "../components/dashboard/DashboardHeading.jsx";

import HeatMap, {
  MapLayerSelector,
  MapLegend,
} from "../components/map/HeatMap.jsx";

import WardPanel from "../components/ward/WardPanel.jsx";

export default function Dashboard() {
  const [ward, setWard] = useState(null);
  const [layer, setLayer] = useState("riskScore");
  const [day, setDay] = useState(0);

  const pageRef = useRef(null);
  const firstLayer = useRef(true);

  // Dashboard entrance animation
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    const ctx = gsap.context(() => {
      gsap.fromTo(
        [".map-frame", ".forecast-timeline", ".lower-intelligence"],
        {
          opacity: 0,
          y: 30,
          filter: "blur(10px)",
        },
        {
          opacity: 1,
          y: 0,
          filter: "blur(0px)",
          stagger: 0.12,
          duration: 0.9,
          ease: "power4.out",
        }
      );
    }, pageRef);

    return () => {
      ctx.revert();
    };
  }, []);

  // Animate map when changing layers
  useEffect(() => {
    if (firstLayer.current) {
      firstLayer.current = false;
      return;
    }

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    gsap.fromTo(
      ".leaflet-overlay-pane",
      {
        opacity: 0.35,
      },
      {
        opacity: 1,
        duration: 0.28,
        ease: "power1.out",
      }
    );
  }, [layer]);

  return (
    <div className="climate-page" ref={pageRef}>
      {/* =====================================================
          HERO / COMMAND CENTRE HEADER
          ===================================================== */}
      <section className="map-command">
        <DashboardHeading />

        {/* =================================================
            HEAT MAP
            ================================================= */}
        <div className="map-frame">
          <HeatMap
            wards={wards}
            layer={layer}
            selectedWard={ward}
            onWardSelect={setWard}
            day={day}
          />

          {/* Map layer selector */}
          <div className="map-overlay overlay-top">
            <MapLayerSelector
              layer={layer}
              onChange={setLayer}
            />
          </div>

          {/* Map legend + summary */}
          <div className="map-overlay overlay-bottom">
            <MapLegend layer={layer} />
            <RiskSummary />
          </div>

          {/* Map instruction */}
          <div className="map-instruction">
            Select a ward for operational intelligence
          </div>

          {/* Ward intelligence panel */}
          <WardPanel
            ward={ward}
            onClose={() => setWard(null)}
          />
        </div>
      </section>

      {/* =====================================================
          5-DAY FORECAST
          ===================================================== */}
      <Forecast
        selectedDay={day}
        onSelect={setDay}
      />

      
    </div>
  );
}