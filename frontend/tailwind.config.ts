import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef7f2",
          100: "#d7eee1",
          500: "#1f7a4d",
          600: "#17613d",
          700: "#114b2f",
        },
      },
    },
  },
  plugins: [],
};

export default config;
