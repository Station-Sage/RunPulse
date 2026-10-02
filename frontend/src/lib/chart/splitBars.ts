// 스플릿 막대 계산(순수) — 서버 ActivitySplit 기반. ±30s/km 고정 도메인 발산 막대, 21km 초과는 5km 묶음.
import type { ActivitySplit } from '../types/index.ts';

export const SPLIT_DOMAIN_SEC = 30;
export const GROUP_ABOVE_M = 21000;
export const GROUP_KM = 5;

export interface SplitRow extends ActivitySplit {
	label: string;
	segs: number[]; // 이 행이 덮는 원본 idx
}

function rowOf(chunk: ActivitySplit[], label: string): SplitRow {
	const dist = chunk.reduce((s, x) => s + x.dist_m, 0);
	const moving = chunk.reduce((s, x) => s + x.moving_sec, 0);
	const hrSplits = chunk.filter((x) => x.avg_hr != null);
	const hrW = hrSplits.reduce((s, x) => s + x.moving_sec, 0);
	const elev = chunk.filter((x) => x.elev_gain_m != null);
	return {
		idx: chunk[0].idx,
		dist_m: dist,
		moving_sec: moving,
		elapsed_sec: chunk.reduce((s, x) => s + x.elapsed_sec, 0),
		stop_sec: chunk.reduce((s, x) => s + x.stop_sec, 0),
		pace_sec_km: moving > 0 && dist > 0 ? Math.round((moving / (dist / 1000)) * 10) / 10 : null,
		avg_hr:
			hrW > 0 ? Math.round(hrSplits.reduce((s, x) => s + (x.avg_hr as number) * x.moving_sec, 0) / hrW) : null,
		elev_gain_m: elev.length ? Math.round(elev.reduce((s, x) => s + (x.elev_gain_m as number), 0) * 10) / 10 : null,
		partial: chunk.some((x) => x.partial),
		label,
		segs: chunk.map((x) => x.idx)
	};
}

export function buildSplitRows(splits: ActivitySplit[]): SplitRow[] {
	if (splits.length === 0) return [];
	const total = splits.reduce((s, x) => s + x.dist_m, 0);
	if (total <= GROUP_ABOVE_M) {
		return splits.map((s) => rowOf([s], s.partial ? `${(s.dist_m / 1000).toFixed(1)}` : String(s.idx)));
	}
	const rows: SplitRow[] = [];
	for (let i = 0; i < splits.length; i += GROUP_KM) {
		const chunk = splits.slice(i, i + GROUP_KM);
		const a = chunk[0].idx;
		const b = chunk[chunk.length - 1].idx;
		rows.push(rowOf(chunk, a === b ? String(a) : `${a}–${b}`));
	}
	return rows;
}

/** 온전한 구간(partial 제외)의 이동시간 가중 평균 페이스. 없으면 null. */
export function averagePace(rows: SplitRow[]): number | null {
	const full = rows.filter((r) => !r.partial && r.pace_sec_km != null);
	const dist = full.reduce((s, r) => s + r.dist_m, 0);
	const moving = full.reduce((s, r) => s + r.moving_sec, 0);
	return dist > 0 && moving > 0 ? moving / (dist / 1000) : null;
}

/** 평균 대비 편차를 -1..1로(음수=빠름). 도메인 밖이면 clipped. */
export function divergence(pace: number | null, avg: number | null, domain = SPLIT_DOMAIN_SEC) {
	if (pace == null || avg == null) return { frac: 0, clipped: false };
	const raw = (pace - avg) / domain;
	return { frac: Math.max(-1, Math.min(1, raw)), clipped: Math.abs(raw) > 1 };
}

/** 가장 빠른 온전한 행의 인덱스(없으면 -1). */
export function fastestRow(rows: SplitRow[]): number {
	let best = -1;
	rows.forEach((r, i) => {
		if (r.partial || r.pace_sec_km == null) return;
		if (best < 0 || r.pace_sec_km < (rows[best].pace_sec_km as number)) best = i;
	});
	return best;
}
