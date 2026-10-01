import type {NextConfig} from 'next';
import path from 'node:path';
const config: NextConfig = {output:'standalone',outputFileTracingRoot:path.resolve(process.cwd())};
export default config;
