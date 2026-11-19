// V2-REPAIR D3 — 인사이트 배너 순수 함수.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { insightSource, signalChip, topInsight } from '../src/lib/insightView.ts';

const ev = (id, severity) => ({ id, kind: 'k', severity, as_of: '2026-11-18', text: 't', state: 'open', signals: [], action: null });

test('topInsight: 심각도 우선, 같으면 최신', () => {
	assert.equal(topInsight([ev(1, 'info'), ev(2, 'watch'), ev(3, 'watch')]).id, 3);
	assert.equal(topInsight([ev(1, 'act'), ev(9, 'watch')]).id, 1);
	assert.equal(topInsight([]), null);
});

test('signalChip: 값 있으면 이름+값, 불리언은 이름만', () => {
	assert.equal(signalChip({ signal: 'acwr', value: 1.62 }), 'ACWR 1.62');
	assert.equal(signalChip({ signal: 'checkin_pain', value: 'mild' }), '통증');
});

test('insightSource: 서버 source 우선, 없으면 polished 로 판정(ADR-059)', () => {
	assert.equal(insightSource({ source: 'ai', polished: true }), 'ai');
	assert.equal(insightSource({ source: 'rule', polished: true }), 'rule');
	assert.equal(insightSource({ polished: true }), 'ai');
	assert.equal(insightSource({}), 'rule');
});
