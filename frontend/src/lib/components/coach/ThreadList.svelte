<script lang="ts">
	// 코치 홈 '최근 대화' 목록 — 로드 실패(ErrorState·다시 시도, ERR-5), 빈 상태, 목록.
	import { base } from '$app/paths';
	import { invalidate } from '$app/navigation';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import { formatRelativeTime } from '$lib/format';
	import { stripMarkdown } from '$lib/markdownLite';
	import { staleLabel } from '$lib/threadAge';
	import type { Failure } from '$lib/loadFailure';
	import type { ChatThread } from '$lib/types';

	let { threads, titles, failure }: { threads: ChatThread[]; titles: Map<number, string>; failure: Failure | null } =
		$props();
</script>

{#if failure && threads.length === 0}
	<div class="px-4 py-6">
		<ErrorState message="대화를 불러오지 못했어요" {failure} onRetry={() => invalidate('app:coach-threads')} />
	</div>
{:else if threads.length === 0}
	<div class="flex flex-col items-center gap-1 px-4 py-10 text-center">
		<p class="text-fg-secondary">아직 대화가 없습니다</p>
		<p class="text-sm text-fg-muted">아래에서 새 대화를 시작해 보세요.</p>
	</div>
{:else}
	<ul class="divide-y divide-border-subtle">
		{#each threads as t (t.id)}
			<li>
				<a
					href="{base}/coach/{t.id}"
					class="flex items-center gap-3 px-4 py-3 hover:bg-surface-2 active:bg-surface-3"
				>
					<div class="min-w-0 flex-1">
						<p class="truncate text-sm font-medium">{titles.get(t.id) ?? t.title}</p>
						{#if t.last_message}
							<p class="line-clamp-2 text-xs text-fg-muted">{stripMarkdown(t.last_message)}</p>
						{/if}
						{#if staleLabel(t.last_message_at, Date.now())}
							<p class="text-[10px] text-semantic-amber">{staleLabel(t.last_message_at, Date.now())}</p>
						{/if}
					</div>
					{#if t.last_message_at}
						<span class="shrink-0 text-xs text-fg-muted">{formatRelativeTime(t.last_message_at)}</span>
					{/if}
					<span class="text-fg-muted">›</span>
				</a>
			</li>
		{/each}
	</ul>
{/if}
