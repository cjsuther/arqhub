/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      colors: {
        // ArchiMate layer palette, tuned to the design system (SPEC §8.2).
        layer: {
          business: "#f5c542",
          application: "#4f9dde",
          technology: "#5cb85c",
          motivation: "#9b7ede",
        },
      },
      transitionDuration: { DEFAULT: "150ms" },
    },
  },
  plugins: [],
};
