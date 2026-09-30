// Coach 답변 근거 v2 순수 함수 — 칩 노출 분할, 투영 문구, drift 배너, D2 스냅샷 줄(30-coach-chat design §4.4·§7.3).
import type { AnswerEvidence } from '$lib/types';

export const MAX_VISIBLE = 3;
export const PROJECTION_METRIC = 'race_form_projection';

/** pinned(체크인)는 항상 보이고, 나머지는 순서대로 채워 max개까지. 나머지는 hidden. */
export function splitVisible(items: AnswerEvidence[], max = MAX_VISIBLE) {
	const pinned = items.filter((i) => i.pinned);
	let room = Math.max(max - pinned.length, 0);
	const visible: AnswerEvidence[] = [];
	const hidden: AnswerEvidence[] = [];
	for (const it of items) {
		if (it.pinned) visible.push(it);
		else if (room > 0) {
			visible.push(it);
			room -= 1;
		} else hidden.push(it);
	}
	return { visible, hidden };
}

function signed(v: number | string | null): string {
	if (typeof v !== 'number') return String(v ?? '');
	const n = Math.abs(v) >= 10 ? Math.round(v) : Math.round(v * 10) / 10;
	return n > 0 ? `+${n}` : String(n).replace('-', '−');
}

// 스냅샷·drift 문구는 소수 1자리로 정확히(−10.7), 유니코드 마이너스로 통일.
function exact(v: number | string | null | undefined): string {
	if (typeof v === 'number') return (Math.round(v * 10) / 10).toString().replace('-', '−');
	return String(v ?? '').replace('-', '−');
}

/** 투영값은 단정하지 않는다("계획대로 가면 … 약 +25"). 나머지는 서버 라벨 그대로. */
export function chipLabel(ev: AnswerEvidence): string {
	if (ev.metric === PROJECTION_METRIC && typeof ev.value === 'number') {
		return `계획대로 가면 레이스 아침 폼 약 ${signed(ev.value)}`;
	}
	return ev.label;
}

export type ChipTarget = 'drill' | 'race' | 'none';

/** legacy·drill 없는 근거는 InfoTag(none), 투영은 레이스 허브(x.taper D2 도입 전 목적지). */
export function chipTarget(ev: AnswerEvidence): ChipTarget {
	if (ev.role === 'legacy') return 'none';
	if (ev.metric === PROJECTION_METRIC) return 'race';
	return ev.drill ? 'drill' : 'none';
}

export function driftItems(items: AnswerEvidence[] | undefined): AnswerEvidence[] {
	return (items ?? []).filter((i) => i.drifted && i.current);
}

/** 답변 하단 배너 문구 — 값 변화가 있는 근거가 없으면 null. */
export function driftText(items: AnswerEvidence[] | undefined): string | null {
	const d = driftItems(items);
	if (d.length === 0) return null;
	const parts = d.slice(0, 2).map((i) => `${i.status_label ?? i.metric.toUpperCase()} ${exact(i.snapshot?.value)} → ${exact(i.current!.display)}`);
	const more = d.length > 2 ? ` 외 ${d.length - 2}건` : '';
	return `답변 이후 데이터가 바뀌었어요 · ${parts.join(', ')}${more}`;
}

function stamp(iso: string | null | undefined): string {
	const m = /^\d{4}-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/.exec(iso ?? '');
	return m ? `${Number(m[1])}/${Number(m[2])} ${m[3]}:${m[4]}` : '';
}

/** D2 스냅샷 줄 — 답변 칩에서 열었을 때만. 값이 같으면 한 줄, 다르면 변화 안내를 함께. */
export function snapshotLine(ev: AnswerEvidence): { text: string; changed: boolean } | null {
	const s = ev.snapshot;
	if (!s || s.value == null) return null;
	const meta = (at: string | null, ver: string | null, verb: string) =>
		[[stamp(at), verb].filter(Boolean).join(' '), ver].filter(Boolean).join(' · ');
	const then = `답변 당시 ${exact(s.value)}${meta(s.computed_at, s.version, '계산') ? ` (${meta(s.computed_at, s.version, '계산')})` : ''}`;
	const cur = ev.current;
	if (!cur || !ev.drifted) return { text: then, changed: false };
	const now = `현재 ${exact(cur.display)} (${meta(cur.computed_at, cur.version, '재계산')})`;
	return { text: `${then} → ${now}`, changed: true };
}
