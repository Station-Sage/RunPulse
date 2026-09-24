<script lang="ts">
	// 03e-coach.md 5-B — 대화 스레드: 메시지 목록 + 입력 바.
	// 컨텍스트 패널은 범위 밖(7d). EvidenceQuote는 현재 API가 구조화된 근거를
	// 별도로 반환하지 않아 텍스트 렌더링만 사용(Phase 7b API 확장 시 개선 가능).
	import type { ThreadPageData } from './+page';
	import { addMessage } from '$lib/api/coach';
	import { ApiError } from '$lib/api/client';
	import { base } from '$app/paths';
	import type { ChatMessage } from '$lib/types';

	let { data }: { data: ThreadPageData } = $props();

	const thread = $derived(data.detail?.thread ?? null);
	let messages = $state<ChatMessage[]>(data.detail?.messages ?? []);
	let errorMessage = $state(data.errorMessage);

	let inputText = $state('');
	let sending = $state(false);
	let messagesEnd: HTMLDivElement | undefined = $state();

	function scrollToBottom() {
		messagesEnd?.scrollIntoView({ behavior: 'smooth' });
	}

	async function send() {
		const content = inputText.trim();
		if (!content || sending || !thread) return;

		// 낙관적 사용자 메시지 추가
		const tempUserMsg: ChatMessage = {
			id: Date.now(),
			role: 'user',
			content,
			ai_model: null,
			created_at: new Date().toISOString()
		};
		messages = [...messages, tempUserMsg];
		inputText = '';
		sending = true;
		errorMessage = null;

		// 스크롤
		setTimeout(scrollToBottom, 50);

		try {
			const res = await addMessage(thread.id, content);
			messages = [
				...messages,
				{
					...res.message,
					created_at: res.message.created_at ?? new Date().toISOString()
				}
			];
			setTimeout(scrollToBottom, 50);
		} catch (e) {
			errorMessage = e instanceof ApiError ? e.message : '메시지 전송에 실패했습니다.';
		} finally {
			sending = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			send();
		}
	}
</script>

<svelte:head><title>Coach 대화 · RunPulse</title></svelte:head>

{#if !thread}
	<div class="flex flex-col items-center gap-3 px-4 py-20 text-center">
		<p class="text-lg text-fg-secondary">대화를 찾을 수 없습니다</p>
		{#if data.errorMessage}
			<p class="text-xs text-fg-muted">{data.errorMessage}</p>
		{/if}
		<a href="{base}/coach" class="text-sm text-fg-secondary underline">← Coach로</a>
	</div>
{:else}
	<!-- 헤더 -->
	<div class="flex items-center gap-2 border-b border-border-subtle px-4 py-3">
		<a href="{base}/coach" class="shrink-0 text-fg-muted" aria-label="Coach로">←</a>
		<h1 class="min-w-0 flex-1 truncate text-base font-semibold">{thread.title}</h1>
	</div>

	<!-- 메시지 목록 -->
	<div class="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-4 pb-2">
		{#if messages.length === 0}
			<p class="text-center text-sm text-fg-muted">대화를 시작해 보세요.</p>
		{/if}

		{#each messages as msg (msg.id)}
			{#if msg.role === 'user'}
				<!-- 사용자 말풍선 (오른쪽) -->
				<div class="flex justify-end">
					<div
						class="max-w-[75%] rounded-2xl rounded-br-sm bg-fg-primary px-3 py-2 text-sm text-surface-1"
					>
						{msg.content}
					</div>
				</div>
			{:else}
				<!-- Coach 말풍선 (왼쪽) -->
				<div class="flex justify-start">
					<div
						class="max-w-[80%] rounded-2xl rounded-bl-sm border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-primary"
					>
						<p class="whitespace-pre-wrap">{msg.content}</p>
						{#if msg.ai_model}
							<p class="mt-1 text-[10px] text-fg-muted">{msg.ai_model}</p>
						{/if}
					</div>
				</div>
			{/if}
		{/each}

		{#if sending}
			<div class="flex justify-start">
				<div
					class="rounded-2xl rounded-bl-sm border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-muted"
				>
					답변 생성 중…
				</div>
			</div>
		{/if}

		{#if errorMessage}
			<p class="text-center text-xs text-semantic-red">{errorMessage}</p>
		{/if}

		<div bind:this={messagesEnd}></div>
	</div>

	<!-- 입력 바 -->
	<div class="border-t border-border-subtle px-4 py-3">
		<div class="flex items-end gap-2">
			<textarea
				bind:value={inputText}
				onkeydown={handleKeydown}
				placeholder="메시지 입력…"
				rows={1}
				disabled={sending}
				class="flex-1 resize-none rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-primary placeholder:text-fg-muted focus:outline-none disabled:opacity-50"
				style="min-height:2.25rem; max-height:8rem; overflow-y:auto;"
			></textarea>
			<button
				type="button"
				onclick={send}
				disabled={sending || !inputText.trim()}
				class="rounded-lg bg-fg-primary px-4 py-2 text-sm text-surface-1 disabled:opacity-40"
				aria-label="전송"
			>
				전송
			</button>
		</div>
	</div>
{/if}
