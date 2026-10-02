import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { formatMetric } from '../src/lib/format.ts';

describe('formatMetric', () => {
	it('null/NaN은 대시', () => {
		assert.equal(formatMetric({ format: 'score' }, null), '—');
		assert.equal(formatMetric({}, NaN), '—');
	});
	it('format별 디스패치', () => {
		assert.equal(formatMetric({ format: 'race_time' }, 13223), '3:40:23');
		assert.equal(formatMetric({ format: 'pace' }, 330), '5:30/km');
		assert.equal(formatMetric({ format: 'signed' }, -14.7), '−15');
		assert.equal(formatMetric({ format: 'percent' }, 71.6), '72%');
		assert.equal(formatMetric({ format: 'score' }, 60.3), '60');
	});
	it('number는 decimal_places 우선', () => {
		assert.equal(formatMetric({ format: 'number', decimal_places: 1 }, 72.66), '72.7');
		assert.equal(formatMetric({ format: 'number', decimal_places: 0 }, 72.66), '73');
	});
});
