import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // iOS 浅色模式：纸感底 + 高对比文字
        ink: "#ffffff",
        ink2: "#f5f5f7",          // Apple system gray 6 light
        // 卡片底（白 + 极淡叠层）
        card: "rgba(255,255,255,0.78)",
        cardSolid: "#ffffff",
        line: "rgba(0,0,0,0.08)",
        line2: "rgba(0,0,0,0.14)",
        // iOS 强调色（浅色模式下略加深以提升对比）
        accent: "#0071e3",        // Apple.com 主蓝
        accentInk: "#ffffff",
        indigo: "#5856d6",        // System Indigo (light)
        pink: "#ff2d55",          // System Pink (light)
        teal: "#5ac8fa",          // System Teal (light)
        green: "#28cd41",         // System Green (light)
        orange: "#ff9500",        // System Orange (light)
        // 文本（按 apple.com 用色）
        primary: "#1d1d1f",
        secondary: "rgba(29,29,31,0.72)",
        tertiary: "rgba(29,29,31,0.45)",
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
        // 苹果浅色"软"阴影：极轻的灰投影
        soft: "0 1px 0 0 rgba(255,255,255,0.6) inset, 0 1px 2px 0 rgba(0,0,0,0.04), 0 12px 32px -16px rgba(0,0,0,0.18)",
        glow: "0 0 0 1px rgba(0,113,227,0.18) inset, 0 18px 48px -16px rgba(0,113,227,0.32)",
        pop: "0 8px 24px -10px rgba(0,0,0,0.18)",
      },
      backgroundImage: {
        // 浅色"光晕"——低饱和淡色 wash
        "ios-grad-1":
          "radial-gradient(60% 50% at 20% 0%, rgba(88,86,214,0.16) 0%, rgba(255,255,255,0) 60%), radial-gradient(50% 40% at 90% 10%, rgba(255,45,85,0.12) 0%, rgba(255,255,255,0) 60%), radial-gradient(60% 60% at 50% 110%, rgba(0,113,227,0.14) 0%, rgba(255,255,255,0) 60%)",
        "btn-primary":
          "linear-gradient(180deg, #2b8bff 0%, #0071e3 55%, #0058b8 100%)",
        "shimmer":
          "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.55) 50%, rgba(255,255,255,0) 100%)",
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
