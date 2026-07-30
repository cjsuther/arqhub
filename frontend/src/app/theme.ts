import { create } from "zustand";

type Theme = "light" | "dark";

interface ThemeState {
  theme: Theme;
  toggle: () => void;
}

function apply(theme: Theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

const initial: Theme =
  (localStorage.getItem("arqhub-theme") as Theme | null) ??
  (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
apply(initial);

export const useTheme = create<ThemeState>((set, get) => ({
  theme: initial,
  toggle: () => {
    const next: Theme = get().theme === "dark" ? "light" : "dark";
    localStorage.setItem("arqhub-theme", next);
    apply(next);
    set({ theme: next });
  },
}));
