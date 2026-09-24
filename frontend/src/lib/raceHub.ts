// frontend/src/lib/raceHub.ts
// 레이스 허브 순수 함수 — 격차 톤, 격차 포맷, 예측 시리즈 변환. 테스트: frontend/tests/raceHub.test.mjs

import type { TrendSeries } from './trendChart';

/** 격차 톤: 음수(예측이 빠름)=green, null·0=teal(권장), 양수(느림)=amber */
export type GapTone = 'green' | 'teal' | 'amber';

export function gapTone(gapSec: number | null): GapTone {
	if (gapSec === null || gapSec === 0) return 'teal';
	return gapSec < 0 ? 'green' : 'amber';
}

/** gap_sec를 "+2:23" / "-1:45" 형식으로. 0이면 "±0:00". */
export function formatGap(gapSec: number): string {
	if (gapSec === 0) return '±0:00';
	const abs = Math.abs(gapSec);
	const sign = gapSec > 0 ? '+' : '-';
	const min = Math.floor(abs / 60);
	const sec = abs % 60;
	return `${sign}${min}:${String(sec).padStart(2, '0')}`;
}

/** 예측 이력 배열을 TrendChart용 TrendSeries로 변환. color는 호출자가 tone에 따라 지정. */
export function predictionToSeries(
	history: { date: string; value: number }[],
	color: string
): TrendSeries {
	return {
		key: 'pred',
		label: '예측',
		color,
		points: history.map((h) => ({ date: h.date, value: h.value }))
	};
}
