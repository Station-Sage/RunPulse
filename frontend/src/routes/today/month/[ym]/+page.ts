export interface MonthPageData {
	year: number;
	month: number;
}

// `/today/month/2026-10` — 형식이 틀리면 이번 달로 폴백한다.
export function load({ params }: { params: { ym: string } }): MonthPageData {
	const m = /^(\d{4})-(\d{2})$/.exec(params.ym);
	const now = new Date();
	if (m && +m[2] >= 1 && +m[2] <= 12) return { year: +m[1], month: +m[2] };
	return { year: now.getFullYear(), month: now.getMonth() + 1 };
}
