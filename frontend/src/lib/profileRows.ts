// 러너 기준값 표시 헬퍼 — 라벨·단위·값 포맷.
import type { ProfileKey, ProfileRow, ProfileSource } from '$lib/api/data';

export const PROFILE_LABEL: Record<ProfileKey, string> = {
	hrmax: '최대심박',
	lthr: '젖산역치 심박',
	threshold_pace: '역치 페이스',
	resting_hr: '안정시 심박',
	weekly_km: '주간 목표 거리'
};

export const SOURCE_LABEL: Record<ProfileSource, string> = {
	self: '자체 추정',
	device: '기기 값',
	manual: '직접 입력'
};

export function formatProfileValue(key: ProfileKey, v: number | null | undefined): string {
	if (v == null) return '—';
	if (key === 'threshold_pace') return `${Math.floor(v / 60)}:${String(Math.round(v % 60)).padStart(2, '0')}/km`;
	if (key === 'weekly_km') return `${v}km`;
	return `${v}bpm`;
}

export function usedValue(row: ProfileRow): number | null {
	return row.using === 'none' ? null : (row[row.using]?.value ?? null);
}

/** 입력 문자열 → 숫자. 페이스는 m:ss 또는 초. 빈 값은 null(직접 입력 해제). 해석 불가면 undefined. */
export function parseProfileInput(key: ProfileKey, raw: string): number | null | undefined {
	const s = raw.trim();
	if (!s) return null;
	if (key === 'threshold_pace' && s.includes(':')) {
		// D-30: 정확히 m:ss 만(초과 구간 "5:30:99"·소수·음수 거부)
		const m = /^(\d{1,2}):([0-5]\d)$/.exec(s);
		return m ? Number(m[1]) * 60 + Number(m[2]) : undefined;
	}
	const n = Number(s);
	return Number.isFinite(n) ? n : undefined;
}

/** 서버 `profile_service._RANGE` 와 같은 허용 범위(S-19 입력 중 안내용). */
export const PROFILE_RANGE: Record<ProfileKey, [number, number]> = {
	hrmax: [120, 230],
	lthr: [100, 220],
	threshold_pace: [150, 600],
	resting_hr: [30, 100],
	weekly_km: [0, 300]
};

/** S-19: 입력 한 칸 검사 → {value, error}. 빈 값은 '입력 안 함'(value null, 오류 없음). */
export function checkProfileInput(key: ProfileKey, raw: string): { value: number | null; error: string | null } {
	const v = parseProfileInput(key, raw);
	const [lo, hi] = PROFILE_RANGE[key];
	const range = key === 'threshold_pace'
		? `${formatProfileValue(key, lo)}~${formatProfileValue(key, hi)}`
		: `${lo}~${hi}${key === 'weekly_km' ? 'km' : 'bpm'}`;
	if (v === null) return { value: null, error: null };
	if (v === undefined) return { value: null, error: key === 'threshold_pace' ? '페이스는 5:30 처럼 분:초로 적어 주세요' : '숫자로 적어 주세요' };
	if (v < lo || v > hi) return { value: null, error: `${PROFILE_LABEL[key]}: ${range} 사이로 적어 주세요` };
	return { value: v, error: null };
}
