import { Bell, ChevronDown, MapPin, UserCircle } from "lucide-react";
export default function Header() {
  return (
    <header className="command-bar">
      <div className="command-context">
        <span>HEAT INTELLIGENCE</span>
        <b>Kolkata Municipal Corporation</b>
      </div>
      <div className="command-tools">
        <button>
          <MapPin size={14} /> Kolkata <ChevronDown size={13} />
        </button>
        <time>20 MAY 2025 · 14:32 IST</time>
        <span className="live-state">
          <i /> LIVE
        </span>
        <button className="notification" aria-label="Three active alerts">
          <Bell size={17} />
          <em>3</em>
        </button>
        <UserCircle size={23} />
      </div>
    </header>
  );
}
