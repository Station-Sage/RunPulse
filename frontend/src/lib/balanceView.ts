// Training Balance 표시 문구(순수) — 상태·기준·주석 텍스트, 요약 문장, 표 행. 테스트: tests/balanceView.test.mjs
import type { BalanceAxis, BalanceBasis, BalanceStatus, TrainingBalance } from './types/trainingBalance.ts';

export const STATUS_TEXT: Record<BalanceStatus, string> = { low: '부족', balanced: '균형', high: '과다' };
export const STATUS_MARK: Record<BalanceStatus, string> = { low: '▼', balanced: '', high: '▲' };
export const STATUS_CLASS: Record<BalanceStatus, string> = {
	low: 'text-status-caution',
	balanced: 'text-status-good',
	high: 'text-status-caution'
};
export const BASIS_TEXT: Record<BalanceBasis, string> = {
	plan: '플랜',
	goal: '목표',
	default_rule: '기본 기준',
	personal_peak: '개인 최고',
	personal_baseline: '개인 60일 평소'
};
export const NOTE_TEXT: Record<string, string> = {
	zone_boundary_vdot: '이지·품질 구간 경계는 VDOT 기반 페이스라, VDOT 가 낮게 잡히면 품질이 많게 집계돼요.',
	quality_includes_races: '품질 강도에는 대회 기록도 포함돼요.',
	long_run_includes_races: '롱런은 최근 12주 최장 1회 값이라 하프 등 대회도 롱런으로 잡혀요.',
	volume_personal_peak: '플랜이 없어 볼륨 목표는 최근 26주 개인 최고 지속 볼륨이에요.',
	default_rule_assumed: '기본 기준(80/20 강도, 거리별 롱런)은 일반 권장치를 가정한 값이에요.'
};
export const COLLECTING = '데이터 수집 중';

export function statusText(s: BalanceStatus | null): string {
	return s ? STATUS_TEXT[s] : COLLECTING;
}

export function basisText(b: BalanceBasis | null): string {
	return b ? BASIS_TEXT[b] : '—';
}

/** 값 표시: 단위별 자릿수. 회복(기준선 대비)은 배수 대신 % 로. */
export function formatValue(v: number | null, axis: Pick<BalanceAxis, 'key' | 'unit'>): string {
	if (v == null) return '—';
	if (axis.key === 'recovery') return `${Math.round(v * 100)}%`;
	if (axis.key === 'load') return v.toFixed(2);
	if (axis.unit === '%') return `${v.toFixed(1)}%`;
	return `${v.toFixed(1)} ${axis.unit}`;
}

export function formatScore(s: number | null): string {
	return s == null ? '—' : String(Math.round(s));
}

/** 카드·figcaption 요약 한 줄: "품질 강도 부족, 나머지 균형". */
export function summarySentence(axes: BalanceAxis[]): string {
	const scored = axes.filter((a) => a.status != null);
	if (scored.length === 0) return COLLECTING;
	const off = scored.filter((a) => a.status !== 'balanced');
	const missing = axes.length - scored.length;
	const tail = missing > 0 ? ` (${missing}개 축 ${COLLECTING})` : '';
	if (off.length === 0) return `모든 축 균형${tail}`;
	const parts = off.map((a) => `${a.label} ${STATUS_TEXT[a.status as BalanceStatus]}`);
	const rest = scored.length > off.length ? ', 나머지 균형' : '';
	return `${parts.join(', ')}${rest}${tail}`;
}

export interface BalanceRow {
	key: string;
	label: string;
	actual: string;
	target: string;
	basis: string;
	score: string;
	status: string;
	statusClass: string;
	mark: string;
	compare: string;
	reason: string | null;
	stale: boolean;
}

export function tableRows(d: TrainingBalance): BalanceRow[] {
	const prev = new Map((d.compare?.axes ?? []).map((a) => [a.key, a.score]));
	return d.axes.map((a) => ({
		key: a.key,
		label: a.label,
		actual: formatValue(a.actual, a),
		target: formatValue(a.target, a),
		basis: basisText(a.basis),
		score: formatScore(a.score),
		status: statusText(a.status),
		statusClass: a.status ? STATUS_CLASS[a.status] : 'text-fg-muted',
		mark: a.status ? STATUS_MARK[a.status] : '',
		compare: formatScore(prev.get(a.key) ?? null),
		reason: a.score == null ? (a.reason_text ?? COLLECTING) : null,
		stale: a.stale
	}));
}

/** 표 하단 주석: 서버 notes + 기본 기준을 쓴 축이 있으면 가정 안내. */
export function noteTexts(d: TrainingBalance): string[] {
	const codes = [...d.notes];
	if (d.axes.some((a) => a.basis === 'default_rule' && a.score != null)) codes.push('default_rule_assumed');
	return codes.map((c) => NOTE_TEXT[c]).filter((t): t is string => !!t);
}

/** 상세 링크·로더용 ?date= 파싱. YYYY-MM-DD 가 아니면 null(오늘). */
export function parseDateParam(raw: string | null): string | null {
	return raw && /^\d{4}-\d{2}-\d{2}$/.test(raw) ? raw : null;
}
