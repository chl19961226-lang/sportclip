import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Crux · 高光剪辑师",
  description: "The crux of every move. 一键识别运动 · 检出高光 · 生成分享文案",
};

export const viewport = {
  themeColor: "#f5f5f7",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover" as const,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="font-sans antialiased text-primary">{children}</body>
    </html>
  );
}
