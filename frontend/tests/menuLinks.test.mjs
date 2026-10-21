import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { EXPORT_LABEL, EXPORT_PATH, DATA_LINKS, QUICK_LINKS } from '../src/lib/menuLinks.ts';

const drawer = readFileSync(new URL('../src/lib/components/MenuDrawer.svelte', import.meta.url), 'utf8');

test('export link points at the v2 EXP screen, not the v1 csv route (V1-11 b)', () => {
	assert.equal(EXPORT_PATH, '/data/export');
	assert.equal(EXPORT_LABEL, 'CSV 내보내기');
	for (const l of [...QUICK_LINKS, ...DATA_LINKS]) {
		assert.ok(!l.href.includes('export'), l.href);
	}
	assert.ok(!drawer.includes('export.csv'));
});

test('MenuDrawer renders the export link with base and closes the drawer', () => {
	assert.match(drawer, /href="\{base\}\{EXPORT_PATH\}"/);
	assert.match(drawer, /data-testid="menu-export-link"/);
});

test('menu links are app-relative (base added at render) and have no v1 reload/back button', () => {
	for (const l of [...QUICK_LINKS, ...DATA_LINKS]) {
		assert.ok(l.href.startsWith('/') && !l.href.startsWith('/v2'), l.href);
	}
	assert.ok(!drawer.includes('data-sveltekit-reload'));
	assert.ok(!drawer.includes('back-to-v1'));
	assert.match(drawer, /href="\{base\}\{link\.href\}"/);
});

test('every menu link has a v2 route', () => {
	for (const l of [...QUICK_LINKS, ...DATA_LINKS]) {
		const dir = l.href === '/coach' ? 'coach' : l.href.slice(1);
		const f = new URL(`../src/routes/${dir}/+page.svelte`, import.meta.url);
		assert.ok(readFileSync(f, 'utf8').length > 0, l.href);
	}
});

test('the EXP route exists in the v2 app', () => {
	const f = new URL('../src/routes/data/export/+page.svelte', import.meta.url);
	assert.ok(readFileSync(f, 'utf8').length > 0);
});
