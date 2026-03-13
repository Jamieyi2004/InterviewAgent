import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#ECFDF5",
          100: "#D1FAE5",
          200: "#A7F3D0",
          300: "#6EE7B7",
          400: "#34D399",
          500: "#10B981",
          600: "#059669",
          700: "#005A4E",   // 华师主色 —— 深森绿
          800: "#004A40",
          900: "#003B33",
        },
        surface: {
          sidebar: "#F7F8FA",
          main: "#FFFFFF",
          hover: "#F0F1F3",
          card: "#F9FAFB",
          elevated: "#FFFFFF",
        },
        ink: {
          primary: "#1F2329",
          secondary: "#646A73",
          tertiary: "#8F959E",
          disabled: "#C0C4CC",
          inverse: "#FFFFFF",
        },
      },
      borderRadius: {
        "3xl": "24px",
        "4xl": "32px",
      },
      boxShadow: {
        "float": "0 8px 32px rgba(0, 0, 0, 0.08)",
        "float-lg": "0 12px 48px rgba(0, 0, 0, 0.12)",
        "card": "0 1px 4px rgba(0, 0, 0, 0.04)",
        "card-hover": "0 4px 16px rgba(0, 0, 0, 0.08)",
        "input": "0 4px 24px rgba(0, 0, 0, 0.06)",
      },
      animation: {
        "pulse-dot": "pulse-dot 1.4s infinite ease-in-out",
        "fade-in": "fade-in 0.3s ease-out",
        "slide-up": "slide-up 0.3s ease-out",
        "float": "float 3s ease-in-out infinite",
      },
      keyframes: {
        "pulse-dot": {
          "0%, 80%, 100%": { transform: "scale(0)" },
          "40%": { transform: "scale(1)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "float": {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
