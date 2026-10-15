import { test } from 'node:test';
import assert from 'node:assert/strict';
import { freshnessBadgeText, freshnessReasonTexts, missingInputsText, holdText } from '../src/lib/freshness.ts';
import { heroView } from '../src/lib/todayHero.ts';

const base = { state: 'pre', target_date: '2026-10-15', verdict: 'as_planned', today_result: null, session: null, adjustment: null, caveats: [] };
const hold = [{ code: 'crs_stale', params: {}, text: '컨디션 입력이 오래돼 증량은 보류했어요' }];

test('freshnessBadgeText: 서버 badge.text 그대로, 없으면 null', () => {
	assert.equal(freshnessBadgeText({ level: 'partial', badge: { code: 'partial', text: '일부 데이터 없이 계산' } }), '일부 데이터 없이 계산');
	assert.equal(freshnessBadgeText({ level: 'fresh', badge: null }), null);
	assert.equal(freshnessBadgeText(null), null);
	assert.equal(freshnessBadgeText(undefined), null);
});

test('freshnessReasonTexts / missingInputsText', () => {
	const fr = { level: 'partial', badge: null, reasons: [{ code: 'a', text: '가' }, { code: 'b' }], missing_inputs: ['hrv', 'sleep'] };
	assert.deepEqual(freshnessReasonTexts(fr), ['가']);
	assert.equal(missingInputsText(fr), 'hrv, sleep');
	assert.deepEqual(freshnessReasonTexts(null), []);
	assert.equal(missingInputsText(null), '');
});

test('holdText: 여러 사유는 · 로 연결, 없으면 null', () => {
	assert.equal(holdText(hold), '컨디션 입력이 오래돼 증량은 보류했어요');
	assert.equal(holdText([...hold, { code: 'x', text: '다른 사유' }]), '컨디션 입력이 오래돼 증량은 보류했어요 · 다른 사유');
	assert.equal(holdText([]), null);
	assert.equal(holdText(null), null);
});

test('heroView: hold_reason 은 경고(adjustment) 와 분리된 hold 줄, adjustment 가 있으면 숨김', () => {
	const v = heroView({ ...base, hold_reason: hold });
	assert.equal(v.hold, '컨디션 입력이 오래돼 증량은 보류했어요');
	assert.equal(v.adjustment, null);
	assert.equal(v.tone, 'neutral');
	assert.equal(heroView({ ...base }).hold, null);
	const adj = heroView({ ...base, hold_reason: hold, adjustment: { reason: '피로', from: '템포', to: '이지런' } });
	assert.equal(adj.hold, null);
	assert.ok(adj.adjustment);
	assert.equal(heroView({ ...base, state: 'done', hold_reason: hold }).hold, null);
});
