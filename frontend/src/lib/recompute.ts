// 재계산 결과 표시 헬퍼 — 전후 값·변화량 포맷, 진행률.
import type { BeforeAfterRow, RecomputeJob } from '$lib/api/data';

export function formatMetric(slug: string, v: number | null): string {
	if (v == null) return '—';
	if (slug === 'marathon') {
		const h = Math.floor(v / 3600);
		const m = Math.floor((v % 3600) / 60);
		const s = Math.round(v % 60);
		return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
	}
	return String(Math.round(v * 10) / 10);
}

export function formatDelta(row: BeforeAfterRow): string {
	if (row.status === 'unchanged') return '변화 없음';
	if (row.status === 'new') return '새로 계산됨';
	if (row.status === 'lost') return '값 없음';
	if (row.status === 'unavailable' || row.delta == null) return '데이터 부족';
	const sign = row.delta > 0 ? '+' : row.delta < 0 ? '−' : '';
	const abs = Math.abs(row.delta);
	return row.slug === 'marathon' ? `${sign}${Math.round(abs)}초` : `${sign}${Math.round(abs * 10) / 10}`;
}

export function progressPct(job: Pick<RecomputeJob, 'progress'>): number {
	const { done, total } = job.progress;
	return total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
}
