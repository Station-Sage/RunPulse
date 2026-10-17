import { invalidate } from '$app/navigation';
import { getRaceZones, type RaceZones } from '$lib/api/raceCalendar';
import { swrLoad } from '$lib/loadCache';

export interface RaceCalendarPageData {
	zones: RaceZones | null;
	failed: boolean;
}

export async function load({ depends }: { depends: (key: string) => void }): Promise<RaceCalendarPageData> {
	depends('app:race-calendar');
	try {
		return { zones: await swrLoad('app:race-calendar', getRaceZones, invalidate), failed: false };
	} catch {
		return { zones: null, failed: true };
	}
}
