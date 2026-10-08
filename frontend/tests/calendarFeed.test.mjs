import { test } from 'node:test';
import assert from 'node:assert/strict';
import { googleSubscribeUrl, lastAccessText } from '../src/lib/calendarFeed.ts';

const base = { enabled: true, refresh_hint_hours: 6, contents: [], excluded: [] };

test('no access yet', () => {
	assert.match(lastAccessText(base), /가져간 적이 없어요/);
});

test('relative time and client', () => {
	const now = new Date('2026-10-08T12:00:00Z');
	const f = { ...base, last_access_at: '2026-10-08T10:00:00Z', last_client: 'Google' };
	assert.equal(lastAccessText(f, now), '마지막 가져감 2시간 전 · Google');
	assert.equal(lastAccessText({ ...f, last_access_at: '2026-10-08T11:59:30Z', last_client: null }, now), '마지막 가져감 방금');
});

test('google url encodes webcal', () => {
	assert.equal(
		googleSubscribeUrl('webcal://h/feeds/cal/t.ics'),
		'https://calendar.google.com/calendar/r?cid=webcal%3A%2F%2Fh%2Ffeeds%2Fcal%2Ft.ics'
	);
});
