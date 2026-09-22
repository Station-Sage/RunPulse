<script lang="ts">
	// 03e-coach.md 5-A — Coach 홈: 최근 대화 목록 + 새 대화 시작.
	// 플랜 섹션(plan_service 스텁) · QuickInput(Today에 이미 있음) · 컨텍스트 패널(7d)은 범위 밖.
	import type { CoachPageData } from './+page';
	import { createThread } from '$lib/api/coach';
	import { ApiError } from '$lib/api/client';
	import { formatRelativeTime } from '$lib/format';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import type { ChatThread } from '$lib/types';

	let { data }: { data: CoachPageData } = $props();

	let threads = $state<ChatThread[]>(data.result?.threads ?? []);
	let errorMessage = $state(data.errorMessage);

	// 새 대화 입력 상태
	let isCreating = $state(false);
	let newInput = $state('');
	let sending = $state(false);

	const SUGGESTED_TOPICS = ['오늘 훈련 조언', '레이스 전략', '부상 위험 확인', '훈련 분석'];

	function openNew(prefill = '') {
		newInput = prefill;
		isCreating = true;
	}

	async function submitNew() {
		const msg = newInput.trim();
		if (!msg || sending) return;
		sending = true;
		errorMessage = null;
		try {
			const res = await createThread(msg);
			await goto(`${base}/coach/${res.thread.id}`);
		} catch (e) {
			errorMessage = e instanceof ApiError ? e.message : '대화를 시작할 수 없습니다.';
			sending = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			submitNew();
		}
	}
</script>

<div class="flex flex-col">
	<!-- 최근 대화 섹션 -->
	<div class="border-b border-border-subtle px-4 py-3">
		<p class="text-xs uppercase tracking-wide text-fg-muted">최근 대화</p>
	</div>

	{#if errorMessage && threads.length === 0}
		<div class="flex flex-col items-center gap-2 px-4 py-10 text-center">
			<p class="text-fg-secondary">대화를 불러올 수 없습니다</p>
			<p class="text-xs text-fg-muted">{errorMessage}</p>
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
							<p class="truncate text-sm font-medium">{t.title}</p>
							{#if t.last_message}
								<p class="truncate text-xs text-fg-muted">{t.last_message}</p>
							{/if}
						</div>
						{#if t.last_message_at}
							<span class="shrink-0 text-xs text-fg-muted"
								>{formatRelativeTime(t.last_message_at)}</span
							>
						{/if}
						<span class="text-fg-muted">›</span>
					</a>
				</li>
			{/each}
		</ul>
	{/if}

	<!-- 새 대화 입력 폼 (토글) -->
	{#if isCreating}
		<div class="border-t border-border-subtle px-4 py-3">
			<textarea
				bind:value={newInput}
				onkeydown={handleKeydown}
				placeholder="무엇이든 물어보세요…"
				rows={3}
				disabled={sending}
				class="w-full resize-none rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-primary placeholder:text-fg-muted focus:outline-none disabled:opacity-50"
			></textarea>
			<div class="mt-2 flex justify-end gap-2">
				<button
					type="button"
					onclick={() => {
						isCreating = false;
						newInput = '';
					}}
					disabled={sending}
					class="rounded-lg border border-border-subtle px-4 py-2 text-sm text-fg-secondary disabled:opacity-50"
				>
					취소
				</button>
				<button
					type="button"
					onclick={submitNew}
					disabled={sending || !newInput.trim()}
					class="rounded-lg bg-fg-primary px-4 py-2 text-sm text-surface-1 disabled:opacity-40"
				>
					{sending ? '전송 중…' : '전송'}
				</button>
			</div>
			{#if errorMessage}
				<p class="mt-1 text-xs text-semantic-red">{errorMessage}</p>
			{/if}
		</div>
	{:else}
		<!-- + 새 대화 시작 버튼 -->
		<div class="flex justify-center px-4 py-4">
			<button
				type="button"
				onclick={() => openNew()}
				class="rounded-lg border border-border-subtle bg-surface-2 px-6 py-2.5 text-sm font-medium text-fg-primary"
			>
				+ 새 대화 시작
			</button>
		</div>
	{/if}

	<!-- 자주 묻는 주제 -->
	{#if !isCreating}
		<div class="border-t border-border-subtle px-4 py-3">
			<p class="mb-2 text-xs uppercase tracking-wide text-fg-muted">자주 묻는 주제</p>
			<div class="flex flex-wrap gap-2">
				{#each SUGGESTED_TOPICS as topic}
					<button
						type="button"
						onclick={() => openNew(topic)}
						class="rounded-full border border-border-subtle bg-surface-2 px-3 py-1 text-sm text-fg-secondary hover:bg-surface-3"
					>
						{topic}
					</button>
				{/each}
			</div>
		</div>

		<!-- 플랜 섹션 (plan_service 스텁 — Phase 7b에서 완성) -->
		<div class="border-t border-border-subtle px-4 py-3">
			<p class="mb-1 text-xs uppercase tracking-wide text-fg-muted">플랜</p>
			<p class="text-sm text-fg-muted">플랜 기능은 준비 중입니다.</p>
		</div>
	{/if}
</div>
