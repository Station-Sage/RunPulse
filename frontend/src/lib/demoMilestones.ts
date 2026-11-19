// /demo 마일스톤 응답 — 스냅샷의 전체 이력(`/library/milestones`) 한 벌에서 종류 필터·커서·건수를 서버와 같은 규칙으로 잘라 준다(ADR-057).
// 스냅샷은 정확한 키만 담으므로, 칩·'더 보기'·Today 패널처럼 쿼리가 달라지는 요청은 여기서 만든다.

export const MILESTONE_BASE_KEY = '/library/milestones';

interface Entry {
	id: number;
	type: string;
	date: string;
	[k: string]: unknown;
}
interface History {
	items: Entry[];
	next_before: string | null;
	type_counts: { type: string; count: number }[];
}

const TYPE = /^[a-z_]{1,32}$/;
const CURSOR = /^(\d{4}-\d{2}-\d{2}):(\d+)$/;
const invalid = () => ({ status: 400, body: { error: { code: 'INVALID_PARAM', message: 'type·before·limit 형식이 올바르지 않습니다.' } } });

function base(snap: Record<string, unknown>): History | null {
	const hit = snap[MILESTONE_BASE_KEY] as { data?: History } | undefined;
	return hit?.data ?? null;
}

/** 서버 list_milestones 와 같은 규칙 — 최신순(date desc, id desc), type=a,b 필터, before='날짜:id' 커서, limit 1..100(기본 50). */
export function pageHistory(all: History, q: URLSearchParams): { status: number; body: unknown } {
	const rawTypes = q.get('type');
	const types = rawTypes ? rawTypes.split(',').map((t) => t.trim()).filter(Boolean) : [];
	if (types.some((t) => !TYPE.test(t))) return invalid();
	const rawBefore = q.get('before');
	const m = rawBefore ? CURSOR.exec(rawBefore) : null;
	if (rawBefore && !m) return invalid();
	const limit = Number(q.get('limit') ?? 50);
	if (!Number.isInteger(limit) || limit < 1 || limit > 100) return invalid();
	const sorted = [...all.items].sort((a, b) => (a.date === b.date ? b.id - a.id : a.date < b.date ? 1 : -1));
	const rows = sorted.filter(
		(r) =>
			(!types.length || types.includes(r.type)) &&
			(!m || r.date < m[1] || (r.date === m[1] && r.id < Number(m[2])))
	);
	const items = rows.slice(0, limit);
	const last = items[items.length - 1];
	const next_before = rows.length > limit && last ? `${last.date}:${last.id}` : null;
	return { status: 200, body: { data: { items, next_before, type_counts: all.type_counts } } };
}

/** 스냅샷에 정확한 키가 없을 때 마일스톤 요청을 만들어 준다. 해당 없으면 null. */
export function demoMilestoneResponse(key: string, snap: Record<string, unknown>): { status: number; body: unknown } | null {
	const [path, qs] = key.split('?');
	if (path !== MILESTONE_BASE_KEY && path !== '/today/milestones') return null;
	const all = base(snap);
	if (!all) return null;
	const q = new URLSearchParams(qs ?? '');
	if (path === MILESTONE_BASE_KEY) return pageHistory(all, q);
	// Today 패널 — 최근 N건(기본 10)
	const page = pageHistory(all, new URLSearchParams({ limit: q.get('limit') ?? '10' }));
	const items = (page.body as { data: History }).data.items;
	return { status: 200, body: { data: { milestones: items } } };
}
