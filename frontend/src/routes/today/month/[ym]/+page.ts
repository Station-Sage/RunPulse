import { redirect } from '@sveltejs/kit';
import { base } from '$app/paths';
import { normalizeMonthParam } from '$lib/utils/validation';

export interface MonthPageData {
	year: number;
	month: number;
}

// `/today/month/2026-10` — 형식이 틀리거나 미래 달이면 이번 달로 바꾸고, URL 도 정규 표기로 교체한다
// (load 의 redirect 는 클라이언트 내비게이션에서 replaceState 로 동작 — 잘못된 주소가 히스토리에 남지 않는다).
export function load({ params, url }: { params: { ym: string }; url: URL }): MonthPageData {
	const { year, month, ym } = normalizeMonthParam(params.ym);
	if (ym !== params.ym) redirect(307, `${base}/today/month/${ym}${url.search}`);
	return { year, month };
}
