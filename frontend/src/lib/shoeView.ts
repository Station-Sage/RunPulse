// 신발 화면 순수 로직(V2-SHOES) — 상태 색·라벨, 배정 방식 라벨, 정렬, 폼 검증. DOM·Svelte 비의존(node --test 대상).
import { ApiError } from './api/client.ts';
import { classifyFailure, failureMessage } from './loadFailure.ts';
import type { ActivityShoe, Shoe, ShoeCategory, ShoeKind, ShoeMethod, ShoeStatus, ShoeInput } from './api/shoes.ts';

export const CATEGORY_OPTIONS: { value: ShoeCategory; label: string }[] = [
	{ value: 'daily', label: '데일리' },
	{ value: 'tempo', label: '템포·경량' },
	{ value: 'race', label: '레이스(카본)' },
	{ value: 'trail', label: '트레일' },
	{ value: 'other', label: '기타' }
];

export const KIND_OPTIONS: { value: ShoeKind; label: string }[] = [
	{ value: 'road', label: '로드' },
	{ value: 'trail', label: '트레일' },
	{ value: 'treadmill', label: '트레드밀' }
];

const STATUS_META: Record<ShoeStatus, { label: string; bar: string; text: string }> = {
	ok: { label: '충분', bar: 'bg-semantic-green', text: 'text-semantic-green' },
	soon: { label: '교체 준비', bar: 'bg-semantic-amber', text: 'text-semantic-amber' },
	replace: { label: '교체 권장', bar: 'bg-semantic-red', text: 'text-semantic-red' },
	retired: { label: '은퇴', bar: 'bg-fg-muted', text: 'text-fg-muted' }
};

export function statusMeta(status: ShoeStatus | null | undefined) {
	return STATUS_META[status ?? 'ok'] ?? STATUS_META.ok;
}

const SOURCE_LABEL: Record<string, string> = {
	garmin: 'Garmin',
	strava: 'Strava',
	strava_export: 'Strava 파일',
	intervals: 'Intervals.icu',
	runalyze: 'Runalyze'
};

export function sourceLabel(source: string): string {
	return SOURCE_LABEL[source] ?? source;
}

// 배정 방식 태그 — "직접 / Garmin / 기본 규칙". source 는 우선순위 1위 소스 이름을 쓴다.
export function methodLabel(method: ShoeMethod, firstSource?: string | null): string {
	if (method === 'manual') return '직접';
	if (method === 'rule') return '기본 규칙';
	if (method === 'source') return firstSource ? sourceLabel(firstSource) : '소스';
	return '미지정';
}

export function kindLabel(kind: ShoeKind | null | undefined): string | null {
	return KIND_OPTIONS.find((k) => k.value === kind)?.label ?? null;
}

const ORDER: Record<ShoeStatus, number> = { replace: 0, soon: 1, ok: 2, retired: 3 };

// replace → soon → ok, 같은 상태는 최근 사용 순(미사용은 뒤). 서버 정렬과 같은 규칙(재정렬·낙관적 갱신용).
export function sortShoes<T extends Pick<Shoe, 'status' | 'last_used'>>(shoes: T[]): T[] {
	return [...shoes].sort((a, b) => {
		const d = ORDER[a.status] - ORDER[b.status];
		if (d) return d;
		return (b.last_used ?? '').localeCompare(a.last_used ?? '');
	});
}

export function wearPercent(mileageKm: number, retireKm: number): number {
	if (!retireKm) return 0;
	return Math.max(0, Math.round((mileageKm / retireKm) * 100));
}

export interface ShoeFormValues {
	name: string;
	brand: string;
	model: string;
	category: ShoeCategory;
	start_date: string;
	initial_km: string;
	retire_km: string;
	default_for: ShoeKind | '';
	notes: string;
}

export function emptyForm(shoe?: Partial<Shoe> | null): ShoeFormValues {
	return {
		name: shoe?.name ?? '',
		brand: shoe?.brand ?? '',
		model: shoe?.model ?? '',
		category: shoe?.category ?? 'daily',
		start_date: shoe?.start_date ?? '',
		initial_km: shoe?.initial_km ? String(shoe.initial_km) : '',
		retire_km: shoe?.retire_km_custom ? String(shoe.retire_km_custom) : '',
		default_for: shoe?.default_for ?? '',
		notes: shoe?.notes ?? ''
	};
}

// 서버 규칙(routes_shoes._FIELDS)과 같은 범위. 오류는 필드별 한국어 문구.
export function validateShoeForm(v: ShoeFormValues): Record<string, string> {
	const err: Record<string, string> = {};
	if (!v.name.trim()) err.name = '이름을 입력해 주세요';
	else if (v.name.trim().length > 60) err.name = '이름은 60자 이하로 입력해 주세요';
	if (v.brand.trim().length > 60) err.brand = '60자 이하로 입력해 주세요';
	if (v.model.trim().length > 60) err.model = '60자 이하로 입력해 주세요';
	if (v.initial_km.trim()) {
		const n = Number(v.initial_km);
		if (!Number.isFinite(n) || n < 0 || n > 3000) err.initial_km = '0~3000 km 사이로 입력해 주세요';
	}
	if (v.retire_km.trim()) {
		const n = Number(v.retire_km);
		if (!Number.isInteger(n) || n < 100 || n > 2000) err.retire_km = '100~2000 km 사이 정수로 입력해 주세요';
	}
	if (v.start_date && !/^\d{4}-\d{2}-\d{2}$/.test(v.start_date)) err.start_date = '날짜 형식이 올바르지 않아요';
	if (v.notes.length > 500) err.notes = '메모는 500자 이하로 입력해 주세요';
	return err;
}

export function formToInput(v: ShoeFormValues): ShoeInput {
	const opt = (s: string) => (s.trim() ? s.trim() : null);
	return {
		name: v.name.trim(),
		brand: opt(v.brand),
		model: opt(v.model),
		category: v.category,
		start_date: v.start_date || null,
		initial_distance_km: v.initial_km.trim() ? Number(v.initial_km) : 0,
		retire_km: v.retire_km.trim() ? Number(v.retire_km) : null,
		default_for: v.default_for || null,
		notes: opt(v.notes)
	};
}

// 쓰기 실패 문구 — 400(규칙 위반)·409(GEAR_LINKED 등)는 서버 문구, 그 외는 공통 failureMessage.
export function shoeWriteError(e: unknown): string {
	if (e instanceof ApiError && (e.status === 400 || e.status === 409)) return e.message;
	return failureMessage(classifyFailure(e).kind);
}

// 활동 상세 칩 문구 — "페가수스 40 (기본 규칙)" / "신발 없음 (직접)" / "신발 미지정". 비러닝(null)은 빈 문자열.
export function shoeChipText(shoe: ActivityShoe | null | undefined): string {
	if (!shoe) return '';
	if (shoe.id == null) return shoe.method === 'manual' ? '신발 없음 (직접)' : '신발 미지정';
	return `${shoe.name} (${methodLabel(shoe.method, shoe.source)})`;
}
