// 캘린더 구독 주소 API — design ICS-SUBSCRIBE §6.
import { ApiError, apiFetch } from './client';

export interface CalendarFeed {
	enabled: boolean;
	refresh_hint_hours: number;
	contents: string[];
	excluded: string[];
	url?: string | null;
	webcal_url?: string | null;
	revealable?: boolean;
	created_at?: string | null;
	last_access_at?: string | null;
	last_client?: string | null;
}

export const getCalendarFeed = () => apiFetch<CalendarFeed>('/data/calendar-feed');

// POST는 자동 재시도하지 않는다. rotate=true면 기존 주소가 즉시 무효가 된다.
export const issueCalendarFeed = (rotate = false) =>
	apiFetch<CalendarFeed>('/data/calendar-feed', { method: 'POST', body: JSON.stringify({ rotate }) });

// 204 No Content라 apiFetch(JSON 파싱)를 쓰지 않는다. 멱등.
export async function revokeCalendarFeed(): Promise<void> {
	const res = await fetch('/api/v1/data/calendar-feed', { method: 'DELETE' });
	if (!res.ok) throw new ApiError(res.status, {});
}
