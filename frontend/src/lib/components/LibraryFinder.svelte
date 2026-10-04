<script lang="ts">
	// Library 홈 찾기 행 — 검색(Enter → 활동 목록) + 빠른 칩.
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { finderQuery, QUICK_CHIPS } from '$lib/libraryHome';

	let q = $state('');

	function submit(e: SubmitEvent) {
		e.preventDefault();
		const query = finderQuery(q);
		if (query) goto(`${base}/library/activities?${query}`);
	}
</script>

<section class="flex flex-col gap-2 px-4" aria-label="활동 찾기">
	<form onsubmit={submit} role="search">
		<input
			type="search"
			bind:value={q}
			placeholder="활동 이름·메모 검색"
			aria-label="활동 검색"
			class="h-10 w-full rounded-lg border border-border-subtle bg-surface-2 px-3 text-sm text-fg-primary placeholder:text-fg-muted"
		/>
	</form>
	<div class="flex flex-wrap gap-2">
		{#each QUICK_CHIPS as c (c.query)}
			<a
				href="{base}/library/activities?{c.query}"
				class="rounded-full border border-border-subtle bg-surface-2 px-3 py-1.5 text-xs text-fg-secondary hover:bg-surface-3"
				>{c.label}</a
			>
		{/each}
	</div>
</section>
