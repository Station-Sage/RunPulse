import test from 'node:test';
import assert from 'node:assert/strict';
import { smallDataTodos, evidenceLimitNotice } from '../src/lib/coachSmallData.ts';

const e = (have, req, unlocked) => ({ required_days: req, have_days: have, unlocked, basis: 'load_span' });
const small = { ctl: e(14, 42, false), tsb: e(14, 42, false), cirs: e(14, 28, false), utrs: e(3, 7, false) };
const full = { ctl: e(60, 42, true), tsb: e(60, 42, true), cirs: e(60, 28, true), utrs: e(10, 7, true) };

test('소량 데이터면 할 일 3개, 충분하면 없음', () => {
	assert.equal(smallDataTodos(small).length, 3);
	assert.equal(smallDataTodos(full).length, 0);
	assert.equal(smallDataTodos(null).length, 0);
});
test('한계 문구', () => {
	assert.equal(evidenceLimitNotice(small), '아직 14일치라 추세는 말하기 일러요 (CTL 미산출)');
	assert.equal(evidenceLimitNotice({ ...small, ctl: e(0, 42, false) }), '아직 훈련 기록이 없어 추세는 말하기 일러요 (CTL 미산출)');
	assert.equal(evidenceLimitNotice(full), null);
});
