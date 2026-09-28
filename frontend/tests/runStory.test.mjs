import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildRunStory } from '../src/lib/runStory.ts';

const sp = (paces, hrs = []) =>
	paces.map((p, i) => ({
		km: i + 1,
		distanceM: 1000,
		sec: p,
		paceSecKm: p,
		avgHr: hrs[i] ?? null,
		elevDelta: null
	}));

test('4구간 미만이면 null', () => {
	assert.equal(buildRunStory(sp([300, 300, 300])), null);
});

test('후반이 빠르면 negative', () => {
	const s = buildRunStory(sp([360, 360, 300, 300]));
	assert.equal(s.kind, 'negative');
	assert.match(s.headline, /후반이 전반보다 1:00\/km 빨랐어요/);
	assert.equal(s.facts[0].value, '6:00 → 5:00');
});

test('후반이 느리면 positive, 2% 이내면 even', () => {
	assert.equal(buildRunStory(sp([300, 300, 330, 330])).kind, 'positive');
	assert.equal(buildRunStory(sp([300, 301, 300, 301])).kind, 'even');
});

test('디커플링은 백엔드 값만 표시(프론트 재계산 금지)', () => {
	const s = buildRunStory(sp([300, 300, 300, 300], [140, 140, 154, 154]), 9.1);
	const d = s.facts.find((f) => f.key === 'decoupling');
	assert.equal(d.value, '9.1%');
	assert.equal(d.tone, 'warn');
	const none = buildRunStory(sp([300, 300, 300, 300], [140, 140, 154, 154]));
	assert.ok(!none.facts.some((f) => f.key === 'decoupling'));
});

test('심박이 없으면 hr fact 생략', () => {
	const keys = buildRunStory(sp([300, 300, 300, 300])).facts.map((f) => f.key);
	assert.deepEqual(keys, ['pace', 'fastest']);
});

test('가장 빠른 구간, 부분 구간은 제외', () => {
	const splits = [...sp([300, 290, 310, 305]), { km: 5, distanceM: 400, sec: 100, paceSecKm: 250, avgHr: null, elevDelta: null }];
	const f = buildRunStory(splits).facts.find((x) => x.key === 'fastest');
	assert.equal(f.value, '2km · 4:50');
});
