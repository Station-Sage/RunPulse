// frontend/src/lib/raceHub.ts
// 레이스 허브 순수 함수 — 격차 판정·D-day·거리 표기. 테스트: frontend/tests/raceHub.test.mjs

export type GapTone = 'ahead' | 'on' | 'behind' | 'unknown';

/** 예측−목표 격차(초, 양수=목표보다 느림)를 톤과 문구로. |격차|<60초는 '목표 페이스권'. null이면 unknown. */
export function gapVerdict(gapSec: number | null): { tone: GapTone; label: string } {
	if (gapSec == null) return { tone: 'unknown', label: '목표 시간을 설정하면 격차를 보여줘요' };
	if (Math.abs(gapSec) < 60) return { tone: 'on', label: '목표 페이스권' };
	const abs = Math.abs(gapSec);
	const h = Math.floor(abs / 3600);
	const m = Math.floor((abs % 3600) / 60);
	const s = Math.round(abs % 60);
	const text = h > 0 ? `${h}시간 ${m}분` : `${m}분 ${s}초`;
	return gapSec < 0
		? { tone: 'ahead', label: `목표보다 ${text} 빠름` }
		: { tone: 'behind', label: `목표보다 ${text} 느림` };
}

/** D-day 문구: 0이면 'D-DAY', 양수 'D-31', 음수 'D+3'. */
export function countdownLabel(daysLeft: number): string {
	if (daysLeft === 0) return 'D-DAY';
	return daysLeft > 0 ? `D-${daysLeft}` : `D+${-daysLeft}`;
}

/** 목표 거리(km) 표기: 풀/하프/10K/5K 근사(±허용) 아니면 소수 1자리 km. */
export function distanceLabel(km: number): string {
	if (Math.abs(km - 42.195) <= 2.5) return '풀 마라톤';
	if (Math.abs(km - 21.0975) <= 2) return '하프';
	if (Math.abs(km - 10) <= 1.5) return '10K';
	if (Math.abs(km - 5) <= 1) return '5K';
	return `${km.toFixed(1)}km`;
}

export type FormTone = 'bad' | 'warn' | 'neutral' | 'good';

/** 레이스 아침 TSB 해석 — <-30 과부하, <-10 훈련 부하, <5 중립, ≤15 레이스 최적, 그 위는 회복 과다. */
export function formBand(tsb: number): { label: string; tone: FormTone } {
	if (tsb < -30) return { label: '과부하', tone: 'bad' };
	if (tsb < -10) return { label: '훈련 부하 높음', tone: 'warn' };
	if (tsb < 5) return { label: '중립', tone: 'neutral' };
	if (tsb <= 15) return { label: '레이스 최적', tone: 'good' };
	return { label: '회복 과다', tone: 'warn' };
}

/** TSB 부호 표기: +13 / −1 / 0 (정수 반올림). */
export function signedTsb(tsb: number): string {
	const r = Math.round(tsb);
	return r > 0 ? `+${r}` : r < 0 ? `−${-r}` : '0';
}
