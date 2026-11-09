/** @type {import('next').NextConfig} */
const backendUrl = process.env.INTERNAL_BACKEND_URL || 'http://localhost:8000';

const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
