import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

test('데모 to 파라미터는 내부 경로만 허용하는 정규식을 쓴다', () => {
	const src = readFileSync(new URL('../src/routes/demo/+page.ts', import.meta.url), 'utf8');
	assert.match(src, /searchParams\.get\('to'\)/);
	const re = /^\/[a-z0-9/_-]*$/i;
	assert.ok(re.test('/library/metrics/cirs'));
	assert.ok(!re.test('//evil.com'));
	assert.ok(!re.test('https://evil.com'));
});
