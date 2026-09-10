const alerts = [
  {
    severity: "HIGH",
    place: "Kolkata, West Bengal",
    message: "Heat index expected to exceed 45°C this afternoon.",
  },
  {
    severity: "HIGH",
    place: "Patna, Bihar",
    message: "Severe heatwave conditions likely for the next 48 hours.",
  },
  {
    severity: "MODERATE",
    place: "Bhubaneswar, Odisha",
    message: "Stay hydrated and avoid prolonged outdoor exposure.",
  },
];
export default function AlertCard() {
  return (
    <section className="card alert-card">
      <div className="card-heading">
        <div>
          <p className="card-kicker">ACTIVE ALERTS</p>
          <h2>Heatwave advisories</h2>
        </div>
        <span className="alert-count">3 active</span>
      </div>
      <div className="alerts-list">
        {alerts.map((alert) => (
          <article className="alert-item" key={alert.place}>
            <span
              className={`severity severity-${alert.severity.toLowerCase()}`}
            >
              {alert.severity}
            </span>
            <div>
              <h3>{alert.place}</h3>
              <p>{alert.message}</p>
            </div>
          </article>
        ))}
      </div>
      <a className="text-link" href="#alerts">
        View all alerts <span>→</span>
      </a>
    </section>
  );
}
