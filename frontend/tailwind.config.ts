import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#121826",
        canvas: "#F7F9FC",
        panel: "#FFFFFF",
        line: "#E6EAF0",
        brand: "#2563EB",
        brandDark: "#1D4ED8",
        brandSoft: "#EAF2FF",
        blue: "#2563EB",
        violet: "#3B82F6",
        cyan: "#22C7D6",
        success: "#34C38F",
        warning: "#F4B740",
        danger: "#E45B69",
      },
      boxShadow: {
        glow: "0 20px 60px rgba(37, 99, 235, 0.14)",
        soft: "0 18px 50px rgba(18, 24, 38, 0.065)",
      },
    },
  },
  plugins: [],
};

export default config;
