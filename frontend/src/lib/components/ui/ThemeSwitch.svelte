<script lang="ts">
	// A11Y 공통 4단계 — 테마 3상태(시스템/라이트/다크). 설정 화면에만 둔다.
	import { onMount } from 'svelte';
	import { applyTheme, readPref, writePref, type ThemePref } from '$lib/theme/theme';

	const OPTIONS: { value: ThemePref; label: string }[] = [
		{ value: 'system', label: '시스템' },
		{ value: 'light', label: '라이트' },
		{ value: 'dark', label: '다크' }
	];

	let pref = $state<ThemePref>('system');
	onMount(() => (pref = readPref()));

	function choose(value: ThemePref) {
		pref = value;
		writePref(value);
		applyTheme(value);
	}
</script>

<div class="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-2 p-3">
	<span id="theme-switch-label" class="text-sm text-fg-primary">화면 테마</span>
	<span class="text-xs text-fg-secondary">시스템을 고르면 기기의 라이트/다크 설정을 따라가요.</span>
	<div role="radiogroup" aria-labelledby="theme-switch-label" class="flex gap-2">
		{#each OPTIONS as o (o.value)}
			<button
				type="button"
				role="radio"
				aria-checked={pref === o.value}
				onclick={() => choose(o.value)}
				class="min-h-11 flex-1 rounded-lg border px-3 text-sm {pref === o.value
					? 'border-semantic-teal bg-surface-3 text-fg-primary'
					: 'border-border-strong text-fg-secondary'}"
			>
				{o.label}
			</button>
		{/each}
	</div>
</div>
