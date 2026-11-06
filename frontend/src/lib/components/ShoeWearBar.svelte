<script lang="ts">
	// 신발 마모 막대(V2-SHOES) — role="meter" + aria-valuenow/max + 상태 문구(색만으로 전달 금지).
	import type { ShoeStatus } from '$lib/api/shoes';
	import { statusMeta, wearPercent } from '$lib/shoeView';

	let { mileage, retire, status, label }: { mileage: number; retire: number; status: ShoeStatus; label: string } =
		$props();

	const meta = $derived(statusMeta(status));
	const pct = $derived(Math.min(100, wearPercent(mileage, retire)));
</script>

<div
	role="meter"
	aria-label="{label} 마모"
	aria-valuemin={0}
	aria-valuemax={retire}
	aria-valuenow={Math.round(mileage)}
	aria-valuetext="{Math.round(mileage)} / {retire} km, {meta.label}"
	class="h-2 w-full overflow-hidden rounded bg-surface-3"
>
	<div class="h-2 rounded {meta.bar}" style="width:{pct}%"></div>
</div>
