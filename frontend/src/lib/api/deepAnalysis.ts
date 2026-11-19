// 오늘 훈련 상세 분석(opus) — 시작 → 코치 스레드로 이어짐 (V2-AI-CLAUDE-QUEUE E5-d).
import { apiFetch } from './client';

export interface DeepState {
	available: boolean;
	activity_id: number | null;
}

export interface DeepStarted {
	thread: { id: number };
	assistant_message: { id: number };
	activity_id: number;
}

export const getDeepAnalysis = (): Promise<DeepState> => apiFetch<DeepState>('/coach/deep');

export const startDeepAnalysis = (activityId?: number): Promise<DeepStarted> =>
	apiFetch('/coach/deep', { method: 'POST', body: JSON.stringify(activityId ? { activity_id: activityId } : {}) });
