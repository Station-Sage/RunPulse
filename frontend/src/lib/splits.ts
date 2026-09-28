// frontend/src/lib/splits.ts
// km 스플릿 계산 순수 함수 — 스트림의 시간·거리를 활동 총 시간·거리에 맞춰 재구성한다.
// 테스트: frontend/tests/splits.test.mjs (스트림 elapsed_sec가 인덱스로 저장된 경우: P7-DATA-STREAM-ELAPSED)

export interface SplitStream {
	elapsed_sec: number;
	distance_m: number | null;
	speed_ms: number | null;
	heart_rate: number | null;
	altitude_m: number | null;
}

export interface Split {
	km: number;
	distanceM: number;
	sec: number;
	paceSecKm: number;
	/** 구간 안의 정지 시간(초) — sec·paceSecKm에서 빠졌다. 0이면 정지 없음 */
	stoppedSec: number;
	avgHr: number | null;
	elevDelta: number | null;
}

/** 샘플별 경과 초. 마지막 elapsed_sec가 totalSec의 90% 미만이면 등간격 샘플로 보고 totalSec에 비례해 재환산. */
export function sampleTimes(streams: SplitStream[], totalSec: number): number[] {
	const n = streams.length;
	if (n < 2 || totalSec <= 0) return streams.map((s) => s.elapsed_sec);
	if (streams[n - 1].elapsed_sec >= totalSec * 0.9) return streams.map((s) => s.elapsed_sec);
	return streams.map((_, i) => (i * totalSec) / (n - 1));
}

/** 샘플별 누적 거리(m). distance_m가 전부 있으면 그대로, 없으면 속도 적분 후 활동 총 거리에 맞춰 스케일링. */
export function cumulativeDistance(
	streams: SplitStream[],
	totalSec: number,
	totalDistM: number
): number[] {
	const n = streams.length;
	if (n === 0) return [];
	const last = streams[n - 1].distance_m;
	if (streams.every((s) => s.distance_m != null) && last != null && last > 0) {
		return streams.map((s) => s.distance_m as number);
	}
	const t = sampleTimes(streams, totalSec);
	const d: number[] = [0];
	let lastSpeed = 0;
	for (let i = 1; i < n; i++) {
		const sp = streams[i].speed_ms;
		if (sp != null && Number.isFinite(sp)) lastSpeed = Math.max(0, sp);
		d.push(d[i - 1] + lastSpeed * Math.max(0, t[i] - t[i - 1]));
	}
	const end = d[n - 1];
	if (end > 0 && totalDistM > 0) {
		const k = totalDistM / end;
		return d.map((v) => v * k);
	}
	return d;
}

// 정지 기준(백엔드 src/metrics/stream_utils.py와 같은 값, UX 리뷰 20 design §4-5)
const STOP_SPEED_MS = 0.5;
const GAP_SEC = 10;
const GAP_DIST_M = 5;

/** 샘플 i(≥1)가 직전 샘플 이후 정지 상태였는지. */
export function stoppedFlags(streams: SplitStream[], t: number[], d: number[]): boolean[] {
	return streams.map((s, i) => {
		if (i === 0) return false;
		const dt = t[i] - t[i - 1];
		if (dt <= 0) return false;
		const dd = d[i] - d[i - 1];
		const speed = s.speed_ms ?? dd / dt;
		return speed < STOP_SPEED_MS || (dt > GAP_SEC && dd < GAP_DIST_M);
	});
}

/** 누적 정지 시간 배열 → time 시점의 누적 정지 초(선형보간). */
function stoppedAt(t: number[], cum: number[], time: number): number {
	let lo = 0;
	let hi = t.length - 1;
	if (time <= t[0]) return 0;
	if (time >= t[hi]) return cum[hi];
	while (hi - lo > 1) {
		const mid = (lo + hi) >> 1;
		if (t[mid] <= time) lo = mid;
		else hi = mid;
	}
	const span = t[hi] - t[lo];
	return span > 0 ? cum[lo] + ((time - t[lo]) / span) * (cum[hi] - cum[lo]) : cum[lo];
}

function nearestIndex(t: number[], time: number): number {
	let lo = 0;
	let hi = t.length - 1;
	while (lo < hi) {
		const mid = (lo + hi) >> 1;
		if (t[mid] < time) lo = mid + 1;
		else hi = mid;
	}
	if (lo > 0 && Math.abs(t[lo - 1] - time) <= Math.abs(t[lo] - time)) return lo - 1;
	return lo;
}

/** 1km 단위 구간(마지막은 200m 이상 남을 때만 부분 구간). 재구성 불가(샘플<2, 총시간≤0, 총거리<1km)면 [].
 *  sec·페이스는 **이동 시간** 기준(정지 제외), 평균 심박도 이동 샘플만. */
export function computeSplits(
	streams: SplitStream[],
	totalSec: number,
	totalDistM: number
): Split[] {
	const n = streams.length;
	if (n < 2 || totalSec <= 0 || totalDistM < 1000) return [];
	const t = sampleTimes(streams, totalSec);
	const d = cumulativeDistance(streams, totalSec, totalDistM);
	const stopped = stoppedFlags(streams, t, d);
	const cumStop: number[] = [0];
	for (let i = 1; i < n; i++) cumStop.push(cumStop[i - 1] + (stopped[i] ? t[i] - t[i - 1] : 0));
	const dEnd = d[n - 1];
	const fullKm = Math.floor(dEnd / 1000);

	// 경계 통과 시각 (선형보간)
	const bounds: number[] = [t[0]];
	let j = 1;
	for (let k = 1; k <= fullKm; k++) {
		const target = k * 1000;
		while (j < n - 1 && d[j] < target) j++;
		const span = d[j] - d[j - 1];
		const frac = span > 0 ? (target - d[j - 1]) / span : 1;
		bounds.push(t[j - 1] + Math.min(1, Math.max(0, frac)) * (t[j] - t[j - 1]));
	}

	const ranges: { start: number; end: number; distanceM: number; last: boolean }[] = [];
	for (let k = 1; k <= fullKm; k++) {
		ranges.push({ start: bounds[k - 1], end: bounds[k], distanceM: 1000, last: false });
	}
	const remainder = dEnd - fullKm * 1000;
	if (remainder >= 200) {
		ranges.push({ start: bounds[fullKm], end: t[n - 1], distanceM: remainder, last: true });
	}

	return ranges.map((r, i) => {
		const stoppedSec = stoppedAt(t, cumStop, r.end) - stoppedAt(t, cumStop, r.start);
		const sec = r.end - r.start - stoppedSec;
		let hrSum = 0;
		let hrCount = 0;
		for (let s = 0; s < n; s++) {
			const inside = t[s] >= r.start && (t[s] < r.end || (r.last && t[s] <= r.end));
			const hr = streams[s].heart_rate;
			if (inside && !stopped[s] && hr != null) {
				hrSum += hr;
				hrCount++;
			}
		}
		const a0 = streams[nearestIndex(t, r.start)].altitude_m;
		const a1 = streams[nearestIndex(t, r.end)].altitude_m;
		return {
			km: i + 1,
			distanceM: r.distanceM,
			sec,
			paceSecKm: sec / (r.distanceM / 1000),
			stoppedSec: Math.round(stoppedSec),
			avgHr: hrCount > 0 ? Math.round(hrSum / hrCount) : null,
			elevDelta: a0 != null && a1 != null ? Math.round((a1 - a0) * 10) / 10 : null
		};
	});
}
