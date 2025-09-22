declare const process: any;
const pendelOrigin = process.env?.PENDEL_ORIGIN as string | undefined;

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    if (!pendelOrigin) {
      return [];
    }
    return [
      {
        source: "/pendel",
        destination: `${pendelOrigin}/pendel`,
      },
      {
        source: "/pendel/:path*",
        destination: `${pendelOrigin}/pendel/:path*`,
      },
    ];
  },
};

export default nextConfig;
