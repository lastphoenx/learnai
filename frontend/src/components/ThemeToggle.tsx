"use client";

import { useTheme } from "./ThemeProvider";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();

  return (
    <button type="button" onClick={toggle} aria-label="Theme wechseln">
      {theme === "light" ? "Dunkel" : "Hell"}
    </button>
  );
}
