<script lang="ts">
	// A11Y 공통 4단계 — 테마 3상태(시스템/라이트/다크). 설정 화면에만 둔다.
	import { onMount } from 'svelte';
	import ToggleGroup from './ToggleGroup.svelte';
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
	<span class="text-sm text-fg-primary">화면 테마</span>
	<span class="text-xs text-fg-secondary">시스템을 고르면 기기의 라이트/다크 설정을 따라가요.</span>
	<ToggleGroup label="화면 테마" items={OPTIONS.map((o) => ({ value: o.value, label: o.label }))} selected={pref} onchange={(v) => choose(v as ThemePref)} class="grid grid-cols-3 gap-2" />
</div>
