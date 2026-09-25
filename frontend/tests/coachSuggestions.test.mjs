import { test } from 'node:test';
import assert from 'node:assert/strict';
import { homeTopics, followUps } from '../src/lib/coachSuggestions.ts';

test('homeTopics(null): 기본 4개', () => {
	const result = homeTopics(null);
	assert.equal(result.length, 4);
	assert.equal(result[0], '오늘 훈련 조언');
	assert.equal(result[1], '레이스 전략');
	assert.equal(result[2], '부상 위험 확인');
	assert.equal(result[3], '훈련 분석');
});

test('homeTopics: days_left 30, target_time_sec 있음', () => {
	const result = homeTopics({ name: 'A', days_left: 30, target_time_sec: 15300 });
	assert.deepEqual(result, [
		'오늘 훈련 조언',
		'레이스까지 어떻게 훈련을 쌓을까?',
		'목표 기록 가능할까?',
		'부상 위험 확인'
	]);
});

test('homeTopics: days_left 10 → 테이퍼 질문', () => {
	const result = homeTopics({ name: 'B', days_left: 10, target_time_sec: null });
	assert.equal(result[1], '테이퍼는 언제부터 어떻게 할까?');
});

test('homeTopics: target_time_sec null → 목표 기록 없음', () => {
	const result = homeTopics({ name: 'C', days_left: 30, target_time_sec: null });
	assert.ok(!result.includes('목표 기록 가능할까?'));
});

test('followUps: 여러 메트릭 → 앞 3개', () => {
	const result = followUps(['race_days_left', 'race_form_projection', 'tsb', 'utrs']);
	assert.deepEqual(result, [
		'왜 테이퍼하면 폼이 올라가?',
		'이 폼이면 이번 주엔 뭘 하면 돼?',
		'남은 기간 주차별로 어떻게 준비할까?'
	]);
});

test('followUps([]): 기본 질문', () => {
	const result = followUps([]);
	assert.deepEqual(result, ['이번 주 훈련 뭘 하면 좋을까?']);
});
