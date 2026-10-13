import { apiFetch } from './client';

// 개발 전용 사용자 전환(V1-8) — 서버가 production 이면 두 경로 모두 404(숨김 판정에 쓴다).
export interface DevUsers {
	users: string[];
	current: string;
}

export const getDevUsers = () => apiFetch<DevUsers>('/dev/users');
export const switchDevUser = (userId: string) =>
	apiFetch<{ user_id: string; users: string[] }>('/dev/switch-user', {
		method: 'POST',
		body: JSON.stringify({ user_id: userId })
	});
