import { ChevronDown, MapPin } from "lucide-react";
import { useState, useEffect } from "react";

export default function Header() {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date());
    }, 1000);

    // Stop the timer when component is removed
    return () => clearInterval(timer);
  }, []);

  const formattedDate = time
    .toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "numeric",
      year: "numeric",
      timeZone: "Asia/Kolkata",
    })
    .toUpperCase();

  const formattedTime = time.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone: "Asia/Kolkata",
  });
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
        <time>{formattedDate}</time>
        <time>{formattedTime} IST</time>
      </div>
    </header>
  );
}
