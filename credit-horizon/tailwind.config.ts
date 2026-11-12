import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          950: "#04261c",
          900: "#063b2b",
          800: "#0a4d38",
          700: "#0d6047",
          600: "#0f7a58",
          500: "#10b981",
          400: "#34d399",
          300: "#6ee7b7",
          100: "#d1fae5",
          50: "#ecfdf5",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(6,59,43,0.06), 0 4px 16px rgba(6,59,43,0.06)",
      },
    },
  },
  plugins: [],
} satisfies Config;
