// 오늘 훈련 상세 분석(opus) — 시작·진행 폴링·취소 (V2-AI-CLAUDE-QUEUE E5-d).
import { apiFetch } from './client';

export interface DeepRun {
	state: 'running' | 'ready' | 'failed' | 'cancelled';
	stage: 'queued' | 'thinking' | 'analyzing' | 'done';
	tools: string[];
	elapsed: number;
	reason?: string | null;
	activity_id: number;
}

export interface DeepResult {
	text: string;
	suggestions: string[];
	created_at: string;
}

export interface DeepState {
	available: boolean;
	activity_id: number | null;
	run: DeepRun | null;
	result: DeepResult | null;
}

export const getDeepAnalysis = (): Promise<DeepState> => apiFetch<DeepState>('/coach/deep');

export const startDeepAnalysis = (activityId?: number): Promise<{ started: boolean; activity_id: number }> =>
	apiFetch('/coach/deep', { method: 'POST', body: JSON.stringify(activityId ? { activity_id: activityId } : {}) });

export const cancelDeepAnalysis = (): Promise<{ cancelled: boolean }> =>
	apiFetch('/coach/deep/cancel', { method: 'POST', body: '{}' });
