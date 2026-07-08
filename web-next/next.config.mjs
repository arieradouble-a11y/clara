/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone", // minimal, self-contained server output for Docker
};

export default nextConfig;
