// Garmin 일정 삭제 확인·결과 문구 (DESIGN-PLAN-A6-REPLAN-UI §13.1 D).
import type { GarminCleanupResult } from '$lib/api/plan';

function md(date: string): string {
	const [, m, d] = date.split('-');
	return `${Number(m)}/${Number(d)}`;
}

export function dateList(dates: string[], max = 4): string {
	const s = [...dates].sort().map(md);
	return s.length > max ? `${s.slice(0, max).join(', ')} 외 ${s.length - max}개` : s.join(', ');
}

export function confirmText(dates: string[]): string {
	return `Garmin 캘린더의 세션 ${dates.length}개(${dateList(dates)})를 삭제해요. 삭제 후에는 되돌리기를 해도 워치 일정은 돌아오지 않아요.`;
}

export function resultText(r: GarminCleanupResult): string {
	const ok = r.deleted + r.missing;
	if (!r.failed.length) return `${ok}개 정리했어요.`;
	return `${ok}개 지웠어요, ${r.failed.length}개는 직접 지워 주세요(${dateList(r.failed.map((f) => f.date))}).`;
}
