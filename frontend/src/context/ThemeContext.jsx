import { createContext, useContext, useEffect, useState } from "react";

const ThemeContext = createContext(null);
const THEME_KEY = "heatshield-theme";

function getInitialTheme() {
  try { return localStorage.getItem(THEME_KEY) === "light" ? "light" : "dark"; }
  catch { return "dark"; }
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(getInitialTheme);
  useEffect(() => {
    document.documentElement.classList.remove("light", "dark");
    document.documentElement.classList.add(theme);
    try { localStorage.setItem(THEME_KEY, theme); } catch { /* storage unavailable */ }
  }, [theme]);
  const toggleTheme = () => setTheme((current) => current === "dark" ? "light" : "dark");
  return <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>{children}</ThemeContext.Provider>;
}

// This hook intentionally shares the provider module's private context.
// eslint-disable-next-line react-refresh/only-export-components
export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme must be used within a ThemeProvider");
  return context;
}
