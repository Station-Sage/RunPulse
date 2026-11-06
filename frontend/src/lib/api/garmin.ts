// Garmin 연결 v2 API (V2-GARMIN-CONNECT) — 비밀번호 로그인·MFA·토큰 붙여넣기. 오류는 ApiError(code)로 온다.
// 해제·연결 테스트는 data.ts 의 disconnectSource/testSource 를 그대로 쓴다.
import { apiFetch } from './client';

const BASE = '/data/sources/garmin';

export type GarminConnectResult =
	| { status: 'connected'; message_ko?: string }
	| { status: 'needs_mfa'; mfa_ticket: string; expires_in: number };

const post = <T>(path: string, body: unknown) =>
	apiFetch<T>(`${BASE}${path}`, { method: 'POST', body: JSON.stringify(body) });

export const garminLogin = (email: string, password: string) =>
	post<GarminConnectResult>('/connect', { email, password });

export const garminMfa = (mfaTicket: string, code: string) =>
	post<{ status: 'connected'; message_ko?: string }>('/mfa', { mfa_ticket: mfaTicket, code });

export const garminMfaCancel = () => post<{ status: 'disconnected' }>('/mfa/cancel', {});

export const garminToken = (tokenJson: string) =>
	post<{ status: 'connected'; message_ko?: string }>('/token', { token_json: tokenJson });

// 로컬 PC 동기화 키트 다운로드 주소(같은 출처 GET, 첨부 응답)
export const LOCAL_KIT_SCRIPT_URL = `/api/v1${BASE}/local-kit/script`;
export const LOCAL_KIT_ENV_URL = `/api/v1${BASE}/local-kit/env`;
