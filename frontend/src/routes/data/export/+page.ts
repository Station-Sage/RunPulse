// Data › 내보내기: 아카이브 이력.
import { getCalendarFeed, type CalendarFeed } from '$lib/api/calendarFeed';
import { getExports, type ExportItem } from '$lib/api/data';

export interface ExportPageData {
	history: ExportItem[] | null;
	feed: CalendarFeed | null;
}

export async function load(): Promise<ExportPageData> {
	const [history, feed] = await Promise.all([
		getExports().catch(() => null),
		getCalendarFeed().catch(() => null)
	]);
	return { history, feed };
}
