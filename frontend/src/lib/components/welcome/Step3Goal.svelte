<script lang="ts">
	// 3/4 목표 대회(선택) — 기존 계획 생성 마법사를 재사용한다.
	import { base } from '$app/paths';
</script>

<div class="flex flex-col gap-3">
	<h2 class="text-base font-semibold text-fg-primary">3/4 · 목표 대회 (선택)</h2>
	<p class="text-sm text-fg-secondary">목표 대회가 있으면 훈련 계획을 만들어 드려요. 나중에 해도 돼요.</p>
	<a class="text-sm underline" href="{base}/coach/plan/new">목표 대회 정하기 ↗</a>
</div>
