<script lang="ts">
	// 활동 한 줄 판정 — 전·후반 페이스·심박·디커플링을 근거(fact)와 함께 보여준다.
	// DECISIONS.md [P7-IMPL-RUN-STORY]: 모든 문장은 아래 근거 칸으로 검증 가능해야 한다.
	import type { RunStory } from '$lib/runStory';

	let { story }: { story: RunStory | null } = $props();

	const TONE: Record<string, string> = {
		good: 'text-semantic-green',
		warn: 'text-semantic-amber',
		neutral: 'text-fg-primary'
	};
	const ACCENT: Record<string, string> = {
		negative: 'border-l-semantic-green',
		positive: 'border-l-semantic-amber',
		even: 'border-l-semantic-teal'
	};
</script>

{#if story}
	<section
		aria-label="이 러닝의 이야기"
		class="flex flex-col gap-3 rounded-lg border border-border-subtle border-l-4 bg-surface-2 p-4 {ACCENT[story.kind]}"
	>
		<p class="text-base font-semibold leading-snug">{story.headline}</p>
		<div class="grid grid-cols-2 gap-x-4 gap-y-3">
			{#each story.facts as f (f.key)}
				<div class="flex flex-col gap-0.5" title={f.hint}>
					<span class="text-[11px] text-fg-muted">{f.label}</span>
					<span class="font-mono text-lg font-bold {TONE[f.tone]}">{f.value}</span>
					<span class="text-[10px] leading-tight text-fg-muted">{f.hint}</span>
				</div>
			{/each}
		</div>
		<p class="text-[10px] text-fg-muted">스트림에서 재구성한 km 구간 기반 · 아래 구간 차트로 확인</p>
	</section>
{/if}
