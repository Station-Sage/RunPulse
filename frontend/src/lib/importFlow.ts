// 가져오기 화면 표시 헬퍼.
import type { ImportKind, ImportPreview } from '$lib/api/data';

const KIND_LABEL: Record<ImportKind, string> = {
	strava_archive: 'Strava 전체 내보내기',
	strava_csv: 'Strava 활동 CSV',
	garmin_csv: 'Garmin 활동 CSV',
	files: 'FIT/GPX/TCX 파일'
};

export const kindLabel = (k: ImportKind): string => KIND_LABEL[k] ?? k;

export function periodText(p: { from: string | null; to: string | null }): string {
	if (!p.from) return '기간 정보 없음';
	const a = p.from.slice(0, 10);
	const b = (p.to ?? p.from).slice(0, 10);
	return a === b ? a : `${a} ~ ${b}`;
}

/** 미리보기 숫자를 사람 말로 한 줄씩 푼다. 0인 항목은 생략. */
export function previewLines(p: ImportPreview): string[] {
	const out = [`${p.recognized}건을 찾았어요`, `기간 ${periodText(p.period)}`];
	out.push(p.new > 0 ? `새로 들어갈 활동 ${p.new}건` : '새로 들어갈 활동이 없어요');
	if (p.duplicates > 0) out.push(`이미 있는 활동 ${p.duplicates}건은 건너뛰어요`);
	if (p.merged > 0) out.push(`다른 소스와 같은 활동으로 합쳐지는 것 ${p.merged}건`);
	if (p.enriched > 0) out.push(`스트림·랩을 채우는 활동 ${p.enriched}건`);
	if (p.errors > 0) out.push(`읽지 못한 항목 ${p.errors}건`);
	return out;
}

export const canCommit = (p: ImportPreview | null): boolean => !!p && (p.new > 0 || p.enriched > 0);
