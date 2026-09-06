import { readFile, readdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = path.join(root, '_site');
const names = ['index.html', 'packages.html', 'services.html', 'header.html', 'footer.html'];
const documents = Object.fromEntries(await Promise.all(names.map(async name => [name, await readFile(path.join(output, name), 'utf8')])));
const ids = Object.fromEntries(Object.entries(documents).map(([name, html]) => [name, new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]))]));
for (const [name, html] of Object.entries(documents)) {
    assert(!/fetch\s*\(|\/api\//.test(html), `${name}: unexpected server dependency`);
    const allIds = [...html.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);
    assert.equal(new Set(allIds).size, allIds.length, `${name}: duplicate id`);
    for (const script of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) new vm.Script(script[1], { filename: name });
    for (const match of html.matchAll(/\b(?:href|src)="([^"]+)"/g)) {
        const value = match[1];
        if (/^(?:https?:|mailto:|tel:|data:|\/\/)/.test(value)) continue;
        const baseName = ['header.html', 'footer.html'].includes(name) ? 'index.html' : name;
        const url = new URL(value, 'https://example.com/rasdad/' + baseName);
        assert(url.pathname.startsWith('/rasdad/'), `${name}: root-relative link ${value}`);
        const target = decodeURIComponent(url.pathname.slice('/rasdad/'.length));
        await readFile(path.join(output, target));
        if (url.hash) assert(ids[target]?.has(url.hash.slice(1)) || ids['header.html'].has(url.hash.slice(1)) || ids['footer.html'].has(url.hash.slice(1)), `${name}: missing anchor ${value}`);
    }
}
for (const name of await readdir(path.join(output, 'media'))) {
    if (!name.endsWith('.js')) continue;
    const code = await readFile(path.join(output, 'media', name), 'utf8');
    new vm.Script(code, { filename: name });
    assert(!/fetch\s*\(|\/api\//.test(code), `${name}: unexpected API dependency`);
}
const context = { window: {} };
vm.runInNewContext(await readFile(path.join(output, 'media/components.js'), 'utf8'), context);
for (const name of ['header.html', 'footer.html']) assert.equal(context.window.RASDAD_COMPONENTS[name], documents[name], 'Stale component bundle');
for (const name of await readdir(output)) assert([...names, 'media', '.nojekyll'].includes(name), `Unexpected publish file: ${name}`);
console.log('PASS: page links, anchors, unique IDs, JavaScript syntax, component bundle and static-only publish contents.');
