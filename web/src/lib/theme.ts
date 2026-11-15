/** Appearance: "system" follows the device; "light" / "dark" are pinned on <html data-theme> and remembered per device. */
export type ThemeChoice = "system" | "light" | "dark";
export const THEME_KEY = "finn.theme";
export const THEME_EVENT = "finn-theme";

export function readTheme(): ThemeChoice {
  try {
    const v = localStorage.getItem(THEME_KEY);
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}

export function effectiveTheme(choice: ThemeChoice): "light" | "dark" {
  if (choice !== "system") return choice;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function applyTheme(choice: ThemeChoice): void {
  try {
    if (choice === "system") localStorage.removeItem(THEME_KEY);
    else localStorage.setItem(THEME_KEY, choice);
  } catch {}
  const root = document.documentElement;
  if (choice === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", choice);
  const meta = document.querySelector('meta[name="theme-color"]:not([media])') ?? Object.assign(document.createElement("meta"), { name: "theme-color" });
  meta.setAttribute("content", effectiveTheme(choice) === "dark" ? "#0B1020" : "#FAF6EF");
  if (!meta.parentNode) document.head.appendChild(meta);
  window.dispatchEvent(new Event(THEME_EVENT));
}

/** Inline in <head>: pins the saved theme before first paint, so there is no flash of the wrong one. */
export const themeBootScript = `try{var t=localStorage.getItem("${THEME_KEY}");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}`;
