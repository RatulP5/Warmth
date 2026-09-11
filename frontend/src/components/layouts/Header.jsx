import { ChevronDown, MapPin, Moon, Sun } from "lucide-react";
import { useState, useEffect } from "react";
import { useTheme } from "../../context/ThemeContext.jsx";

export default function Header() {
  const [time, setTime] = useState(new Date());
  const { theme, toggleTheme } = useTheme();

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
        <button className="theme-toggle" onClick={toggleTheme} aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"} title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}>
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>
        <button>
          <MapPin size={14} /> Kolkata <ChevronDown size={13} />
        </button>
        <time>{formattedDate}</time>
        <time>{formattedTime} IST</time>
      </div>
    </header>
  );
}
