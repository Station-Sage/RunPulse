// frontend/src/lib/streamAxis.ts
// 스트림 화면 시간축 계산 유틸. 순수 함수만 포함 — 테스트: frontend/tests/streamAxis.test.mjs

/**
 * n개 포인트 배열에서 분율 fraction(0~1)에 해당하는 인덱스를 반환한다.
 * fraction=0 → 0, fraction=1 → n-1.
 */
export function indexAtFraction(n: number, fraction: number): number {
	if (n <= 0) return 0;
	const clamped = Math.max(0, Math.min(1, fraction));
	return Math.round(clamped * (n - 1));
}

/**
 * elapsed_sec 배열과 눈금 개수를 받아 x축 눈금 목록을 반환한다.
 * 반환값: { frac: 0~1 위치(CSS left 용), label: "0" | "15m" | "1h 03m" 형식 }[]
 * 위치는 포인트 인덱스 기준 등간격, 라벨은 해당 인덱스의 실제 elapsed_sec.
 */
export function axisTicks(
	elapsed: (number | null)[],
	count: number = 5
): { label: string; frac: number }[] {
	const n = elapsed.length;
	if (n === 0 || count < 2) return [];

	const ticks: { label: string; frac: number }[] = [];
	for (let t = 0; t < count; t++) {
		const frac = t / (count - 1);
		const idx = indexAtFraction(n, frac);
		const sec = elapsed[idx] ?? nearestNonNull(elapsed, idx);
		ticks.push({ frac, label: formatElapsed(sec) });
	}
	return ticks;
}

function nearestNonNull(arr: (number | null)[], start: number): number {
	for (let d = 1; d < arr.length; d++) {
		if (start - d >= 0 && arr[start - d] != null) return arr[start - d]!;
		if (start + d < arr.length && arr[start + d] != null) return arr[start + d]!;
	}
	return 0;
}

export function isTrustedBasis(basis?: string | null): boolean {
	return basis === 'measured' || basis === 'derived' || basis === 'scaled';
}

/**
 * elapsed_sec 배열과 활동 총 시간(초)을 받아 시간 눈금에 쓸 elapsed 배열을 반환한다.
 * 마지막 non-null elapsed_sec가 totalSec의 90% 미만이면 등간격 샘플로 보고
 * totalSec에 비례해 재환산한다(Garmin downsample 시 elapsed_sec가 샘플 인덱스로
 * 저장되는 경우 대응). 유효한 경우에는 원본 값을 그대로 반환한다.
 * 반환값에 null은 포함되지 않는다(null → 0으로 대체).
 */
export function streamSeconds(
	elapsed: (number | null)[],
	totalSec: number,
	basis?: string | null,
	originalCount?: number | null
): number[] {
	const n = elapsed.length;
	// 서버가 시간축 출처를 확정한 경우(measured/derived/scaled) 저장값을 그대로 쓴다. 휴리스틱은 meta 없는 행 전용.
	if (isTrustedBasis(basis)) return elapsed.map((v) => v ?? 0);
	if (n === 0 || totalSec <= 0) return elapsed.map((v) => v ?? 0);
	if (n === 1) return [0];

	// 마지막 non-null elapsed_sec 찾기
	let lastSec = 0;
	for (let i = n - 1; i >= 0; i--) {
		if (elapsed[i] != null) {
			lastSec = elapsed[i]!;
			break;
		}
	}

	if (lastSec >= totalSec * 0.9) {
		// 저장값이 신뢰할 만한 수준 — 그대로 사용
		return elapsed.map((v) => v ?? 0);
	}

	// 등간격 재환산: i번째 샘플 → (원본 점 번호 / (N-1)) * totalSec.
	// 서버 다운샘플(`?max_points=`, A-36)을 받았으면 N = 원본 점 수 — 서버와 같은 균등 간격 규칙으로 원본 번호를 되짚는다.
	const N = originalCount != null && originalCount > n ? originalCount : n;
	return elapsed.map((_, i) => {
		const orig = N === n ? i : Math.round((i * (N - 1)) / (n - 1));
		return Math.round((orig / (N - 1)) * totalSec);
	});
}

/**
 * elapsed_sec 값을 축 눈금용 "0" | "15분" | "1시간 03분" 으로 포맷한다.
 * 예전 "13m" 은 고도·거리 축의 m(미터)와 헷갈려 한글 단위로 바꿨다(A-36).
 */
export function formatElapsed(sec: number | null | undefined): string {
	if (sec == null) return '—';
	const s = Math.round(sec);
	if (s === 0) return '0';
	const h = Math.floor(s / 3600);
	const m = Math.floor((s % 3600) / 60);
	if (h > 0) return `${h}시간 ${m.toString().padStart(2, '0')}분`;
	return `${m}분`;
}

/** 스트림 값 범위 "최소 – 최대" — 페이스 외 스트림(심박·고도·케이던스·파워)은 정수(A-37, 고도는 A-12 규칙과 같음). */
export function streamRange(vals: (number | null)[]): string {
	const nums = vals.filter((v): v is number => v != null);
	if (nums.length === 0) return '—';
	return `${Math.round(Math.min(...nums))} – ${Math.round(Math.max(...nums))}`;
}

const SOURCE_NAMES: Record<string, string> = { garmin: 'Garmin', strava: 'Strava', intervals: 'Intervals.icu', runalyze: 'Runalyze', runpulse: 'RunPulse' };

/**
 * 스트림 머리 한 줄 — "Garmin · 기록점 1,675개(약 2초마다)". 소스명은 표준 표기(A-38),
 * '기록점'의 뜻은 평균 간격으로 바로 보인다. totalSec 가 없으면 간격은 생략.
 */
export function pointsCaption(sources: string[], n: number, totalSec: number | null, shown?: number | null): string {
	const names = [...new Set(sources.map((s) => SOURCE_NAMES[s.split(':')[0]] ?? s))].join(' / ');
	const gap = totalSec != null && totalSec > 0 && n > 1 ? Math.round(totalSec / (n - 1)) : null;
	const every = gap != null && gap >= 1 ? `(약 ${gap}초마다)` : '';
	// n = 원본 기록점 수. 서버가 줄여 보냈으면(shown < n) 차트에 그린 점 수를 덧붙인다(A-36, 문구 TXT-1 잠정)
	const thin = shown != null && shown < n ? ` · 차트는 ${shown.toLocaleString('ko-KR')}개로 줄여 표시` : '';
	return `${names ? `${names} · ` : ''}기록점 ${n.toLocaleString('ko-KR')}개${every}${thin}`;
}

/** 거리 기준 x축 눈금 — 포인트 등간격 위치에 해당 포인트의 누적 거리(km) 라벨. */
export function distanceTicks(
	distM: (number | null)[],
	count: number = 5
): { label: string; frac: number }[] {
	const n = distM.length;
	if (n === 0 || count < 2) return [];
	return Array.from({ length: count }, (_, t) => {
		const frac = t / (count - 1);
		const d = distM[indexAtFraction(n, frac)] ?? nearestNonNull(distM, indexAtFraction(n, frac));
		return { frac, label: `${(d / 1000).toFixed(d >= 10000 ? 0 : 1)}km` };
	});
}

/** 크로스헤어 점의 세로 위치(%, 위=0). Sparkline의 min–max 선형 매핑과 동일. */
export function dotTopPct(values: (number | null)[], v: number | null, invert: boolean): number | null {
	if (v == null) return null;
	const nums = values.filter((x): x is number => x != null);
	if (nums.length === 0) return null;
	const mn = Math.min(...nums);
	const mx = Math.max(...nums);
	if (mx === mn) return 50;
	const frac = (v - mn) / (mx - mn);
	return (invert ? frac : 1 - frac) * 100;
}
