const stats = [
  ["Extreme", 8],
  ["High", 21],
  ["Moderate", 34],
  ["Low", 78],
];
export default function RiskSummary() {
  return (
    <div className="risk-summary" aria-label="Ward risk summary">
      {stats.map(([risk, count]) => (
        <div className={risk.toLowerCase()} key={risk}>
          <b>{count}</b>
          <span>{risk}</span>
        </div>
      ))}
    </div>
  );
}
