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

/** TSB 부호 표기: +13 / −1 / 0 (정수 반올림). */
export function signedTsb(tsb: number): string {
	const r = Math.round(tsb);
	return r > 0 ? `+${r}` : r < 0 ? `−${-r}` : '0';
}

export interface RaceSummaryInput {
	days_left: number;
	pred_sec: number | null;
	low_sec: number | null;
	high_sec: number | null;
	range_kind: 'model_envelope' | 'calibrated80' | null;
	target_sec: number | null;
}

function clockOf(sec: number): string {
	const s = Math.round(sec);
	const h = Math.floor(s / 3600);
	const m = Math.floor((s % 3600) / 60);
	return `${h}:${String(m).padStart(2, '0')}`;
}

/** B4 한 줄 조각 — [D-56, 예측 3:40 (모델 범위 3:26–4:03), 목표 3:19]. 예측 없으면 '예측 수집 중'. */
export function raceSummaryParts(s: RaceSummaryInput): string[] {
	const parts = [countdownLabel(s.days_left)];
	if (s.pred_sec == null) {
		parts.push('예측 수집 중');
	} else {
		let pred = `예측 ${clockOf(s.pred_sec)}`;
		if (s.low_sec != null && s.high_sec != null) {
			const kind = s.range_kind === 'model_envelope' ? '모델 범위 ' : '';
			pred += ` (${kind}${clockOf(s.low_sec)}–${clockOf(s.high_sec)})`;
		}
		parts.push(pred);
	}
	if (s.target_sec != null) parts.push(`목표 ${clockOf(s.target_sec)}`);
	return parts;
}

/** 예측 추이(최근 90일) 첫·마지막 값 차이 — {deltaSec(음수=빨라짐), label}. 점이 2개 미만이면 null. */
export function trendDelta(history: { date: string; value: number }[]): { deltaSec: number; label: string } | null {
	if (history.length < 2) return null;
	const delta = history[history.length - 1].value - history[0].value;
	if (Math.abs(delta) < 30) return { deltaSec: delta, label: '90일간 거의 변화 없음' };
	const abs = Math.abs(delta);
	const m = Math.floor(abs / 60);
	const s = Math.round(abs % 60);
	return { deltaSec: delta, label: `90일간 ${m}분 ${s}초 ${delta < 0 ? '빨라짐' : '느려짐'}` };
}
