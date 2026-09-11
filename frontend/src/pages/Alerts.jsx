import { useEffect, useRef, useState } from "react";
import "./OperationsPages.css";
import { gsap } from "gsap";
import { Check, Send, ArrowUpRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { initialAlerts } from "../data/alerts.js";
export default function Alerts() {
  const [alerts, setAlerts] = useState(
    initialAlerts.map((a) => ({
      ...a,
      acknowledged: false,
      dispatched: false,
    })),
  );
  const [filter, setFilter] = useState("All");
  const ref = useRef();
  const nav = useNavigate();
  useEffect(() => {
    const ctx = gsap.context(
      () =>
        gsap.from(".alert-card", {
          y: 16,
          opacity: 0,
          stagger: 0.08,
          duration: 0.45,
        }),
      ref,
    );
    return () => ctx.revert();
  }, []);
  const visible = alerts.filter((a) =>
    filter === "All" || filter === "Acknowledged"
      ? filter === "Acknowledged"
        ? a.acknowledged
        : true
      : a.severity === filter,
  );
  const update = (id, key) =>
    setAlerts((items) =>
      items.map((a) => (a.id === id ? { ...a, [key]: true } : a)),
    );
  return (
    <div className="page alerts-page" ref={ref}>
      <div className="alert-toolbar">
        <div>
          <p>RESPONSE QUEUE</p>
          <h2>Actionable heat alerts</h2>
        </div>
        <div className="filter-row">
          {["All", "Extreme", "High", "Moderate", "Acknowledged"].map(
            (item) => (
              <button
                onClick={() => setFilter(item)}
                className={filter === item ? "filter-active" : ""}
                key={item}
              >
                {item}
              </button>
            ),
          )}
        </div>
      </div>
      <div className="alert-grid">
        {visible.map((alert) => (
          <article
            className={`alert-card ${alert.severity.toLowerCase()}`}
            key={alert.id}
          >
            <div className="alert-title">
              <span>{alert.severity} HEAT</span>
              {alert.acknowledged && <small>ACKNOWLEDGED</small>}
              <h3>Ward {alert.ward}</h3>
              <p>{alert.title}</p>
            </div>
            <div>
              <b>Risk signals</b>
              <ul>
                {alert.reasons.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </div>
            <div>
              <b>Recommended actions</b>
              <ul>
                {alert.actions.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </div>
            <footer>
              <button
                className={alert.acknowledged ? "done" : ""}
                onClick={() => update(alert.id, "acknowledged")}
              >
                <Check size={15} />
                {alert.acknowledged ? "Acknowledged" : "Acknowledge"}
              </button>
              <button
                className={alert.dispatched ? "done" : ""}
                onClick={() => update(alert.id, "dispatched")}
              >
                <Send size={14} />
                {alert.dispatched ? "Dispatched" : "Dispatch"}
              </button>
              <button
                onClick={() => nav(`/ward-intelligence?ward=${alert.ward}`)}
              >
                <ArrowUpRight size={15} />
                View ward
              </button>
            </footer>
          </article>
        ))}
        {visible.length === 0 && (
          <div className="empty-state">No alerts match this filter.</div>
        )}
      </div>
    </div>
  );
}
