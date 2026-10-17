<script lang="ts">
	// 진행 중·확정된 상태 기록 목록 — 끝내기·삭제. 질병 삭제만 코치 대화 선택을 묻는다(NEW-18·25).
	import { closeContext, deleteContext } from '$lib/api/context';
	import { getThreads } from '$lib/api/coach';
	import { episodeLabel, isOpen, type ContextEpisode } from '$lib/contextView';
	import type { ChatThread } from '$lib/types';
	import IllnessDeleteChatPicker from './IllnessDeleteChatPicker.svelte';

	let { episodes, onChange }: { episodes: ContextEpisode[]; onChange: () => void } = $props();

	let target = $state<ContextEpisode | null>(null);
	let threads = $state<ChatThread[]>([]);
	let selected = $state<number[]>([]);
	let withChat = $state(true);
	let busy = $state(false);
	let error = $state<string | null>(null);

	const shown = $derived(episodes.filter((e) => e.status === 'confirmed'));

	async function askDelete(e: ContextEpisode) {
		error = null;
		if (e.kind === 'illness') {
			try { threads = (await getThreads()).threads; } catch { threads = []; }
			selected = threads.map((t) => t.id);
			withChat = true;
		}
		target = e;
	}

	async function run(fn: () => Promise<unknown>) {
		busy = true; error = null;
		try { await fn(); target = null; onChange(); } catch (e) { error = e instanceof Error ? e.message : '처리하지 못했어요'; }
		finally { busy = false; }
	}
</script>

{#if shown.length}
	<ul class="space-y-1" aria-label="상태 기록">
		{#each shown as e (e.id)}
			<li class="flex items-center justify-between gap-2 text-sm text-fg-secondary">
				<span class="truncate">{episodeLabel(e)} · {e.start_date}~{e.end_date ?? ''}</span>
				<span class="flex shrink-0 gap-1">
					{#if isOpen(e)}<button type="button" class="min-h-11 px-2" disabled={busy} onclick={() => run(() => closeContext(e.id))}>끝내기</button>{/if}
					<button type="button" class="min-h-11 px-2 text-semantic-red" disabled={busy} onclick={() => askDelete(e)}>삭제</button>
				</span>
			</li>
		{/each}
	</ul>
{/if}

{#if target}
	{@const t = target}
	<div class="fixed inset-0 z-50 flex items-end bg-black/40 lg:items-center lg:justify-center" role="dialog" aria-modal="true" aria-labelledby="ctx-del-title">
		<div class="w-full space-y-3 rounded-t-2xl bg-surface-1 p-4 lg:max-w-md lg:rounded-2xl">
			<p id="ctx-del-title" class="text-sm font-medium text-fg-primary">이 기록을 삭제할까요?</p>
			{#if t.kind === 'illness'}
				<p class="text-xs text-fg-secondary">관련 조정 기록과 AI 요약에서 아팠던 기록도 지워요. 조정 기록 자체는 남아요.</p>
				<IllnessDeleteChatPicker {threads} bind:selected bind:withChat />
			{/if}
			{#if error}<p class="text-xs text-semantic-red">{error}</p>{/if}
			<div class="flex gap-2">
				<button type="button" class="min-h-11 flex-1 rounded-lg bg-surface-2" onclick={() => (target = null)}>취소</button>
				<button type="button" class="min-h-11 flex-1 rounded-lg bg-semantic-red text-white" disabled={busy}
					onclick={() => run(() => deleteContext(t.id, t.kind === 'illness' && withChat ? selected : undefined))}>삭제</button>
			</div>
		</div>
	</div>
{/if}
