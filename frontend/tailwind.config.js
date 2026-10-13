/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        border: "var(--border)",
        "border-strong": "var(--border-strong)",
        text: "var(--text)",
        "text-muted": "var(--text-muted)",
        accent: "var(--accent)",
        "accent-soft": "var(--accent-soft)",
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
        idle: "var(--idle)",
      },
      fontFamily: {
        sans: ['"Inter Variable"', "Inter", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono: ['"JetBrains Mono Variable"', "JetBrains Mono", "monospace"],
      },
      borderRadius: {
        DEFAULT: "6px",
        card: "8px",
        input: "6px",
        chip: "9999px",
      },
      boxShadow: {
        modal: "var(--shadow-modal)",
      },
    },
  },
  plugins: [],
};
