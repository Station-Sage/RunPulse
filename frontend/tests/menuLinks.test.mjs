import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { EXPORT_LABEL, EXPORT_PATH, MENU_GROUPS, TAB_ROOTS, allMenuLinks } from '../src/lib/menuLinks.ts';
import { navTabs } from '../src/lib/shell/navTabs.ts';

const drawer = readFileSync(new URL('../src/lib/components/MenuDrawer.svelte', import.meta.url), 'utf8');
const links = allMenuLinks();

test('export link points at the v2 EXP screen, not the v1 csv route (V1-11 b)', () => {
	assert.equal(EXPORT_PATH, '/data/export');
	assert.equal(EXPORT_LABEL, '데이터 내보내기');
	const exp = links.filter((l) => l.href.includes('export'));
	assert.deepEqual(exp.map((l) => [l.href, l.label, l.testid]), [[EXPORT_PATH, EXPORT_LABEL, 'menu-export-link']]);
	assert.ok(!drawer.includes('export.csv'));
});

test('MenuDrawer renders every group link with base, testid and closes the drawer', () => {
	assert.match(drawer, /\{#each MENU_GROUPS as group/);
	assert.match(drawer, /href="\{base\}\{link\.href\}"/);
	assert.match(drawer, /data-testid=\{link\.testid\}/);
	assert.match(drawer, /onclick=\{onClose\}/);
});

test('menu links are app-relative (base added at render) and have no v1 reload/back button', () => {
	for (const l of links) {
		assert.ok(l.href.startsWith('/') && !l.href.startsWith('/v2'), l.href);
	}
	assert.ok(!drawer.includes('data-sveltekit-reload'));
	assert.ok(!drawer.includes('back-to-v1'));
});

test('every menu link has a v2 route', () => {
	for (const l of links) {
		const f = new URL(`../src/routes${l.href}/+page.svelte`, import.meta.url);
		assert.ok(existsSync(f), l.href);
	}
});

test('MENUDRAWER-POST-V1: 그룹 순서 데이터→설정→바로가기, 탭 루트와 중복 없음, 링크 중복 없음', () => {
	assert.deepEqual(MENU_GROUPS.map((g) => g.id), ['data', 'settings', 'shortcuts']);
	assert.deepEqual([...TAB_ROOTS], navTabs('').map((t) => t.match));
	for (const l of links) assert.ok(!TAB_ROOTS.includes(l.href), `탭과 중복: ${l.href}`);
	assert.equal(new Set(links.map((l) => l.href)).size, links.length);
	for (const g of MENU_GROUPS) assert.ok(g.links.length > 0 && g.title.length > 0, g.id);
	// 데이터 영역은 주 탭이 없으므로 개요가 드로어 첫 링크다
	assert.equal(MENU_GROUPS[0].links[0].href, '/data');
});
