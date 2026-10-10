import test from 'node:test';
import assert from 'node:assert/strict';
import { confirmText, resultText } from '../src/lib/garminCleanup.ts';

test('confirmText 날짜 정렬·개수', () => {
	assert.equal(
		confirmText(['2026-10-16', '2026-10-14']),
		'Garmin 캘린더의 세션 2개(10/14, 10/16)를 삭제해요. 삭제 후에는 되돌리기를 해도 워치 일정은 돌아오지 않아요.'
	);
});

test('resultText 부분 실패', () => {
	assert.equal(resultText({ deleted: 2, missing: 1, failed: [{ date: '2026-10-17', error: 'x' }] }), '3개 지웠어요, 1개는 직접 지워 주세요(10/17).');
	assert.equal(resultText({ deleted: 2, missing: 0, failed: [] }), '2개 정리했어요.');
});
