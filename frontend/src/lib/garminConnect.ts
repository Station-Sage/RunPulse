// Garmin 연결 시트 순수 로직(V2-GARMIN-CONNECT §3.6·§4) — 단계 전이, 오류코드→문구, MFA 코드 검사, 남은 시간 표시.
import { ApiError } from './api/client.ts';
import { classifyFailure, failureMessage } from './loadFailure.ts';

export type GarminStep = 'credentials' | 'mfa' | 'done';
export type GarminMode = 'login' | 'mfa' | 'token';

export interface GarminErrorView {
	text: string;
	// 오류 뒤 돌아갈 단계(없으면 현재 단계 유지)
	resetTo?: GarminStep;
	// MFA 코드 입력값을 지울지
	clearCode?: boolean;
}

export function stepAfter(result: { status: string }): GarminStep {
	return result.status === 'needs_mfa' ? 'mfa' : result.status === 'connected' ? 'done' : 'credentials';
}

export function isValidCode(code: string): boolean {
	return /^\d{6,8}$/.test(code.trim());
}

export function attemptsLeft(e: unknown): number | null {
	if (!(e instanceof ApiError) || e.code !== 'MFA_INVALID') return null;
	const n = (e.details as { attempts_left?: unknown } | undefined)?.attempts_left;
	return typeof n === 'number' ? n : null;
}

export function garminErrorText(e: unknown, mode: GarminMode): GarminErrorView {
	if (!(e instanceof ApiError)) return { text: failureMessage(classifyFailure(e).kind) };
	switch (e.code) {
		case 'GARMIN_AUTH_FAILED':
			return {
				text:
					mode === 'token'
						? '토큰으로 로그인하지 못했어요. 새로 발급한 토큰인지 확인해 주세요'
						: '이메일 또는 비밀번호가 맞지 않아요'
			};
		case 'MFA_INVALID': {
			const left = attemptsLeft(e);
			return {
				text: `인증 코드가 맞지 않아요${left != null ? ` (남은 시도 ${left}번)` : ''}`,
				clearCode: true
			};
		}
		case 'MFA_EXPIRED':
			return { text: '시간이 지났어요. 다시 로그인해 주세요', resetTo: 'credentials', clearCode: true };
		case 'MFA_UNAVAILABLE':
			return {
				text: '지금은 인증 코드 단계를 처리할 수 없어요. 고급의 토큰 붙여넣기를 이용해 주세요',
				resetTo: 'credentials'
			};
		case 'GARMIN_RATE_LIMITED':
			return { text: 'Garmin이 잠시 막았어요. 15분 뒤 다시 시도해 주세요' };
		case 'RATE_LIMITED':
			return { text: '시도가 너무 많아요. 잠시 후 다시 시도해 주세요' };
		case 'GARMIN_UPSTREAM':
			return { text: 'Garmin에 연결하지 못했어요. 잠시 후 다시 시도해 주세요' };
		case 'INVALID_PARAM':
			return { text: e.message || '입력값을 확인해 주세요' };
		default:
			return { text: failureMessage(classifyFailure(e).kind) };
	}
}

// 남은 초 → "4:05"
export function formatRemaining(sec: number): string {
	const s = Math.max(0, Math.floor(sec));
	return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

// 최근 30일 동기화 기간(로컬 날짜 YYYY-MM-DD)
export function last30Range(today: Date = new Date()): { from: string; to: string } {
	const iso = (d: Date) =>
		`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	const from = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 30);
	return { from: iso(from), to: iso(today) };
}
