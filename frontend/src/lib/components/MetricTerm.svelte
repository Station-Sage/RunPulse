<script lang="ts">
	// 용어 옆 ⓘ — 탭하면 한 줄 설명 팝오버. 설명이 없으면 아무것도 렌더하지 않는다.
	import { getMetricExplain } from '$lib/api/metrics';

	let { slug, label, fallback = null, date = '' }: { slug: string; label: string; fallback?: string | null; date?: string } = $props();

	let open = $state(false);
	let what = $state<string | null>(null);
	let loaded = false;

	async function toggle() {
		open = !open;
		if (open && !loaded) {
			loaded = true;
			try {
				if (date) what = (await getMetricExplain(slug, 'daily', date)).meaning?.what ?? null;
			} catch {
				what = null;
			}
		}
	}
	const text = $derived(what || fallback);
</script>

{#if text || date}
	<span class="relative inline-block align-middle">
		<button
			type="button"
			class="ml-0.5 inline-flex h-5 w-5 items-center justify-center text-xs text-fg-muted"
			aria-label="{label} 설명 보기"
			aria-expanded={open}
			onclick={toggle}>ⓘ</button
		>
		{#if open}
			<span
				class="absolute left-0 top-6 z-20 w-56 rounded-md border border-border-subtle bg-surface-3 p-2 text-xs font-normal text-fg-primary shadow"
				role="status">{text ?? '설명 준비 중이에요.'}</span
			>
		{/if}
	</span>
{/if}
