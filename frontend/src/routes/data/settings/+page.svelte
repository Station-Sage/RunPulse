<svelte:head><title>데이터 설정 · RunPulse</title></svelte:head>

<div class="flex flex-col gap-3 px-4 py-4">
	<a
		href="/data/sources"
		class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3 hover:bg-surface-3"
	>
		<span class="text-sm text-fg-primary">소스 연결·자동 동기화</span>
		<span class="text-xs text-fg-secondary">소스별 연결, 켜기/끄기, 자동 동기화 주기를 바꿔요.</span>
	</a>
	<a
		href="/data/settings/profile"
		class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3 hover:bg-surface-3"
	>
		<span class="text-sm text-fg-primary">러너 기준값</span>
		<span class="text-xs text-fg-secondary">최대심박·역치 페이스 등을 자체 추정/기기 값/직접 입력 중에서 골라요.</span>
	</a>
	<a
		href="/data/settings/ai"
		class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3 hover:bg-surface-3"
	>
		<span class="text-sm text-fg-primary">AI 설정</span>
		<span class="text-xs text-fg-secondary">제공자·API 키·AI에 보내는 데이터 범위와 최근 사용량을 봐요.</span>
	</a>
</div>
