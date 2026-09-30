<script lang="ts">
	// H0 — 연속 3회 이상 규칙 답변으로 떨어졌을 때 홈 상단 안내 (1회 성공하면 서버가 해제).
	import { base } from '$app/paths';
	import type { CoachEngine } from '$lib/types';
	import { reasonText } from '$lib/coachEngine';

	let { engine }: { engine: CoachEngine | null } = $props();
	const err = $derived(engine?.health.last_error ?? null);
</script>

{#if engine?.health.degraded}
	<div
		class="rounded-lg border border-semantic-amber/40 bg-semantic-amber/10 px-3 py-2 text-xs text-fg-secondary"
		role="status"
		data-testid="degraded-banner"
	>
		AI 연결이 계속 실패해 규칙 답변으로 대신하고 있어요{err ? ` (${reasonText(err.reason)})` : ''}.
		<a href="{base}/settings" class="underline">AI 설정 ›</a>
	</div>
{/if}
