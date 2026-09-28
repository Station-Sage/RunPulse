<script lang="ts">
	// §7.1(40-v2-unimplemented/design.md) — Library·Data 공용 서브탭. 44px, 가로 스크롤,
	// aria-current. F-UI-09 "서브탭 복제" 방지 — 소비 화면은 이 컴포넌트 하나만 쓴다.
	let {
		tabs,
		current
	}: {
		tabs: { href: string; label: string }[];
		current: string;
	} = $props();
</script>

<nav
	aria-label="하위 메뉴"
	class="flex overflow-x-auto border-b border-border-subtle [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
>
	{#each tabs as tab (tab.href)}
		<a
			href={tab.href}
			aria-current={current === tab.href ? 'page' : undefined}
			class="flex h-11 shrink-0 items-center border-b-2 px-3 text-sm whitespace-nowrap {current ===
			tab.href
				? 'border-fg-primary font-medium text-fg-primary'
				: 'border-transparent text-fg-muted hover:text-fg-secondary'}"
		>
			{tab.label}
		</a>
	{/each}
</nav>
