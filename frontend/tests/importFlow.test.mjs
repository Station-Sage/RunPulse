import { test } from 'node:test';
import assert from 'node:assert/strict';
import { canCommit, kindLabel, periodText, previewLines } from '../src/lib/importFlow.ts';

const prev = (o = {}) => ({
	upload_id: 'u', kind: 'strava_csv', source: 'strava', recognized: 3, new: 2, duplicates: 1,
	enriched: 0, errors: 0, merged: 0, period: { from: '2026-01-01T07:00:00', to: '2026-02-01T07:00:00' }, ...o
});

test('periodText: 기간·단일일·없음', () => {
	assert.equal(periodText({ from: '2026-01-01T07:00', to: '2026-02-01T07:00' }), '2026-01-01 ~ 2026-02-01');
	assert.equal(periodText({ from: '2026-01-01T07:00', to: null }), '2026-01-01');
	assert.equal(periodText({ from: null, to: null }), '기간 정보 없음');
});

test('previewLines: 0인 항목 생략', () => {
	const l = previewLines(prev());
	assert.ok(l.includes('새로 들어갈 활동 2건'));
	assert.ok(l.includes('이미 있는 활동 1건은 건너뛰어요'));
	assert.ok(!l.some((s) => s.includes('합쳐지는')));
	assert.ok(previewLines(prev({ new: 0 })).includes('새로 들어갈 활동이 없어요'));
});

test('canCommit: 새 활동 또는 보강이 있을 때만', () => {
	assert.equal(canCommit(null), false);
	assert.equal(canCommit(prev({ new: 0, enriched: 0 })), false);
	assert.equal(canCommit(prev({ new: 0, enriched: 2 })), true);
	assert.equal(canCommit(prev()), true);
});

test('kindLabel', () => assert.equal(kindLabel('garmin_csv'), 'Garmin 활동 CSV'));
