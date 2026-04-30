/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    // 允许 Server Action / 大文件上传（默认 1MB 太小）
    serverActions: { bodySizeLimit: "1024mb" },
  },
};
export default nextConfig;
