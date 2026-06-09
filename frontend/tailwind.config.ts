import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#18202a",
        panel: "#ffffff",
        line: "#d8e0e8",
        teal: "#0f766e",
        amber: "#b7791f",
        danger: "#b42318"
      },
      boxShadow: {
        soft: "0 12px 35px rgba(21, 31, 44, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;

