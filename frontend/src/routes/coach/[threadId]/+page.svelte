<script lang="ts">
	// 03e-coach.md 5-B — 대화 스레드: 메시지 목록 + 입력 바.
	// P7-IMPL-COACH-EVIDENCE-UI: 근거 칩(EvidenceQuote) + MetricBreakdown 드릴다운 + 입력창 하단 도킹.
	import type { ThreadPageData } from './+page';
	import { addMessage } from '$lib/api/coach';
	import { ApiError } from '$lib/api/client';
	import { base } from '$app/paths';
	import type { ChatMessage } from '$lib/types';
	import ChatBody from '$lib/components/ChatBody.svelte';
	import EvidenceQuote from '$lib/components/EvidenceQuote.svelte';
	import MetricBreakdown from '$lib/components/MetricBreakdown.svelte';
	import { localizeSource } from '$lib/markdownLite';
	import { adaptEvidence, type DrillTarget } from '$lib/evidence';
	import { followUps } from '$lib/coachSuggestions';

	let { data }: { data: ThreadPageData } = $props();

	const thread = $derived(data.detail?.thread ?? null);
	let messages = $state<ChatMessage[]>(data.detail?.messages ?? []);
	let errorMessage = $state(data.errorMessage);

	let inputText = $state('');
	let sending = $state(false);
	let messagesEnd: HTMLDivElement | undefined = $state();

	const lastMsg = $derived(messages[messages.length - 1] ?? null);

	// MetricBreakdown 드릴다운 스택
	let drillStack = $state<DrillTarget[]>([]);
	const drillTop = $derived(drillStack.length > 0 ? drillStack[drillStack.length - 1] : null);

	function openEvidence(t: DrillTarget) {
		drillStack = [...drillStack, t];
	}

	function closeDrill() {
		drillStack = [];
	}

	function handleDrillInput(slug: string) {
		const top = drillStack.length > 0 ? drillStack[drillStack.length - 1] : null;
		drillStack = [
			...drillStack,
			{
				slug,
				scopeType: top?.scopeType ?? 'daily',
				scopeId: top?.scopeId ?? ''
			}
		];
	}

	function scrollToBottom() {
		messagesEnd?.scrollIntoView({ block: 'end' });
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
	<div class="flex min-h-[calc(100dvh-15.5rem)] flex-col gap-3 px-4 py-4">
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
						<ChatBody content={msg.content} />
						{#if localizeSource(msg.ai_model)}
							<p class="mt-1 text-[11px] font-medium text-fg-secondary">{localizeSource(msg.ai_model)}</p>
						{/if}
						{#if msg.evidence && msg.evidence.length > 0}
							<div class="mt-2 flex flex-wrap gap-2">
								{#each msg.evidence as ev}
									<EvidenceQuote {...adaptEvidence(ev, openEvidence)} />
								{/each}
							</div>
						{/if}
					</div>
				</div>
			{/if}
		{/each}

		{#if lastMsg?.role === 'assistant' && !sending}
			<div class="flex flex-wrap gap-2">
				{#each followUps((lastMsg.evidence ?? []).map((e) => e.metric)) as q}
					<button
						type="button"
						onclick={() => {
							inputText = q;
							send();
						}}
						class="rounded-full border border-border-subtle bg-surface-2 px-3 py-1 text-xs text-fg-secondary hover:bg-surface-3"
					>{q}</button>
				{/each}
			</div>
		{/if}

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

	<!-- 입력 바 (하단 탭바 바로 위 고정) -->
	<div class="sticky bottom-14 z-10 border-t border-border-subtle bg-surface-1 px-4 py-3">
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

	<!-- MetricBreakdown 드릴다운 패널 -->
	{#if drillTop}
		<MetricBreakdown
			slug={drillTop.slug}
			scopeType={drillTop.scopeType}
			scopeId={drillTop.scopeId}
			onClose={closeDrill}
			onDrillInput={handleDrillInput}
		/>
	{/if}
{/if}
