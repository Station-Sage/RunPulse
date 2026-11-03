import { test } from 'node:test';
import assert from 'node:assert/strict';
import { defaultSelection, needsConfirm, toggleKey, archiveBody } from '../src/lib/exportScope.ts';
import { errorText } from '../src/lib/exports.ts';

const groups = [
	{ key: 'activities', label: 'a', default: true, sensitive: false },
	{ key: 'plans', label: 'p', default: false, sensitive: false },
	{ key: 'episodes', label: 'e', default: true, sensitive: true }
];

test('defaultSelection: 기본 체크 그룹만', () => {
	assert.deepEqual(defaultSelection(groups), ['activities', 'episodes']);
});

test('needsConfirm: episodes 선택 시에만', () => {
	assert.equal(needsConfirm(['activities']), false);
	assert.equal(needsConfirm(['episodes']), true);
});

test('toggleKey: 추가·제거', () => {
	assert.deepEqual(toggleKey(['a'], 'b'), ['a', 'b']);
	assert.deepEqual(toggleKey(['a', 'b'], 'a'), ['b']);
});

test('archiveBody: episodes 없으면 include_dismissed 무시', () => {
	assert.equal(archiveBody(['activities'], true, {}).include_dismissed, false);
	assert.deepEqual(archiveBody(['episodes'], true, { from: '2026-01-01' }), {
		groups: ['episodes'], include_dismissed: true, from: '2026-01-01'
	});
});

test('errorText: 코드별 문구', () => {
	assert.match(errorText({ error_code: 'EXPORT_DISK_FULL', error: null }), /공간/);
	assert.equal(errorText({ error_code: null, error: null }), '실패');
});
