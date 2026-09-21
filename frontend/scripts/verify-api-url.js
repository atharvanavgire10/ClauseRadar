/**
 * Production build guard: VITE_API_URL is baked into the bundle at build
 * time, so a production bundle must point at the real API — never localhost.
 *
 * Usage: VITE_API_URL=https://api.example.com npm run build:prod
 * Fails when VITE_API_URL is unset, when dist/ is missing, when the bundle
 * still references localhost:8000, or when it lacks the configured origin.
 */
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const dist = join(root, 'dist');
const apiUrl = (process.env.VITE_API_URL ?? '').replace(/\/$/, '');

if (!apiUrl) {
  console.error('VITE_API_URL is not set. Production builds require it, e.g. VITE_API_URL=https://api.example.com npm run build:prod');
  process.exit(1);
}
if (process.argv.includes('--env-only')) {
  console.log(`OK: VITE_API_URL=${apiUrl}`);
  process.exit(0);
}
if (!existsSync(dist)) {
  console.error('dist/ not found — run vite build first.');
  process.exit(1);
}

const assets = join(dist, 'assets');
const files = existsSync(assets) ? readdirSync(assets).filter((f) => f.endsWith('.js')) : [];
const bundle = files.map((f) => readFileSync(join(assets, f), 'utf8')).join('\n');

let failed = false;
if (bundle.includes('localhost:8000')) {
  console.error('REJECTED: production bundle still references localhost:8000');
  failed = true;
}
if (!bundle.includes(apiUrl)) {
  console.error(`REJECTED: production bundle does not contain the configured API origin ${apiUrl}`);
  failed = true;
}
if (failed) process.exit(1);
console.log(`OK: production bundle targets ${apiUrl} with no localhost fallback.`);
