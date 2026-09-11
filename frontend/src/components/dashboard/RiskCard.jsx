export default function RiskCard() {
  return (
    <section className="card risk-card">
      <div className="card-heading">
        <div>
          <p className="card-kicker">HEAT RISK</p>
          <h2>Current risk level</h2>
        </div>
        <span className="risk-badge">HIGH</span>
      </div>
      <div className="risk-body">
        <div className="risk-score">
          <strong>78</strong>
          <span>/100</span>
        </div>
        <div className="risk-meter" aria-label="Risk score 78 out of 100">
          <span />
        </div>
      </div>
      <p className="card-description">
        High temperatures and humidity may cause heat stress. Limit outdoor
        activity between 11 AM and 4 PM.
      </p>
    </section>
  );
}
