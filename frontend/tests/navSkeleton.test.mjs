// P-25 — 이동 대기 스켈레톤 대상 판정
import test from 'node:test';
import assert from 'node:assert/strict';
import { navSkeletonKind } from '../src/lib/navSkeleton.ts';

const at = (id, params = {}) => ({ route: { id }, params });

test('navSkeletonKind: 다른 화면에서 플랜 상세로 가면 plan-detail', () => {
	assert.equal(navSkeletonKind(at('/coach'), at('/coach/plan/[id]', { id: '3' })), 'plan-detail');
	assert.equal(navSkeletonKind(null, at('/coach/plan/[id]', { id: '3' })), 'plan-detail');
	// 다른 플랜으로
	assert.equal(navSkeletonKind(at('/coach/plan/[id]', { id: '3' }), at('/coach/plan/[id]', { id: '4' })), 'plan-detail');
});

test('navSkeletonKind: 같은 플랜에 머물거나 다른 대상이면 null', () => {
	assert.equal(navSkeletonKind(at('/coach/plan/[id]', { id: '3' }), at('/coach/plan/[id]', { id: '3' })), null);
	assert.equal(navSkeletonKind(at('/coach'), at('/coach/plan/[id]/session/[date]', { id: '3', date: '2026-11-12' })), null);
	assert.equal(navSkeletonKind(at('/coach'), null), null);
	assert.equal(navSkeletonKind(at('/coach'), at(null)), null);
});
