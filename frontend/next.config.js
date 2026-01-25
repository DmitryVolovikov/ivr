/** @type {import('next').NextConfig} */
// Default at build time since rewrites are evaluated then.
const apiProxyTarget = process.env.API_PROXY_TARGET || "http://backend:8000";

const nextConfig = {
  experimental: {
    // Allow long-running /rag/ask requests through the proxy.
    proxyTimeout: 600000,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiProxyTarget}/:path*`,
      },
      {
        source: "/rag/:path*",
        destination: `${apiProxyTarget}/rag/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
