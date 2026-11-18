import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { checkinSavePayload, checkinUndoPayload, toQuickInputExisting, checkinSummary } from '../src/lib/checkinView.ts';

describe('toQuickInputExisting', () => {
	it('null → undefined', () => assert.equal(toQuickInputExisting(null), undefined));
	it('null 필드는 undefined 로, created_at 은 timestamp 로', () => {
		const r = toQuickInputExisting({ id: 1, input_date: '2026-10-26', input_type: 'x', fatigue: null, pain: null, note: null, activity_id: null, created_at: 't' });
		assert.deepEqual(r, { fatigue: undefined, pain: undefined, note: undefined, timestamp: 't' });
	});
	it('값 유지', () => {
		const r = toQuickInputExisting({ id: 1, input_date: 'd', input_type: 'x', fatigue: 3, pain: 'mild', note: 'n', activity_id: null, created_at: 't' });
		assert.equal(r.fatigue, 3);
		assert.equal(r.note, 'n');
	});
});

describe('checkinSavePayload (T-16)', () => {
	it('비운 통증·메모는 null(지움), 피로 미선택은 키 없음', () => {
		assert.deepEqual(checkinSavePayload(undefined, undefined, '  '), { pain: null, note: null });
	});
	it('값은 그대로, 메모는 앞뒤 공백 제거', () => {
		assert.deepEqual(checkinSavePayload(4, 'mild', ' 무릎 '), { fatigue: 4, pain: 'mild', note: '무릎' });
	});
});

describe('checkinUndoPayload (T-19)', () => {
	it('이전 기록 없음 → 세 값 모두 null', () => {
		assert.deepEqual(checkinUndoPayload(null), { fatigue: null, pain: null, note: null });
	});
	it('이전 기록으로 복원', () => {
		const prev = { id: 1, input_date: 'd', input_type: 'checkin', fatigue: 6, pain: 'none', note: null, activity_id: null, created_at: 't' };
		assert.deepEqual(checkinUndoPayload(prev), { fatigue: 6, pain: 'none', note: null });
	});
});

describe('checkinSummary', () => {
	const row = (o) => ({ id: 1, input_date: 'd', input_type: 'x', fatigue: null, pain: null, note: null, activity_id: null, created_at: 't', ...o });
	it('기록 없음·빈 기록 → null', () => {
		assert.equal(checkinSummary(null), null);
		assert.equal(checkinSummary(row({})), null);
	});
	it('피로·통증 요약', () => assert.equal(checkinSummary(row({ fatigue: 4, pain: 'mild' })), '피로 4 · 통증 경미'));
	it('일부만 있으면 — 표시', () => assert.equal(checkinSummary(row({ pain: 'none' })), '피로 — · 통증 없음'));
});
