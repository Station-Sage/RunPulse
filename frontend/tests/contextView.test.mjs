import test from 'node:test';
import assert from 'node:assert/strict';
import { confirmPrompts, episodeLabel, isOpen, staleBanner } from '../src/lib/contextView.ts';

const ep = (o) => ({ id: 1, kind: 'illness', start_date: '2026-10-10', end_date: null, severity: null, detail: {}, origin: 'manual', status: 'confirmed', last_confirmed_date: null, ...o });
const list = (o) => ({ episodes: [], illness_reconfirm: null, consent: { action: null, needs_first_prompt: false }, health_question: false, ...o });

test('episodeLabel: 의미 먼저, 진단 표현 없음', () => {
	assert.equal(episodeLabel(ep({ severity: 2, detail: { site: '목' } })), '아팠던 기록 · 많이 아파요 · 목');
	assert.equal(episodeLabel(ep({ kind: 'travel', detail: { delta_h: 7, direction: 'east' } })), '이동·시차 동쪽 +7시간');
	assert.equal(episodeLabel(ep({ kind: 'altitude', detail: { altitude_m: 2100 } })), '고지대 약 2100m');
});

test('isOpen: 종료·기각은 제외', () => {
	assert.equal(isOpen(ep()), true);
	assert.equal(isOpen(ep({ end_date: '2026-10-12' })), false);
	assert.equal(isOpen(ep({ status: 'dismissed' })), false);
});

test('confirmPrompts: 재확인 → 자동 후보 → 몸 상태 질문 순서', () => {
	const l = list({
		illness_reconfirm: { episode_id: 1, days_since: 8 },
		episodes: [ep({ id: 2, kind: 'travel', origin: 'auto', status: 'candidate', detail: { delta_h: 7, direction: 'east' } })],
		health_question: true
	});
	const p = confirmPrompts(l);
	assert.deepEqual(p.map((x) => x.key), ['re-1', 'c-2', 'health']);
	assert.equal(confirmPrompts(list({ health_question: true }))[0].key, 'health');
	assert.deepEqual(confirmPrompts(null), []);
});

test('staleBanner: 7일 재확인만', () => {
	assert.equal(staleBanner(list()), null);
	assert.match(staleBanner(list({ illness_reconfirm: { episode_id: 1, days_since: 9 } })), /9일째/);
});
