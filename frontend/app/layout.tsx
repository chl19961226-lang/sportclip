import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SportClip · 多合一运动视频剪辑",
  description: "一键识别运动种类、检出高光时刻、自动生成分享文案",
};

export const viewport = {
  themeColor: "#000000",
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
