import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { PREVIEW_PAGES } from '../src/preview/catalog.js';
const root = new URL('../dist/', import.meta.url);
const html = await readFile(new URL('index.html', root), 'utf8');
const paths = new Set(['/preview', ...PREVIEW_PAGES.flatMap(page => [`/preview/${page.id}`, page.path.split('?')[0]])]);
for (const path of paths) {
  if (path === '/') continue;
  const directory = new URL(`${path.slice(1)}/`, root);
  await mkdir(directory, { recursive:true });
  await writeFile(new URL('index.html', directory), html);
}
console.log(`Created static entry points for ${paths.size} preview routes.`);
