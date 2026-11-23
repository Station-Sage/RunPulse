import { test } from 'node:test';
import assert from 'node:assert/strict';
import { navFromPath } from '../src/lib/navFrom.ts';

test('navFromPath — null/undefined/url:null 은 null', () => {
	assert.equal(navFromPath(null), null);
	assert.equal(navFromPath(undefined), null);
	assert.equal(navFromPath({ url: null }), null);
	assert.equal(navFromPath({}), null);
});

test('navFromPath — 정상 URL 은 pathname', () => {
	assert.equal(navFromPath({ url: new URL('http://localhost/v2/today?x=1') }), '/v2/today');
});
