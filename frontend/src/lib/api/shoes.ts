// 신발 관리 v2 API (V2-SHOES) — /api/v1/shoes* + 활동 신발 배정. 오류는 ApiError(code, message)로 온다.
import { apiFetch } from './client';
import type { ActivitySummary } from '$lib/types';

export type ShoeCategory = 'daily' | 'tempo' | 'race' | 'trail' | 'other';
export type ShoeStatus = 'ok' | 'soon' | 'replace' | 'retired';
export type ShoeKind = 'road' | 'trail' | 'treadmill';
export type ShoeMethod = 'manual' | 'source' | 'rule' | 'none';

export interface Shoe {
	id: number;
	name: string;
	brand: string | null;
	model: string | null;
	category: ShoeCategory;
	category_label: string;
	start_date: string | null;
	initial_km: number;
	retire_km_custom: number | null;
	retire_km: number;
	default_for: ShoeKind | null;
	default_since: string | null;
	retired_at: string | null;
	origin: 'manual' | 'gear';
	notes: string | null;
	mileage_km: number;
	activity_count: number;
	last_used: string | null;
	status: ShoeStatus;
	remaining_km: number | null;
	message: string | null;
	note: string | null;
}

export interface GearSuggestion {
	name: string;
	sources: string[];
	gear_ids: number[];
	total_km: number;
}

export interface ShoeList {
	shoes: Shoe[];
	retired_count: number;
	unassigned_count: number;
	headline: string | null;
	suggestions: GearSuggestion[];
}

export interface ShoeDetail extends Shoe {
	breakdown: { initial_km: number; assigned_km: number; by_method: { manual: number; source: number; rule: number } };
	sources: { gear_id: number; source: string; name: string | null; total_km: number }[];
	monthly_km: { month: string; km: number }[];
	conflict_count: number;
}

export interface ConflictSource {
	source: string;
	shoe_id: number;
	name: string | null;
}

export interface ShoeActivity extends ActivitySummary {
	method: ShoeMethod;
	method_source: string | null;
	conflict: boolean;
	conflict_sources: ConflictSource[];
}

export interface ShoeActivityPage {
	activities: ShoeActivity[];
	next_cursor: number | null;
	total: number;
}

export interface ActivityShoe {
	id: number | null;
	name: string | null;
	status: ShoeStatus | null;
	method: ShoeMethod;
	source: string | null;
	conflict: boolean;
	conflict_sources: ConflictSource[];
}

// 활동 상세 응답의 신발 칩 필드 — types/index.ts 줄 수 상한(fileSize ratchet) 때문에 여기서 확장한다.
declare module '$lib/types' {
	interface ActivityDetail {
		shoe?: ActivityShoe | null; // 비러닝 null, 러닝 미배정 id=null
	}
}

export interface ShoeInput {
	name?: string;
	brand?: string | null;
	model?: string | null;
	category?: ShoeCategory;
	start_date?: string | null;
	initial_distance_km?: number | null;
	retire_km?: number | null;
	default_for?: ShoeKind | null;
	notes?: string | null;
	retired_at?: string | null;
}

const json = (method: string, body?: unknown): RequestInit => ({
	method,
	body: body === undefined ? undefined : JSON.stringify(body)
});

export const getShoes = (includeRetired = true) =>
	apiFetch<ShoeList>(`/shoes${includeRetired ? '' : '?include_retired=0'}`);
export const getShoe = (id: number) => apiFetch<ShoeDetail>(`/shoes/${id}`);
export const getShoeActivities = (id: number, cursor = 0) =>
	apiFetch<ShoeActivityPage>(`/shoes/${id}/activities?cursor=${cursor}`);
export const getUnassignedRuns = (cursor = 0, limit = 50) =>
	apiFetch<ShoeActivityPage>(`/shoes/unassigned?cursor=${cursor}&limit=${limit}`);
export const getShoeAlert = () =>
	apiFetch<{ alert: { id: number; name: string; message: string } | null }>('/shoes/alert');

export const createShoe = (input: ShoeInput) => apiFetch<ShoeDetail>('/shoes', json('POST', input));
export const updateShoe = (id: number, input: ShoeInput) => apiFetch<ShoeDetail>(`/shoes/${id}`, json('PATCH', input));
export const deleteShoe = (id: number) => apiFetch<{ deleted: number }>(`/shoes/${id}`, json('DELETE'));
export const mergeShoe = (id: number, sourceShoeId: number) =>
	apiFetch<ShoeDetail>(`/shoes/${id}/merge`, json('POST', { source_shoe_id: sourceShoeId }));
export const unlinkGear = (id: number, gearId: number) => apiFetch<ShoeDetail>(`/shoes/${id}/gear/${gearId}`, json('DELETE'));
export const importGear = () => apiFetch<{ created: number; linked: number }>('/shoes/import-gear', json('POST'));
export const assignShoe = (id: number, activityIds: number[]) =>
	apiFetch<{ assigned: number; skipped_non_running: number; skipped_missing: number }>(
		`/shoes/${id}/assign`,
		json('POST', { activity_ids: activityIds })
	);
export const setActivityShoe = (activityId: number, shoeId: number | null) =>
	apiFetch<{ shoe: ActivityShoe | null }>(`/library/activities/${activityId}/shoe`, json('PUT', { shoe_id: shoeId }));
export const resetActivityShoe = (activityId: number) =>
	apiFetch<{ shoe: ActivityShoe | null }>(`/library/activities/${activityId}/shoe`, json('DELETE'));
