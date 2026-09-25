import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { impactLines } from '../src/lib/activityImpact.ts';

describe('impactLines', () => {
	const fullInput = {
		ctl_delta: 2.3,
		tsb: 5.2,
		similar: { n: 6, pace_rank: 2, avg_pace_sec_km: 340, pace_diff_sec: -12.4 },
		race: { name: '서울마라톤', days_left: 30 },
	};

	it('모든 값이 있을 때 3줄 반환', () => {
		const lines = impactLines(fullInput);
		assert.equal(lines.length, 3);
	});

	it('첫 줄 — CTL +2.3 · TSB +5 형태', () => {
		const lines = impactLines(fullInput);
		assert.equal(lines[0], '이 날 체력(CTL) +2.3 · 폼(TSB) +5');
	});

	it('pace_diff_sec 음수 → 빠름', () => {
		const lines = impactLines(fullInput);
		assert.ok(lines[1].includes('12초/km 빠름'), `got: ${lines[1]}`);
	});

	it('pace_diff_sec === 0 → 평균과 같음', () => {
		const input = {
			...fullInput,
			similar: { ...fullInput.similar, pace_diff_sec: 0 },
		};
		const lines = impactLines(input);
		assert.ok(lines[1].includes('평균과 같음'), `got: ${lines[1]}`);
	});

	it('전부 null → 빈 배열', () => {
		const lines = impactLines({ ctl_delta: null, tsb: null, similar: null, race: null });
		assert.deepEqual(lines, []);
	});
});
