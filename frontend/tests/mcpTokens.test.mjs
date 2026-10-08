import { test } from 'node:test';
import assert from 'node:assert/strict';
import { expiryText, lastUsedText, mcpEndpoint } from '../src/lib/mcpTokens.ts';

const t = { token_id: 'mt_1', label: 'x', last4: 'abcd', created_at: '2026-10-01 00:00:00',
	expires_at: '2026-10-11 00:00:00', revoked_at: null, last_used_at: null, last_client: null };

test('expiry days remaining', () => {
	assert.equal(expiryText(t, new Date('2026-10-08T12:00:00Z')), '3일 남음');
	assert.equal(expiryText(t, new Date('2026-10-12T00:00:00Z')), '만료됨');
	assert.equal(expiryText({ ...t, expires_at: null }), '만료 없음');
});

test('last used text', () => {
	assert.equal(lastUsedText(t), '아직 사용 안 함');
	assert.equal(lastUsedText({ ...t, last_used_at: '2026-10-08 09:00:00', last_client: 'Genspark' }), '최근 사용 2026-10-08 · Genspark');
});

test('endpoint', () => assert.equal(mcpEndpoint('https://a.b'), 'https://a.b/mcp'));
