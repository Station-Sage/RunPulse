import test from 'node:test';
import assert from 'node:assert/strict';
import { specialTitle, TAPER_TOKEN } from '../src/lib/drillSpecial.ts';

test('specialTitle: 등록 토큰은 제목, 미등록은 null', () => {
	assert.equal(specialTitle(TAPER_TOKEN), '레이스 아침 폼');
	assert.equal(specialTitle('x.unknown'), null);
});
