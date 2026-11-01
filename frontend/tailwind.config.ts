import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        cream: {
          50: "#FBF8F2",
          100: "#FAF6EE",
          200: "#F1EADF",
          300: "#E3D8C8",
        },
        ink: {
          900: "#1E1B18",
          700: "#3D3833",
          500: "#6B655E",
          400: "#8A8580",
        },
        ember: {
          400: "#E08A6C",
          500: "#D97757",
          600: "#C4623F",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: {
        card: "18px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(30, 27, 24, 0.04), 0 12px 32px -20px rgba(30, 27, 24, 0.25)",
      },
    },
  },
  plugins: [],
} satisfies Config;
