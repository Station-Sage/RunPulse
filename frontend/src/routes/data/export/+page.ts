// Data › 내보내기: 아카이브 이력.
import type { ExportGroup } from '$lib/exportScope';
import { getCalendarFeed, type CalendarFeed } from '$lib/api/calendarFeed';
import { getExportsFull, type ExportItem } from '$lib/api/data';

export interface ExportPageData {
	history: ExportItem[] | null;
	groups: ExportGroup[];
	feed: CalendarFeed | null;
}

export async function load(): Promise<ExportPageData> {
	const [history, feed] = await Promise.all([
		getExportsFull().catch(() => null),
		getCalendarFeed().catch(() => null)
	]);
	return { history: history?.exports ?? null, groups: history?.groups ?? [], feed };
}
