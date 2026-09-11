import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { forecast } from "../../data/forecast.js";
import { riskColors } from "../../data/wards.js";
export default function Forecast({ selectedDay, onSelect }) {
  const ref = useRef();
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const active = ref.current?.querySelector(".day-active");
    if (active)
      gsap.fromTo(
        active,
        { y: 5, opacity: 0.5 },
        { y: 0, opacity: 1, duration: 0.3, ease: "power2.out" },
      );
  }, [selectedDay]);
  return (
    <section className="forecast-timeline" ref={ref}>
      <div className="timeline-title">
        <span>5-DAY OUTLOOK</span>
        <b>Thermal risk trajectory</b>
      </div>
      <div className="timeline-days">
        {forecast.map((day) => (
          <button
            onClick={() => onSelect(day.id)}
            className={selectedDay === day.id ? "day-active" : ""}
            key={day.id}
          >
            <span>{day.label}</span>
            <strong>{day.temp}&deg;</strong>
            <small>
              WBGT {day.wbgt}&deg; · UTCI {day.utci}&deg;
            </small>
            <i style={{ background: riskColors[day.risk] }}>
              {day.risk}
              {day.peak ? " · PEAK" : ""}
            </i>
          </button>
        ))}
      </div>
    </section>
  );
}
