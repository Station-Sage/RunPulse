import test from 'node:test';
import assert from 'node:assert/strict';
import { lifecycleOf, todayEmptyCopy } from '../src/lib/states.ts';

test('lifecycleOf 판정 표', () => {
	assert.equal(lifecycleOf(null), 'unconnected');
	assert.equal(lifecycleOf({ connected_count: 0, first_sync_running: false }), 'unconnected');
	assert.equal(lifecycleOf({ connected_count: 1, first_sync_running: true }), 'syncing');
	assert.equal(lifecycleOf({ connected_count: 2, first_sync_running: false }), 'connected');
});

test('todayEmptyCopy 링크는 v2 라우트이며 /settings 가 아니다', () => {
	for (const l of ['syncing', 'unconnected', 'connected']) {
		const c = todayEmptyCopy(l);
		assert.ok(c.href.startsWith('/') && !c.href.includes('settings'));
	}
});
