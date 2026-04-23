/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverComponentsExternalPackages: ["mongoose"],
  },
  api: {
    bodyParser: false, // needed for file upload route
  },
};

module.exports = nextConfig;
