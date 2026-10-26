import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { toQuickInputExisting } from '../src/lib/checkinView.ts';

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
