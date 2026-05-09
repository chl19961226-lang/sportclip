import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // iOS 系统色 (Dark)
        ink: "#000000",
        ink2: "#0b0b0f",
        // 卡片底（苹果"卡片"通常是 systemGray6 系列）
        card: "rgba(28,28,30,0.72)",
        cardSolid: "#1c1c1e",
        line: "rgba(255,255,255,0.08)",
        line2: "rgba(255,255,255,0.14)",
        // iOS 强调色
        accent: "#0a84ff",       // System Blue
        accentInk: "#ffffff",
        indigo: "#5e5ce6",       // System Indigo
        pink: "#ff375f",         // System Pink
        teal: "#64d2ff",         // System Teal
        green: "#30d158",        // System Green
        orange: "#ff9f0a",       // System Orange
        // 文本
        primary: "#f5f5f7",
        secondary: "rgba(235,235,245,0.72)",
        tertiary: "rgba(235,235,245,0.42)",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"SF Pro Display"',
          '"SF Pro Text"',
          "Inter",
          '"Helvetica Neue"',
          "Helvetica",
          '"PingFang SC"',
          '"Hiragino Sans GB"',
          '"Microsoft YaHei"',
          "sans-serif",
        ],
        display: [
          '"SF Pro Display"',
          "-apple-system",
          "BlinkMacSystemFont",
          "Inter",
          "sans-serif",
        ],
      },
      borderRadius: {
        // iOS HIG 常用圆角
        ios: "14px",
        iosLg: "22px",
        iosXl: "28px",
      },
      boxShadow: {
        // 苹果"软"阴影
        soft: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 12px 40px -12px rgba(0,0,0,0.6)",
        glow: "0 0 0 1px rgba(255,255,255,0.06) inset, 0 18px 60px -10px rgba(10,132,255,0.45)",
        pop: "0 8px 24px -8px rgba(0,0,0,0.6)",
      },
      backgroundImage: {
        "ios-grad-1":
          "radial-gradient(60% 50% at 20% 0%, rgba(94,92,230,0.35) 0%, rgba(0,0,0,0) 60%), radial-gradient(50% 40% at 90% 10%, rgba(255,55,95,0.28) 0%, rgba(0,0,0,0) 60%), radial-gradient(60% 60% at 50% 110%, rgba(10,132,255,0.30) 0%, rgba(0,0,0,0) 60%)",
        "btn-primary":
          "linear-gradient(180deg, #2596ff 0%, #0a84ff 50%, #0067db 100%)",
        "shimmer":
          "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.18) 50%, rgba(255,255,255,0) 100%)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        floatY: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        shimmer: "shimmer 2.2s linear infinite",
        floatY: "floatY 4.5s ease-in-out infinite",
      },
      backdropBlur: {
        ios: "24px",
      },
    },
  },
  plugins: [],
};
export default config;
