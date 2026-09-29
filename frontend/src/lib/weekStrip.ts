// B5 주간 스트립 순수 헬퍼 — design 10-today §C7 상태 기호. 판정은 서버(week_compliance), 여기선 표기만.
import type { WeekCompliance, WeekDay } from './types/index.ts';

const DOW = ['일', '월', '화', '수', '목', '금', '토'];

export interface DayCell {
	date: string;
	dow: string;
	/** ● 이행 · ◐ 부족 · ○ 놓침 · ⟳ 대체 · ◉ 오늘 · ┄ 휴식 · ◌ 예정 · '' 계획 전 */
	symbol: string;
	label: string;
	title: string;
	/** 예정(점선 외곽)·계획 전(흐림) 스타일 분기용 */
	tone: 'done' | 'partial' | 'missed' | 'upcoming' | 'rest' | 'pre_plan' | 'today';
	linkable: boolean;
}

export function dowOf(date: string): string {
	const [y, m, d] = date.split('-').map(Number);
	return DOW[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
}

export function dayCell(d: WeekDay): DayCell {
	const dow = dowOf(d.date);
	const base = { date: d.date, dow };
	const name = d.title ?? '';
	if (d.state === 'pre_plan') return { ...base, symbol: '', label: '계획 전', title: '계획 시작 전', tone: 'pre_plan', linkable: false };
	if (d.state === 'rest') return { ...base, symbol: '┄', label: '휴식', title: '휴식일', tone: 'rest', linkable: false };
	// 오늘이 아직 예정이면 ◉, 이미 결과가 난 오늘은 결과 기호를 우선한다
	if (d.today && d.state === 'upcoming') return { ...base, symbol: '◉', label: name || '오늘', title: `오늘 · ${name}`, tone: 'today', linkable: true };
	if (d.substituted && d.state !== 'missed') return { ...base, symbol: '⟳', label: name || '대체', title: `${name} · 다른 세션으로 대체`, tone: 'done', linkable: true };
	if (d.state === 'done') return { ...base, symbol: '●', label: name, title: `${name} · 이행`, tone: 'done', linkable: true };
	if (d.state === 'partial') return { ...base, symbol: '◐', label: name, title: `${name} · 부족`, tone: 'partial', linkable: true };
	if (d.state === 'missed') return { ...base, symbol: '○', label: name, title: `${name} · 놓침`, tone: 'missed', linkable: true };
	return { ...base, symbol: '◌', label: name, title: `${name} · 예정`, tone: 'upcoming', linkable: true };
}

export function weekSummary(w: WeekCompliance): string {
	const km = `이번 주 ${w.done_km}/${w.plan_km}km`;
	return w.key_total > 0 ? `${km} · 핵심 ${w.key_done}/${w.key_total}` : km;
}

/** 계획이 없으면(모든 날 workout_type 없음) 스트립 자체를 숨긴다. */
export function hasWeekPlan(w: WeekCompliance | null | undefined): w is WeekCompliance {
	return !!w && w.days.some((d) => !!d.workout_type);
}
