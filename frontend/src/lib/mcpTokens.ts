// 외부 AI 연결 카드 표시 헬퍼.
import type { McpToken } from '$lib/api/mcpTokens';

export function expiryText(t: McpToken, now: Date = new Date()): string {
	if (!t.expires_at) return '만료 없음';
	const days = Math.ceil((new Date(t.expires_at.replace(' ', 'T') + 'Z').getTime() - now.getTime()) / 86400000);
	return days <= 0 ? '만료됨' : `${days}일 남음`;
}

export function lastUsedText(t: McpToken): string {
	if (!t.last_used_at) return '아직 사용 안 함';
	return `최근 사용 ${t.last_used_at.slice(0, 10)}${t.last_client ? ` · ${t.last_client}` : ''}`;
}

export const mcpEndpoint = (origin: string) => `${origin}/mcp`;
