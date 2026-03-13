/** @type {import('next').NextConfig} */
const nextConfig = {
  // 允许后端 API 代理（开发时可选）
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
