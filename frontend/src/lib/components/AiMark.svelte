<script lang="ts">
	// 'AI 해설' 표시 — source==='ai' 일 때만 그린다(규칙 문구엔 표시 없음, ADR-059).
	import { AI_MARK_TITLE, aiMarkText, isAiWorded } from '$lib/aiWording';

	let { source, prefix = false }: { source: string | null | undefined; prefix?: boolean } = $props();
</script>

{#if isAiWorded(source)}
	<span class="normal-case text-xs text-fg-muted" title={AI_MARK_TITLE} data-testid="ai-mark">{aiMarkText(prefix)}</span>
{/if}
