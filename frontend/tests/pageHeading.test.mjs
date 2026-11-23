import test from 'node:test';
import assert from 'node:assert/strict';
import { pageHeading } from '../src/lib/a11y/pageHeading.ts';

const STATES = ['ok', 'empty', 'failed'];

test('자식이 소유한 상태는 null(위임)', () => {
	assert.equal(pageHeading('ok', '활동 상세', ['ok']), null);
	assert.equal(pageHeading('empty', '활동 상세', ['ok', 'empty']), null);
});

test('자식이 소유하지 않은 상태는 제목을 돌려준다', () => {
	assert.equal(pageHeading('failed', '활동 상세', ['ok']), '활동 상세');
	assert.equal(pageHeading('empty', 'Today', ['ok']), 'Today');
});

test('childOwns 가 비면 모든 상태에서 제목', () => {
	for (const s of STATES) assert.equal(pageHeading(s, 'Today', []), 'Today');
});

test('3 상태 × childOwns 전 조합: includes 여부와 일치', () => {
	const subsets = [[], ['ok'], ['empty'], ['failed'], ['ok', 'empty'], ['ok', 'failed'], ['empty', 'failed'], STATES];
	for (const owns of subsets) {
		for (const s of STATES) {
			assert.equal(pageHeading(s, 'T', owns), owns.includes(s) ? null : 'T');
		}
	}
});
