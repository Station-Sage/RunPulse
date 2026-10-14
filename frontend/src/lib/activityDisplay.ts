// 스포츠 군별 활동 히어로 표시 규칙 (ADR-051 NRA-3/4/5). 서버 `display` 계약을 셀 목록으로 변환한다.
import { formatDuration } from './format.ts';
import type { ActivityDisplay, NarrativeOther } from './types/index.ts';

export interface HeroCell {
	label: string;
	value: string;
	unit: string;
}

function paceText(sec: number): string {
	const t = Math.round(sec);
	return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`;
}

/** 거리 숫자를 보일지 — 근력·기타는 숨김. display 없음(구 응답)은 보임. */
export function showDistance(d: ActivityDisplay | null | undefined): boolean {
	return d ? d.show_distance : true;
}

/** 시간 셀: 이동 시간이 총 시간과 다르면 "이동 / 총" 짝으로. */
export function timeCell(d: ActivityDisplay | null | undefined, durationSec: number | null): HeroCell {
	const moving = d?.times.moving_sec ?? null;
	const elapsed = d?.times.elapsed_sec ?? durationSec;
	if (moving != null && elapsed != null && Math.round(moving) !== Math.round(elapsed) && d?.pace?.basis !== 'elapsed') {
		return { label: '시간 (이동/총)', value: `${formatDuration(moving)} / ${formatDuration(elapsed)}`, unit: '' };
	}
	return { label: '시간', value: elapsed != null ? formatDuration(elapsed) : '—', unit: '' };
}

/** 두 번째 셀: 페이스(/km·/100m) · 속도(km/h) · 없으면 null. */
export function paceCell(d: ActivityDisplay | null | undefined): HeroCell | null {
	if (!d) return null;
	if (d.pace) return { label: '평균 페이스', value: paceText(d.pace.value_sec), unit: d.pace.unit };
	if (d.speed_kmh != null) return { label: '평균 속도', value: d.speed_kmh.toFixed(1), unit: 'km/h' };
	return null;
}

const ALT_LABEL: Record<string, [string, string]> = {
	duration: ['시간', ''],
	avg_hr: ['평균 심박', 'bpm'],
	calories: ['칼로리', 'kcal'],
	sets: ['세트', '세트'],
};

/** 거리·페이스가 없는 군의 대체 셀(NRA-5): 있는 값만, 서버 순서대로. */
export function altCells(d: ActivityDisplay | null | undefined): HeroCell[] {
	if (!d) return [];
	return d.alt_fields.flatMap((f) => {
		const meta = ALT_LABEL[f.key];
		if (!meta) return [];
		const value = f.key === 'duration' ? formatDuration(Number(f.value)) : String(f.value);
		return [{ label: meta[0], value, unit: meta[1] }];
	});
}

/** Today 내러티브의 비러닝 한 줄 — "그 외 수영 1회 · 근력 2회", 없으면 ''. */
export function otherLine(others: NarrativeOther[] | null | undefined): string {
	if (!others || others.length === 0) return '';
	return '그 외 ' + others.map((o) => `${o.label} ${o.count}회`).join(' · ');
}
