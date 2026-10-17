<script lang="ts">
	// NEW-25·29·30·35 — 질병 기록 삭제 시 함께 지울 코치 대화를 고른다(기본 전체 선택, 끄면 대화는 유지).
	import type { ChatThread } from '$lib/types';

	let { threads, unthreaded = 0, selected = $bindable<number[]>([]), withChat = $bindable(true) }: {
		threads: ChatThread[]; unthreaded?: number; selected?: number[]; withChat?: boolean;
	} = $props();

	function toggle(id: number) {
		selected = selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id];
	}
</script>

<label class="flex min-h-11 items-center gap-2 text-sm">
	<input type="checkbox" bind:checked={withChat} class="h-5 w-5" /> 코치 대화도 삭제
</label>
{#if withChat}
	<ul class="max-h-40 space-y-1 overflow-y-auto" aria-label="삭제할 코치 대화">
		{#each threads as t (t.id)}
			<li>
				<label class="flex min-h-11 items-center gap-2 text-sm text-fg-secondary">
					<input type="checkbox" checked={selected.includes(t.id)} onchange={() => toggle(t.id)} class="h-5 w-5" />
					<span class="truncate">{t.title}</span>
				</label>
			</li>
		{/each}
	</ul>
	{#if unthreaded >= 1}<p class="text-xs text-fg-muted">대화방에 속하지 않은 메시지는 항상 함께 삭제돼요.</p>{/if}
{/if}
