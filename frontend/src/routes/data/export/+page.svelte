<svelte:head><title>내보내기 · RunPulse</title></svelte:head>

<div class="flex flex-col gap-3 px-4 py-4">
	<a
		href="/activities/export.csv"
		data-sveltekit-reload
		class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3 hover:bg-surface-3"
	>
		<span class="text-sm text-fg-primary">활동 CSV</span>
		<span class="text-xs text-fg-secondary">모든 소스의 러닝 활동을 한 파일로 받아요.</span>
	</a>
	<a
		href="/training/export.ics"
		data-sveltekit-reload
		class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3 hover:bg-surface-3"
	>
		<span class="text-sm text-fg-primary">훈련 계획 캘린더 (.ics)</span>
		<span class="text-xs text-fg-secondary">현재 계획을 캘린더 앱으로 가져갈 수 있어요.</span>
	</a>
	<p class="text-xs text-fg-secondary">웰니스·부하 CSV와 전체 아카이브는 준비 중이에요.</p>
</div>
