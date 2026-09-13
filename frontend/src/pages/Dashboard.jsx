import { useEffect, useRef, useState } from "react";
import "./Dashboard.css";
import { gsap } from "gsap";

import {getDashboardWards} from "../services/dashboardWardService.js";

import RiskSummary from "../components/dashboard/RiskSummary.jsx";
import Forecast from "../components/dashboard/Forecast.jsx";
import DashboardHeading from "../components/dashboard/DashboardHeading.jsx";
import {getWardEnvironmentalFeatures} from "../services/weatherService.js";

import HeatMap, {
  MapLayerSelector,
  MapLegend,
} from "../components/map/HeatMap.jsx";

import WardPanel from "../components/ward/WardPanel.jsx";

export default function Dashboard() {
  console.log("Hello");
  const [wards, setWards] = useState([]);
  const [ward, setWard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [layer, setLayer] = useState("riskScore");
  const [day, setDay] = useState(0);
  const [wardWeather,setWardWeather]=useState(null);
  const [weatherLoading,setWeatherLoading]=useState(false);

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

    const target = document.querySelector(".leaflet-overlay-pane");

    if (!target) return;

    gsap.fromTo(
      target,
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

  //load the wards for the dashboard
  useEffect(() => {
    async function loadWards() {
      try {
        const data = await getDashboardWards();

        console.log("DASHBOARD WARDS FROM SUPABASE:", data);

        setWards(data);
      } catch (err) {
        console.error("Failed to load dashboard wards:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadWards();
  }, []);

  //Fetch weather whenever a ward is selected
  useEffect(()=>{
    if (!ward) {
      return;
    }

  async function loadWardWeather() {
    try {
      setWeatherLoading(true);

      const data = await getWardEnvironmentalFeatures(ward.id);

      console.log("SELECTED WARD WEATHER:", data);

      setWardWeather(data);
    } catch (error) {
      console.error("Failed to load ward weather:", error);
      setWardWeather(null);
    } finally {
      setWeatherLoading(false);
    }
  }

  loadWardWeather();
  },[ward]);

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

          {loading && <p>Loading ward intelligence...</p>}

          {error && <p>Failed to load wards: {error}</p>}

          {!loading && !error && wards.length > 0 && (
            <HeatMap
              wards={wards}
              layer={layer}
              selectedWard={ward}
              onWardSelect={setWard}
              day={day}
            />
          )}

          <div className="map-overlay overlay-top">
            <MapLayerSelector
              layer={layer}
              onChange={setLayer}
            />
          </div>

          <div className="map-overlay overlay-bottom">
            <MapLegend layer={layer} />
            <RiskSummary />
          </div>

          <div className="map-instruction">
            Select a ward for operational intelligence
          </div>

          <WardPanel
            ward={ward}
            weather={wardWeather}
            weatherLoading={weatherLoading}
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