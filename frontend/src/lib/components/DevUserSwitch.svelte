<script lang="ts">
	import { say } from '$lib/a11y/say';
	// 개발 전용 사용자 전환(V1-8, S3 5단계) — 서버가 production 이면 /dev/users 가 404 라 아무것도 그리지 않는다.
	// 같은 빌드를 개발·운영이 함께 쓰므로 빌드 플래그가 아니라 서버 응답(APP_ENV)으로 판정한다.
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { modal } from '$lib/overlay';
	import { ApiError } from '$lib/api/client';
	import { getDevUsers, switchDevUser } from '$lib/api/devUsers';
	import { isSameUser, pickUserId, uidProblem } from '$lib/devUsers';

	let { onClose }: { onClose: () => void } = $props();

	let available = $state(false);
	let dialogOpen = $state(false);
	let users = $state<string[]>([]);
	let current = $state('');
	let selected = $state('');
	let typed = $state('');
	let busy = $state(false);
	let error = $state<string | null>(null);

	const target = $derived(pickUserId(selected, typed));
	const problem = $derived(typed.trim() ? uidProblem(typed) : null);

	onMount(async () => {
		try {
			const d = await getDevUsers();
			users = d.users;
			current = d.current;
			selected = d.current;
			available = true;
		} catch {
			available = false; // 404(production)·네트워크 오류 모두 숨김 — 실패 시 닫힌 쪽이 안전
		}
	});

	async function submit() {
		error = null;
		const bad = uidProblem(target);
		if (bad) {
			error = bad;
			return;
		}
		if (isSameUser(target, current)) {
			dialogOpen = false;
			return;
		}
		busy = true;
		try {
			await switchDevUser(target.trim());
			onClose();
			location.assign(`${base}/`); // 세션 사용자가 바뀌었으니 모든 화면 상태를 새로 읽는다
		} catch (e) {
			if (e instanceof ApiError && e.status === 404) available = false;
			error =
				e instanceof ApiError
					? ((e.details as Record<string, string> | undefined)?.user_id ?? e.message)
					: '전환하지 못했어요';
			busy = false;
		}
	}
</script>

{#if available}
	<button
		type="button"
		data-testid="dev-switch-open"
		onclick={() => (dialogOpen = true)}
		class="block w-full rounded-lg px-3 py-2 text-left text-sm text-fg-secondary hover:bg-surface-2"
	>
		사용자 전환 (개발)
	</button>

	{#if dialogOpen}
		<div
			class="fixed inset-0 z-[60] flex items-center justify-center p-4"
			role="dialog"
			aria-modal="true"
			aria-label="사용자 전환 (개발 전용)"
			use:modal={{ onClose: () => (dialogOpen = false) }}
		>
			<button
				type="button"
				class="absolute inset-0 bg-black/50"
				aria-label="닫기"
				onclick={() => (dialogOpen = false)}
			></button>
			<form
				class="relative w-full max-w-sm rounded-xl bg-surface-1 p-4 shadow-lg"
				onsubmit={(e) => {
					e.preventDefault();
					submit();
				}}
			>
				<h3 class="mb-1 font-medium">사용자 전환</h3>
				<p class="mb-3 text-xs text-fg-muted">개발 환경 전용입니다. 현재: {current}</p>

				<label class="mb-1 block text-xs text-fg-muted" for="dev-user-select">기존 사용자</label>
				<select
					id="dev-user-select"
					bind:value={selected}
					class="mb-3 w-full rounded-lg border border-border-subtle bg-surface-2 px-2 py-2 text-sm"
				>
					{#each users as u (u)}
						<option value={u}>{u}</option>
					{/each}
				</select>

				<label class="mb-1 block text-xs text-fg-muted" for="dev-user-new">또는 새 사용자</label>
				<input
					id="dev-user-new"
					bind:value={typed}
					autocomplete="off"
					autocapitalize="off"
					spellcheck="false"
					placeholder="예: test@example.com"
					class="mb-1 w-full rounded-lg border border-border-subtle bg-surface-2 px-2 py-2 text-sm"
				/>
				{#if problem}
					<p class="mb-2 text-xs text-status-danger" data-testid="dev-switch-problem">{problem}</p>
				{/if}
				{#if error}
					<p class="mb-2 text-xs text-status-danger" data-testid="dev-switch-error" use:say={{ text: error, level: 'assertive' }}>{error}</p>
				{/if}

				<div class="mt-3 flex justify-end gap-2">
					<button
						type="button"
						onclick={() => (dialogOpen = false)}
						class="rounded-lg px-3 py-2 text-sm text-fg-secondary hover:bg-surface-2"
					>
						취소
					</button>
					<button
						type="submit"
						disabled={busy || !!problem || !target}
						data-testid="dev-switch-submit"
						class="rounded-lg bg-surface-3 px-3 py-2 text-sm text-fg-primary hover:bg-border-subtle disabled:opacity-40"
					>
						전환
					</button>
				</div>
			</form>
		</div>
	{/if}
{/if}
