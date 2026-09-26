import { test } from 'node:test';
import assert from 'node:assert/strict';
import { clock, rangeLabel, confidenceLabel, diffVsSelf, contributionLabel } from '../src/lib/predictionCompare.ts';

const self = { key: 'self', label: '', provider: '', value_sec: 2739, low_sec: 2601, high_sec: 2878, confidence: 0.75 };

test('clock', () => {
	assert.equal(clock(2739), '45:39');
	assert.equal(clock(13239), '3:40:39');
	assert.equal(clock(59.6), '1:00');
});

test('rangeLabel / confidenceLabel', () => {
	assert.equal(rangeLabel(self), '43:21~47:58');
	assert.equal(rangeLabel({ ...self, low_sec: null }), null);
	assert.equal(confidenceLabel(0.75), '높음');
	assert.equal(confidenceLabel(0.45), '보통');
	assert.equal(confidenceLabel(0.2), '낮음');
	assert.equal(confidenceLabel(null), null);
});

test('diffVsSelf', () => {
	assert.equal(diffVsSelf({ key: 'garmin', label: '', provider: '', value_sec: 2585 }, self), '−5.6%');
	assert.equal(diffVsSelf({ key: 'ref', label: '', provider: '', value_sec: 2741 }, self), '+0.1%');
	assert.equal(diffVsSelf(self, self), null);
	assert.equal(diffVsSelf({ key: 'garmin', label: '', provider: '', value_sec: null }, self), null);
});

test('contributionLabel', () => {
	assert.equal(contributionLabel({ race: 0.277, T: 0.324, I: 0.188, R: 0.0, H: 0.21 }), '대회 28 · 역치 세트 32 · 인터벌 세트 19 · 심박 21');
	assert.equal(contributionLabel({ race: 0.6, work: 0.2, hr: 0.2 }), '대회 60 · 작업 블록 20 · 심박 20'); // r3 기본 키
	assert.equal(contributionLabel({ race: 0.05, paced: 0.09, T: 0.86 }), '대회 5 · 최대 이하 대회 9 · 역치 세트 86');
	assert.equal(contributionLabel({ T: 0.6, H: 0.4 }), '역치 세트 60 · 심박 40');
	assert.equal(contributionLabel(null), null);
});
