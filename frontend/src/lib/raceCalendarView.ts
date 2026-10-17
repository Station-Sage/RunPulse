// 대회 캘린더 표시 규칙 — 칩·D-day·거리 (RC §2.4). 서버 판정(needs_review·goal_linked)을 그대로 쓴다.
import type { RaceRow, RaceView } from '$lib/api/raceCalendar';

export function dDay(raceDate: string, today: string): number {
	return Math.round((Date.parse(raceDate) - Date.parse(today)) / 86_400_000);
}

export function dDayLabel(raceDate: string, today: string): string {
	const d = dDay(raceDate, today);
	return d === 0 ? 'D-DAY' : d > 0 ? `D-${d}` : `D+${-d}`;
}

export function chipOf(r: RaceRow, goalLinked: boolean): string {
	if (r.status === 'cancelled') return '취소됨';
	if (r.status === 'done') return '결과 연결';
	if (goalLinked) return '목표 대회';
	if (r.adapt_choice === 'adapt') return r.plan_state === 'stale' ? '변경 후 미반영' : '반영됨';
	if (r.adapt_choice === 'no_adapt') return '조정 안 함';
	return r.adapt_choice === 'later' ? '나중에' : '질문 대기';
}

export function kmLabel(km: number): string {
	return `${Number.isInteger(km) ? km : km.toFixed(km > 40 ? 3 : 1).replace(/0+$/, '')}km`;
}

export function goalLine(r: RaceRow): string {
	if (!r.goal_type) return '';
	if (r.goal_type === 'finish') return '완주';
	if (r.goal_type === 'pb') return 'PB 갱신';
	const s = r.goal_value ?? 0;
	const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
	return h ? `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}` : `${m}:${String(sec).padStart(2, '0')}`;
}

export function asView(r: RaceRow, needsReview: boolean, goalLinked: boolean): RaceView {
	return { ...r, needs_review: needsReview, goal_linked: goalLinked };
}
