<script lang="ts">
	// 첫 LLM 전송 동의 + 전송 범위 3개 토글 (30-coach-chat design §7.3). 동의 전에는 외부 호출이 없다.
	import type { CoachEngine } from '$lib/types';
	import type { ConsentInput } from '$lib/api/coach';
	import { visibleScope } from '$lib/coachEngine';
	import { getConsent, postConsent } from '$lib/api/context';
	import { onMount } from 'svelte';
	import { modal } from '$lib/overlay';

	let {
		engine,
		requireConsent,
		onSave,
		onClose
	}: {
		engine: CoachEngine;
		requireConsent: boolean;
		onSave: (input: ConsentInput) => Promise<void>;
		onClose: () => void;
	} = $props();

	const c = engine.consent;
	let excludeNotes = $state(c?.exclude_notes ?? false);
	let toolsEnabled = $state(c?.tools_enabled ?? true);
	let fallbackEnabled = $state(c?.fallback_enabled ?? true);
	let saving = $state(false);
	let error = $state<string | null>(null);

	let illnessShare = $state(false);
	let illnessBusy = $state(false);
	onMount(async () => {
		try { illnessShare = (await getConsent()).action === 'grant'; } catch { /* 부가 설정 — 실패해도 시트는 연다 */ }
	});
	async function toggleIllness() {
		illnessBusy = true;
		const next = !illnessShare;
		try { await postConsent(next ? 'grant' : 'revoke', 'settings'); illnessShare = next; }
		catch (e) { error = e instanceof Error ? e.message : '저장하지 못했어요.'; }
		finally { illnessBusy = false; }
	}

	const items = $derived(visibleScope(engine.scope, excludeNotes));

	async function save() {
		saving = true;
		error = null;
		try {
			await onSave({
				provider: engine.selected.provider,
				exclude_notes: excludeNotes,
				tools_enabled: toolsEnabled,
				fallback_enabled: fallbackEnabled
			});
		} catch (e) {
			error = e instanceof Error ? e.message : '저장하지 못했어요.';
		} finally {
			saving = false;
		}
	}
</script>

<div class="fixed inset-0 z-50 flex flex-col">
	<button class="absolute inset-0 bg-scrim" onclick={onClose} tabindex="-1" aria-hidden="true" aria-label="닫기"></button>
	<div
		use:modal={{ onClose }}
		role="dialog"
		aria-modal="true"
		aria-labelledby="scope-sheet-h"
		class="absolute inset-x-0 bottom-0 flex sheet-bottom flex-col gap-3 rounded-t-2xl bg-surface-1 p-4 shadow-lg"
	>
		<h2 id="scope-sheet-h" class="font-medium">{requireConsent ? 'AI로 질문을 보내기 전에' : '전송 범위'}</h2>
		{#if requireConsent}
			<p class="text-xs text-fg-secondary">
				질문과 아래 러닝 데이터가 {engine.selected.provider} 서버로 전송돼요. 동의해야 AI 답변을 쓸 수 있고, 동의 전에는 아무것도 전송하지 않아요.
			</p>
		{/if}

		<ul class="flex flex-col gap-1 text-xs text-fg-secondary" data-testid="scope-list">
			{#each items as s}
				<li>· {s.item} <span class="text-fg-muted">({s.period})</span></li>
			{/each}
		</ul>

		<label class="flex items-center justify-between gap-3 text-sm">
			<span>메모·주관 입력 제외</span>
			<input type="checkbox" bind:checked={excludeNotes} data-testid="toggle-exclude-notes" />
		</label>
		<label class="flex items-center justify-between gap-3 text-sm">
			<span>필요한 데이터를 AI가 직접 조회</span>
			<input type="checkbox" bind:checked={toolsEnabled} data-testid="toggle-tools" />
		</label>
		<label class="flex items-center justify-between gap-3 text-sm">
			<span>실패 시 다른 AI로 재시도</span>
			<input type="checkbox" bind:checked={fallbackEnabled} data-testid="toggle-fallback" />
		</label>

		<label class="flex items-center justify-between gap-3 text-sm">
			<span>아팠던 기록을 코치와 공유</span>
			<input type="checkbox" checked={illnessShare} disabled={illnessBusy} onchange={toggleIllness} data-testid="toggle-illness" />
		</label>
		{#if !illnessShare}<p class="text-xs text-fg-muted">끄면 이후 AI에는 '컨디션 신호'로만 전달돼요. 이미 보낸 대화는 그대로예요.</p>{/if}

		{#if error}<p class="text-xs text-semantic-red">{error}</p>{/if}

		<div class="flex justify-end gap-2 text-sm">
			<button type="button" onclick={onClose} class="min-h-11 rounded-lg px-3 py-2 text-fg-secondary">취소</button>
			<button
				type="button"
				onclick={save}
				disabled={saving}
				data-testid="consent-save"
				data-autofocus
				class="min-h-11 rounded-lg bg-fg-primary px-4 py-2 text-surface-1 disabled:opacity-40"
			>{requireConsent ? '동의하고 보내기' : '저장'}</button>
		</div>
	</div>
</div>
