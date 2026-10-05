import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { impactLines } from '../src/lib/activityImpact.ts';

describe('impactLines', () => {
	const fullInput = {
		ctl_contribution: 2.3,
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

	it('similar 없음 → 기준 부족 안내 한 줄', () => {
		const lines = impactLines({ ctl_contribution: null, tsb: null, similar: null, race: null });
		assert.equal(lines.length, 1);
		assert.ok(lines[0].includes('기준이 아직 부족'));
	});

	it('same_class → 유형명·부하 중앙값 대비 줄', () => {
		const lines = impactLines({
			...fullInput,
			similar: { basis: 'same_class', class_label: '이지런', n: 8, pace_rank: 3, avg_pace_sec_km: 340,
				pace_diff_sec: 5, load_median: 72, load_pct_vs_median: 35.2 },
		});
		assert.ok(lines[1].startsWith('같은 이지런 이전 8회'), lines[1]);
		assert.equal(lines[2], '부하 대비: 같은 이지런 중앙값 72 대비 +35%');
	});

	it('same_course → 같은 코스 문구', () => {
		const lines = impactLines({ ...fullInput, similar: { ...fullInput.similar, basis: 'same_course' } });
		assert.ok(lines[1].startsWith('같은 코스 이전'));
	});
});
