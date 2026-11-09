import test from 'node:test';
import assert from 'node:assert/strict';
import { navTabs, isTabActive } from '../src/lib/shell/navTabs.ts';

test('navTabs: 3개 탭, base 접두', () => {
	const t = navTabs('/v2');
	assert.deepEqual(t.map((x) => x.label), ['Today', 'Library', 'Coach']);
	assert.equal(t[0].href, '/v2/today');
});

test('isTabActive: 하위 경로 포함, 다른 탭 제외', () => {
	assert.equal(isTabActive('/v2/library/metrics/ctl', '/v2', '/library'), true);
	assert.equal(isTabActive('/v2/today', '/v2', '/library'), false);
});

test('S-06 tabHighlightPath: 이동 중이면 목적지, 아니면 현재 경로', async () => {
	const { tabHighlightPath } = await import('../src/lib/shell/navTabs.ts');
	assert.equal(tabHighlightPath('/v2/library', '/v2/today'), '/v2/today');
	assert.equal(tabHighlightPath('/v2/library', null), '/v2/library');
	assert.equal(tabHighlightPath('/v2/library', undefined), '/v2/library');
});
