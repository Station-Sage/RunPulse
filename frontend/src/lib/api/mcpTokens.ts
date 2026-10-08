// 원격 MCP 토큰 API — design MCP-REMOTE R8. 원문 토큰은 발급 응답에서만 한 번 내려온다.
import { ApiError, apiFetch } from './client';

export interface McpToken {
	token_id: string;
	label: string;
	last4: string;
	created_at: string;
	expires_at: string | null;
	revoked_at: string | null;
	last_used_at: string | null;
	last_client: string | null;
}

export interface McpTokenList {
	enabled: boolean;
	max_active: number;
	default_days: number;
	tokens: McpToken[];
}

export type IssuedMcpToken = McpToken & { token: string };

export const getMcpTokens = () => apiFetch<McpTokenList>('/settings/mcp-tokens');

// POST는 자동 재시도하지 않는다.
export const issueMcpToken = (label: string) =>
	apiFetch<IssuedMcpToken>('/settings/mcp-tokens', { method: 'POST', body: JSON.stringify({ label }) });

export async function revokeMcpToken(tokenId: string): Promise<void> {
	const res = await fetch(`/api/v1/settings/mcp-tokens/${encodeURIComponent(tokenId)}`, { method: 'DELETE' });
	if (!res.ok) throw new ApiError(res.status, {});
}
