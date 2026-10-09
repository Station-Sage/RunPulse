// 재계획 화면 순수 로직 (ADR-035 부록 R, DESIGN-PLAN-A6-REPLAN-UI).
import type { ReplanBasis, ReplanParams, ReplanPreview, ReplanRowRef, ReplanWeek } from '$lib/types';

export interface MergedWeek {
	week_start: string;
	label: string;
	before: number | null;
	after: number | null;
	delta: number | null;
	isRace: boolean;
}

const DOW = ['일', '월', '화', '수', '목', '금', '토'];

function md(iso: string): string {
	return `${iso.slice(5, 7)}/${iso.slice(8, 10)}`;
}

function dow(iso: string): string {
	return DOW[new Date(iso + 'T00:00:00Z').getUTCDay()];
}

export function mergeWeeks(before: ReplanWeek[], after: ReplanWeek[]): MergedWeek[] {
	const b = new Map(before.map((w) => [w.week_start, w.planned_km]));
	const a = new Map(after.map((w) => [w.week_start, w.planned_km]));
	const keys = [...new Set([...b.keys(), ...a.keys()])].sort();
	return keys.map((k, i) => {
		const bv = b.get(k) ?? null;
		const av = a.get(k) ?? null;
		return {
			week_start: k,
			label: `${md(k)} 주`,
			before: bv,
			after: av,
			delta: bv != null && av != null ? av - bv : null,
			isRace: i === keys.length - 1
		};
	});
}

export function deltaText(d: number | null): string {
	if (d == null) return '—';
	const r = Math.round(d);
	if (Math.abs(d) < 0.5 || r === 0) return '=';
	return r < 0 ? `−${-r}` : `+${r}`;
}

export function collapseWeeks(
	rows: MergedWeek[],
	n = 4,
	expanded = false
): { shown: MergedWeek[]; hiddenCount: number } {
	if (expanded || rows.length <= n) return { shown: rows, hiddenCount: 0 };
	const head = rows.slice(0, n);
	const last = rows[rows.length - 1];
	if (head.includes(last)) return { shown: head, hiddenCount: rows.length - n };
	return { shown: [...head, last], hiddenCount: rows.length - n - 1 };
}

export function anchorLabel(anchor: string): string {
	return `${md(anchor)}(${dow(anchor)})`;
}

export function undoUntilLabel(anchor: string): string {
	const d = new Date(anchor + 'T00:00:00Z');
	d.setUTCDate(d.getUTCDate() - 1);
	const iso = d.toISOString().slice(0, 10);
	return `${md(iso)}(${dow(iso)})`;
}

export function canUndo(anchor: string, today: string): boolean {
	return today < anchor;
}

export function replanSummary(p: ReplanPreview): string {
	const m = mergeWeeks(p.before, p.after);
	if (p.before.length === 0) return `대회 주까지 ${p.after.length}주 일정을 새로 넣어요.`;
	const first = m[0];
	const d = first.delta ?? 0;
	let s = `${anchorLabel(p.anchor_monday)}부터 `;
	if (Math.abs(d) < 1) s += '첫 주는 비슷한 거리로 시작하고';
	else s += d < 0 ? `첫 주는 ${first.after}km로 낮춰 시작하고` : `첫 주는 ${first.after}km로 올려 시작하고`;
	const maxB = Math.max(...p.before.map((w) => w.planned_km));
	const maxA = Math.max(0, ...p.after.map((w) => w.planned_km));
	if (Math.round(maxB) !== Math.round(maxA)) s += `, 가장 많은 주는 ${Math.round(maxB)}→${Math.round(maxA)}km로`;
	return `${s} 대회 주까지 다시 짜요.`;
}

export interface RawInputs {
	weekly: string;
	long: string;
	target: string;
}

export type TargetParse = number | null | 'invalid';

export function parseTargetTime(s: string): TargetParse {
	const t = s.trim();
	if (!t) return null;
	const parts = t.split(':');
	if (parts.length < 2 || parts.length > 3 || parts.some((x) => !/^\d{1,2}$/.test(x))) return 'invalid';
	const n = parts.map(Number);
	const sec = parts.length === 3 ? n[0] * 3600 + n[1] * 60 + n[2] : n[0] * 60 + n[1];
	if (n.slice(-2).some((x) => x > 59) || sec <= 0) return 'invalid';
	return sec;
}

function parsePositive(s: string): number | null | 'invalid' {
	const t = s.trim();
	if (!t) return null;
	const v = Number(t.replace(',', '.'));
	return Number.isFinite(v) && v > 0 ? v : 'invalid';
}

export function parseReplanInputs(raw: RawInputs): {
	params: ReplanParams;
	errors: Partial<Record<keyof RawInputs, string>>;
	warnings: string[];
} {
	const params: ReplanParams = {};
	const errors: Partial<Record<keyof RawInputs, string>> = {};
	const warnings: string[] = [];
	const w = parsePositive(raw.weekly);
	const l = parsePositive(raw.long);
	const t = parseTargetTime(raw.target);
	if (w === 'invalid') errors.weekly = '0보다 큰 숫자를 넣어 주세요.';
	else if (w != null) params.recent_weekly_km = w;
	if (l === 'invalid') errors.long = '0보다 큰 숫자를 넣어 주세요.';
	else if (l != null) params.recent_long_km = l;
	if (t === 'invalid') errors.target = '1:45:00 또는 45:30 형식으로 넣어 주세요.';
	else if (t != null) params.target_time_sec = t;
	if (params.recent_weekly_km && params.recent_weekly_km > 200) warnings.push('주간 거리가 200km보다 커요. 맞는지 확인해 주세요.');
	if (params.recent_long_km && params.recent_long_km > 50) warnings.push('가장 긴 러닝이 50km보다 커요. 맞는지 확인해 주세요.');
	if (params.recent_weekly_km && params.recent_long_km && params.recent_long_km > params.recent_weekly_km)
		warnings.push('가장 긴 러닝이 주간 거리보다 길어요. 맞는지 확인해 주세요.');
	return { params, errors, warnings };
}

export function replanQuery(p: ReplanParams): string {
	const q = new URLSearchParams();
	if (p.recent_weekly_km != null) q.set('recent_weekly_km', String(p.recent_weekly_km));
	if (p.recent_long_km != null) q.set('recent_long_km', String(p.recent_long_km));
	if (p.target_time_sec != null) q.set('target_time_sec', String(p.target_time_sec));
	return q.toString();
}

export function canApply(s: { preview: ReplanPreview | null; dirty: boolean; busy: boolean; hasError: boolean }): boolean {
	return s.preview != null && !s.dirty && !s.busy && !s.hasError;
}

function dateList(dates: string[]): string {
	const shown = dates.slice(0, 3).map(md).join(', ');
	return dates.length > 3 ? `${shown} 외 ${dates.length - 3}개` : shown;
}

export function externalNotice(ext: ReplanRowRef[]): string | null {
	if (!ext.length) return null;
	return `Garmin 워치로 보낸 세션 ${ext.length}개(${dateList(ext.map((e) => e.date))})는 자동으로 지울 수 없어요. 적용 후 Garmin Connect 캘린더에서 그 날짜의 운동을 지워 주세요.`;
}

export function preservedNotice(rows: ReplanRowRef[]): string | null {
	if (!rows.length) return null;
	return `기록이 남은 세션 ${rows.length}개는 그대로 둬요(${dateList(rows.map((r) => r.date))}).`;
}

export function skippedNotice(dates: string[]): string | null {
	if (!dates.length) return null;
	return `${dateList(dates)}에는 기존 세션이 남아 있어 새 세션을 넣지 않았어요.`;
}

export type ErrorAction = 'retry' | 'repreview' | 'newGoal' | 'plan' | 'back' | null;
export type Phase = 'preview' | 'apply' | 'undo';

export function replanErrorView(
	err: { status?: number; code?: string } | null,
	phase: Phase
): { text: string; action: ErrorAction; field?: keyof RawInputs } {
	const status = err?.status;
	const code = err?.code;
	if (status === 404 && code === 'NO_GOAL') {
		if (phase === 'undo') return { text: '되돌릴 재계획 기록을 찾지 못했어요. 지금 일정은 그대로예요.', action: 'plan' };
		return { text: '대회일이 있는 목표가 없어요. 다시 맞출 일정이 없어서 지금은 쓸 수 없어요.', action: 'newGoal' };
	}
	if (status === 409 && code === 'RACE_WEEK')
		return { text: '이번 주가 대회 주라 다시 짤 남은 주가 없어요. 계획은 그대로예요.', action: 'back' };
	if (status === 409 && code === 'CONFLICT')
		return { text: '미리보기 뒤에 날짜가 바뀌어 시작 주가 달라졌어요. 아직 바뀐 것은 없어요.', action: 'repreview' };
	if (status === 409 && code === 'REPLAN_LOCKED')
		return { text: '새 일정이 이미 시작됐거나 그 뒤에 기록이 생겨서 되돌릴 수 없어요. 지금 일정은 그대로예요.', action: 'repreview' };
	if (status === 400) return { text: '0보다 큰 숫자를 넣어 주세요.', action: null };
	if (status === 503) return { text: '데이터를 읽지 못했어요. 계획은 바뀌지 않았어요.', action: 'retry' };
	if (phase === 'preview') return { text: '미리보기를 불러오지 못했어요. 계획은 바뀌지 않았어요.', action: 'retry' };
	return { text: '응답을 받지 못했어요. 반영됐는지 계획 화면에서 확인해 주세요.', action: 'plan' };
}

export type StartState = 'A' | 'B' | 'C' | 'D';

const MIN_WEEK_KM = 12;

// 최근 4주 기록 유무로 시작점 상태 결정: A 충분 / B 적음 / C 공백(더 이전 기록 있음) / D 기록 없음.
export function startState(b: Pick<ReplanBasis, 'km4' | 'avg16'>): StartState {
	if (b.km4 >= MIN_WEEK_KM) return 'A';
	if (b.km4 > 0) return 'B';
	return b.avg16 > 0 ? 'C' : 'D';
}

export function inputFields(s: StartState): { weekly: boolean; long: boolean; open: boolean } {
	const show = s === 'C' || s === 'D';
	return { weekly: show, long: show, open: s === 'D' };
}

export function startCardText(p: ReplanPreview): string {
	const km = Math.round(p.start_km);
	const k4 = Math.round(p.basis.km4);
	switch (p.start_source) {
		case 'history':
			return km === k4 ? `첫 주 ${km}km — 최근 4주 평균 ${k4}km 그대로` : `첫 주 ${km}km — 최근 4주 평균 ${k4}km 기준`;
		case 'floor':
			return `첫 주 ${km}km — 최근 4주 평균이 ${k4}km로 적어서 ${km}km부터 시작해요`;
		case 'user':
			return `첫 주 ${km}km — 입력한 값 기준`;
		case 'avg16':
			return `첫 주 ${km}km — 최근 4주 기록이 없어 16주 평균의 60%로 잡았어요`;
		default:
			return `첫 주 ${km}km — 기록이 없어 거리별 기본값으로 잡았어요`;
	}
}

export function startSourceText(p: ReplanPreview): string {
	const km = Math.round(p.start_km);
	const label: Record<ReplanPreview['start_source'], string> = {
		history: '최근 4주 기록',
		floor: '최소 시작 거리(최근 기록이 적음)',
		user: '입력한 값',
		avg16: '최근 16주 평균의 60%',
		default: '거리별 기본값'
	};
	return `시작 주간 ${km}km · ${label[p.start_source]} 기준`;
}

export function fmtTarget(sec: number): string {
	const h = Math.floor(sec / 3600);
	const m = Math.floor((sec % 3600) / 60);
	const s = sec % 60;
	const mm = String(m).padStart(2, '0');
	return h > 0 ? `${h}:${mm}:${String(s).padStart(2, '0')}` : `${m}:${String(s).padStart(2, '0')}`;
}

export function targetChangeText(goalSec: number | null, newSec: number | null): string | null {
	if (newSec == null || newSec === goalSec) return null;
	return goalSec == null ? `목표 ${fmtTarget(newSec)} 기준으로 다시 짜요.` : `목표 ${fmtTarget(goalSec)} → ${fmtTarget(newSec)} 기준으로 다시 짜요.`;
}
