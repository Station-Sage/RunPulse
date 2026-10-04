import test from 'node:test';
import assert from 'node:assert/strict';
import { activityDetailHref } from '../src/lib/activityRow.ts';

test('activityDetailHref appends origin', () => {
	assert.equal(activityDetailHref('/v2', 7, 'list'), '/v2/library/7?from=list');
	assert.equal(activityDetailHref('', 7, 'home'), '/library/7?from=home');
});
