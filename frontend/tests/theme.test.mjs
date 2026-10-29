import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolveTheme, themeColorFor, readPref, writePref, isPref, THEME_COLORS } from '../src/lib/theme/theme.ts';

test('resolveTheme: system 은 OS 값, 수동은 그대로', () => {
	assert.equal(resolveTheme('system', true), 'light');
	assert.equal(resolveTheme('system', false), 'dark');
	assert.equal(resolveTheme('dark', true), 'dark');
	assert.equal(resolveTheme('light', false), 'light');
});

test('themeColorFor: system 은 기본 쌍, 수동은 두 meta 모두 덮음', () => {
	assert.deepEqual(themeColorFor('system'), ['#0f172a', '#f7f5f2']);
	assert.deepEqual(themeColorFor('light'), ['#f7f5f2', '#f7f5f2']);
	assert.deepEqual(themeColorFor('dark'), ['#0f172a', '#0f172a']);
});

test('read/writePref: 저장·복원, system 은 키 제거, 저장소 오류는 system', () => {
	const store = new Map();
	globalThis.localStorage = {
		getItem: (k) => store.get(k) ?? null,
		setItem: (k, v) => store.set(k, v),
		removeItem: (k) => store.delete(k)
	};
	assert.equal(readPref(), 'system');
	writePref('light');
	assert.equal(readPref(), 'light');
	writePref('system');
	assert.equal(store.size, 0);
	store.set('rp-theme', 'bogus');
	assert.equal(readPref(), 'system');
	globalThis.localStorage = {
		getItem() {
			throw new Error('denied');
		}
	};
	assert.equal(readPref(), 'system');
	assert.ok(isPref('dark') && !isPref('x'));
	delete globalThis.localStorage;
});

test('theme-init.js · app.html 의 theme-color 값이 THEME_COLORS 와 일치', () => {
	const init = readFileSync(new URL('../static/theme-init.js', import.meta.url), 'utf8');
	const html = readFileSync(new URL('../src/app.html', import.meta.url), 'utf8');
	for (const c of Object.values(THEME_COLORS)) {
		assert.ok(init.includes(c), `theme-init.js 에 ${c}`);
		assert.ok(html.includes(`content="${c}"`), `app.html 에 ${c}`);
	}
	assert.ok(html.indexOf('theme-init.js') < html.indexOf('%sveltekit.head%'));
});
