import type {NextConfig} from 'next';
import path from 'node:path';

// Keep browser API requests on the web origin, even on alternate dev ports.
const upstream = (process.env.PAKDATA_API_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');
const config: NextConfig = {
  output: 'standalone',
  // Isolate production checks from an active development server.
  distDir: process.env.PAKDATA_NEXT_DIST_DIR ?? '.next',
  outputFileTracingRoot: path.resolve(process.cwd()),
  async rewrites() {
    return [{source: '/backend/:path*', destination: `${upstream}/:path*`}];
  },
};
export default config;
