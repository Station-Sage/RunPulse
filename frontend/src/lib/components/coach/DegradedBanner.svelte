<script lang="ts">
	// H0 — AI 꺼짐(규칙 선택) 안내, 연속 3회 이상 규칙 답변으로 떨어졌을 때 홈 상단 안내 (1회 성공하면 서버가 해제).
	import { base } from '$app/paths';
	import type { CoachEngine } from '$lib/types';
	import { reasonText } from '$lib/coachEngine';
	import { announce } from '$lib/a11y/announce';

	let { engine }: { engine: CoachEngine | null } = $props();
	const err = $derived(engine?.health.last_error ?? null);
	$effect(() => {
		if (engine?.health.degraded) announce('AI 연결이 계속 실패해 규칙 답변으로 대신하고 있어요');
	});
</script>

{#if engine?.mode === 'rule_by_choice'}
	<div
		class="rounded-lg border border-semantic-amber/40 bg-semantic-amber/10 px-3 py-2 text-xs text-fg-secondary"
		data-testid="rule-mode-banner"
	>
		AI가 꺼져 있어 규칙 답변으로 대화해요.
		<a href="{base}/data/settings/ai" class="inline-flex min-h-11 items-center underline">설정에서 변경 ›</a>
	</div>
{:else if engine?.health.degraded}
	<div
		class="rounded-lg border border-semantic-amber/40 bg-semantic-amber/10 px-3 py-2 text-xs text-fg-secondary"
		data-testid="degraded-banner"
	>
		AI 연결이 계속 실패해 규칙 답변으로 대신하고 있어요{err ? ` (${reasonText(err.reason)})` : ''}.
		<a href="{base}/data/settings/ai" class="inline-flex min-h-11 items-center underline">AI 설정 ›</a>
	</div>
{/if}
