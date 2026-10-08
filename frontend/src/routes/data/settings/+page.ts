// Data › 설정: 외부 AI 연결(원격 MCP) 토큰 목록.
import { getMcpTokens, type McpTokenList } from '$lib/api/mcpTokens';

export async function load(): Promise<{ mcp: McpTokenList | null }> {
	return { mcp: await getMcpTokens().catch(() => null) };
}
