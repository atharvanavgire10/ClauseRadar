/**
 * Copy the Vite production build into the Django template/static tree so the
 * native Django deployment (Vercel) serves the React SPA itself:
 *   frontend/dist/index.html -> backend/templates/index.html
 *   frontend/dist/assets/    -> backend/static/assets/
 *
 * Runs in the Vercel buildCommand AFTER `vite build` and BEFORE Django's
 * collectstatic step, so WhiteNoise picks the assets up with hashed names.
 * Usage: node scripts/sync-spa.js [--templates-dir=...] [--static-dir=...]
 * (overrides exist so tests can mirror the layout into temp dirs).
 */
import { cpSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const args = Object.fromEntries(
  process.argv.slice(2).map((a) => {
    const [k, v] = a.replace(/^--/, '').split('=');
    return [k, v ?? ''];
  }),
);

const dist = args['dist-dir'] || join(root, 'frontend', 'dist');
const templatesDir = args['templates-dir'] || join(root, 'backend', 'templates');
const staticDir = args['static-dir'] || join(root, 'backend', 'static');

if (!existsSync(join(dist, 'index.html'))) {
  console.error(`sync-spa: ${dist}/index.html not found — run vite build first.`);
  process.exit(1);
}
if (!existsSync(join(dist, 'assets'))) {
  console.error(`sync-spa: ${dist}/assets not found — run vite build first.`);
  process.exit(1);
}

mkdirSync(templatesDir, { recursive: true });
mkdirSync(staticDir, { recursive: true });

const html = readFileSync(join(dist, 'index.html'), 'utf8');
writeFileSync(join(templatesDir, 'index.html'), html);

const assetsDest = join(staticDir, 'assets');
rmSync(assetsDest, { recursive: true, force: true });
cpSync(join(dist, 'assets'), assetsDest, { recursive: true });

console.log(`sync-spa: index.html -> ${templatesDir}, assets/ -> ${assetsDest}`);
