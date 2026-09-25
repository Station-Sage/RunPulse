export interface GoalLite {
	name: string;
	days_left: number;
	target_time_sec: number | null;
}

const DEFAULT_TOPICS = ['오늘 훈련 조언', '레이스 전략', '부상 위험 확인', '훈련 분석'];

// Coach 홈 주제 칩 — 목표 레이스가 있으면 국면에 맞춘 질문을 앞에 둔다.
export function homeTopics(goal: GoalLite | null): string[] {
	if (!goal) return DEFAULT_TOPICS;
	const phase = goal.days_left <= 21 ? '테이퍼는 언제부터 어떻게 할까?' : '레이스까지 어떻게 훈련을 쌓을까?';
	const topics = ['오늘 훈련 조언', phase];
	if (goal.target_time_sec != null) topics.push('목표 기록 가능할까?');
	topics.push('부상 위험 확인');
	return topics.slice(0, 4);
}

// 답변에 붙은 근거 메트릭 이름으로 다음 질문을 제안한다(최대 3개, 중복 없음).
export function followUps(metrics: string[]): string[] {
	const has = (n: string) => metrics.includes(n);
	const out: string[] = [];
	if (has('race_form_projection')) out.push('왜 테이퍼하면 폼이 올라가?');
	if (has('tsb')) out.push('이 폼이면 이번 주엔 뭘 하면 돼?');
	if (has('race_days_left')) out.push('남은 기간 주차별로 어떻게 준비할까?');
	if (has('utrs')) out.push('오늘 컨디션 점수는 어떻게 계산돼?');
	if (has('cirs')) out.push('부상 위험을 낮추려면?');
	if (out.length === 0) out.push('이번 주 훈련 뭘 하면 좋을까?');
	return [...new Set(out)].slice(0, 3);
}
