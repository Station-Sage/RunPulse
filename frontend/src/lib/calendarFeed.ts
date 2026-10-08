// 캘린더 구독 카드 표시 헬퍼.
import type { CalendarFeed } from '$lib/api/calendarFeed';

export function lastAccessText(feed: CalendarFeed, now: Date = new Date()): string {
	if (!feed.last_access_at) return '아직 캘린더 앱에서 가져간 적이 없어요';
	const mins = Math.floor((now.getTime() - new Date(feed.last_access_at).getTime()) / 60000);
	const when =
		mins < 1 ? '방금' : mins < 60 ? `${mins}분 전` : mins < 1440 ? `${Math.floor(mins / 60)}시간 전` : `${Math.floor(mins / 1440)}일 전`;
	return `마지막 가져감 ${when}${feed.last_client ? ` · ${feed.last_client}` : ''}`;
}

export const googleSubscribeUrl = (webcalUrl: string) =>
	`https://calendar.google.com/calendar/r?cid=${encodeURIComponent(webcalUrl)}`;
