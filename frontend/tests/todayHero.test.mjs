import { test } from 'node:test';
import assert from 'node:assert/strict';
import { eulReul, euroRo, morningAsOf, heroView, caveatText, bipolarAngle, trackPct, deltaText } from '../src/lib/todayHero.ts';

const base = { state: 'pre', target_date: '2026-09-27', verdict: 'as_planned', today_result: null, session: null, adjustment: null, caveats: [] };

test('조사: 을/를, 으로/로', () => {
	assert.equal(eulReul('템포'), '템포를');
	assert.equal(eulReul('인터벌'), '인터벌을');
	assert.equal(euroRo('이지런'), '이지런으로');
	assert.equal(euroRo('휴식'), '휴식으로');
	assert.equal(euroRo('회복'), '회복으로');
	assert.equal(euroRo('롱'), '롱으로');
	assert.equal(euroRo('인터벌'), '인터벌로');
	assert.equal(euroRo('템포'), '템포로');
});

test('morningAsOf: 요일 포함', () => {
	assert.equal(morningAsOf('2026-09-27'), '아침 기준 · 9월 27일 (일)');
});

test('heroView pre: 세션·조정 문구', () => {
	const v = heroView({ ...base, session: { id: 3, title: '템포', distance_m: 8000, pace_min: 300, pace_max: 320, zone: 3 },
		adjustment: { reason: 'TSB 낮음', from: '템포', to: '이지런' }, verdict: 'down' });
	assert.equal(v.headline, '오늘 · 템포');
	assert.match(v.sub, /8\.0km/);
	assert.match(v.sub, /Z3/);
	assert.equal(v.adjustment, '⚠ TSB 낮음 → 템포를 이지런으로');
	assert.equal(v.tone, 'caution');
	assert.equal(v.cta, 'session');
});

test('heroView done/extra/rest/no_plan', () => {
	const r = { activity_id: 1, distance_m: 9300, outcome_label: null, plan_ratio_pct: null };
	assert.equal(heroView({ ...base, state: 'done', today_result: r }).headline, '오늘 완료 ✓ 9.3km');
	assert.equal(heroView({ ...base, state: 'done', today_result: r }).sub, '');
	assert.equal(heroView({ ...base, state: 'done', today_result: { ...r, plan_ratio_pct: 95 } }).sub, '계획의 95%');
	assert.equal(heroView({ ...base, state: 'extra', today_result: r }).headline, '오늘 9.3km 달렸어요');
	assert.equal(heroView({ ...base, state: 'rest' }).headline, '오늘은 휴식');
	assert.equal(heroView({ ...base, state: 'no_plan' }).cta, 'plan_new');
});

test('caveatText: source_missing', () => {
	assert.match(caveatText({ code: 'source_missing', provider: 'garmin', days: 2 }, () => 'Garmin'), /Garmin 데이터가 2일째/);
});

test('bipolarAngle: 0=중앙(90°), 음수 왼쪽', () => {
	assert.equal(bipolarAngle(0), 90);
	assert.equal(bipolarAngle(-40), 180);
	assert.equal(bipolarAngle(40), 0);
	assert.equal(bipolarAngle(100), 0);
});

test('trackPct·deltaText', () => {
	assert.equal(trackPct(50), 50);
	assert.equal(trackPct(120), 100);
	assert.equal(deltaText(3), '+3');
	assert.equal(deltaText(-2.5), '−2.5');
	assert.equal(deltaText(0), '±0');
	assert.equal(deltaText(null), '');
});

test('heroView: 사유 AI 문장(source=ai)만 대체·표시, rule 이면 규칙 조립', () => {
	const adj = { ...base, session: { id: 3, title: '이지런' }, verdict: 'down', adjustment: { reason: 'TSB 낮음', from: '템포', to: '이지런' } };
	const rule = heroView({ ...adj, reason_wording: { text: '규칙 문장', source: 'rule' } });
	assert.equal(rule.adjustment, '⚠ TSB 낮음 → 템포를 이지런으로');
	assert.equal(rule.aiWorded, false);
	const ai = heroView({ ...adj, reason_wording: { text: 'TSB 가 낮아 오늘 템포 대신 이지런으로 가요.', source: 'ai' } });
	assert.equal(ai.adjustment, '⚠ TSB 가 낮아 오늘 템포 대신 이지런으로 가요.');
	assert.equal(ai.aiWorded, true);
	const hold = { ...base, hold_reason: [{ code: 'crs_stale', text: '컨디션 입력이 오래돼 증량은 보류했어요' }] };
	assert.equal(heroView(hold).hold, '컨디션 입력이 오래돼 증량은 보류했어요');
	assert.equal(heroView(hold).aiWorded, false);
	const holdAi = heroView({ ...hold, reason_wording: { text: '회복 신호가 오래돼 오늘은 계획대로만 가요.', source: 'ai' } });
	assert.equal(holdAi.hold, '회복 신호가 오래돼 오늘은 계획대로만 가요.');
	assert.equal(holdAi.aiWorded, true);
	// 완료 상태에선 사유 줄이 없으니 AI 표시도 없다
	assert.equal(heroView({ ...adj, state: 'done', today_result: { activity_id: 1, distance_m: 5000 },
		reason_wording: { text: 'x', source: 'ai' } }).aiWorded, false);
});
