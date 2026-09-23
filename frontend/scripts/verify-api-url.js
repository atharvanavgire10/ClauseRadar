/**
 * Production build guard: VITE_API_URL is baked into the bundle at build
 * time, so a production bundle must point at the real API — never localhost.
 *
 * Usage:
 *   VITE_API_URL=https://api.example.com npm run build:prod  (absolute API)
 *   VITE_API_URL=same-origin npm run build:prod               (same-origin /api/...)
 * Fails when VITE_API_URL is unset, when dist/ is missing, when the bundle
 * still references localhost:8000, or (absolute mode) when it lacks the
 * configured origin. "same-origin" is for deployments serving the API from
 * the same origin (e.g. Vercel rewrites); unset keeps the local-dev default.
 */
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const dist = join(root, 'dist');
const raw = process.env.VITE_API_URL;
const apiUrl = (raw ?? '').replace(/\/$/, '');
const sameOrigin = raw === 'same-origin';

if (raw === undefined || raw === '') {
  console.error('VITE_API_URL is not set. Production builds require it: an absolute origin (VITE_API_URL=https://api.example.com) or the literal "same-origin" (VITE_API_URL=same-origin).');
  process.exit(1);
}
if (process.argv.includes('--env-only')) {
  console.log(`OK: VITE_API_URL=${sameOrigin ? '(same-origin)' : apiUrl}`);
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
if (!sameOrigin && !bundle.includes(apiUrl)) {
  console.error(`REJECTED: production bundle does not contain the configured API origin ${apiUrl}`);
  failed = true;
}
if (failed) process.exit(1);
console.log(`OK: production bundle targets ${sameOrigin ? 'same-origin /api/...' : apiUrl} with no localhost fallback.`);
