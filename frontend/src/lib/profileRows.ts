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
		const [m, sec] = s.split(':').map(Number);
		return Number.isFinite(m) && Number.isFinite(sec) && sec >= 0 && sec < 60 ? m * 60 + sec : undefined;
	}
	const n = Number(s);
	return Number.isFinite(n) ? n : undefined;
}
