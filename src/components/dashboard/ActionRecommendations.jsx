import { CheckCircle2 } from "lucide-react";
const actions = {
  Extreme: [
    "Activate cooling centres by 10 AM",
    "Increase water availability at transit points",
    "Shift outdoor work hours and notify employers",
    "Pre-position healthcare response teams",
  ],
  High: [
    "Issue public advisories",
    "Monitor vulnerable wards",
    "Increase hydration points",
  ],
  Moderate: ["Maintain public advisories", "Review ward readiness"],
};
export default function ActionRecommendations({ risk }) {
  return (
    <section className="section-card action-card">
      <div className="section-heading">
        <div>
          <p>RESPONSE PLAYBOOK</p>
          <h2>What should we do?</h2>
        </div>
        <span className={`tag ${risk.toLowerCase()}`}>{risk}</span>
      </div>
      <p>Recommended municipal actions for the current threat level.</p>
      <ul>
        {(actions[risk] || actions.Moderate).map((action) => (
          <li key={action}>
            <CheckCircle2 size={16} />
            {action}
          </li>
        ))}
      </ul>
      <button className="secondary-btn">Open response checklist</button>
    </section>
  );
}
