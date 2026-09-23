<script lang="ts">
	// 03e-coach.md 5-C — 플랜 없음 화면.
	import type { PlanGatewayData } from './+page';
	import { base } from '$app/paths';

	let { data }: { data: PlanGatewayData } = $props();
</script>

<div class="flex flex-col items-center justify-center gap-6 px-4 py-16 text-center">
	<div>
		<p class="text-base text-fg-secondary">
			목표 레이스를 입력하면 맞춤 프로그램을 만들어드립니다.
		</p>
		{#if data.ctlCurrent != null}
			<p class="mt-2 text-sm text-fg-muted">
				현재 피트니스 수준: CTL {Math.round(data.ctlCurrent)} (분석 완료)
			</p>
		{/if}
	</div>

	<a
		href="{base}/coach/plan/new"
		class="rounded-lg bg-fg-primary px-6 py-3 text-sm font-medium text-surface-1"
	>
		새 프로그램 만들기 →
	</a>
</div>
