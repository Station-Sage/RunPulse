<script lang="ts">
	// U15d — 활동별 RPE·통증·메모 입력(ADR-022). 저장은 PUT, 전부 비우면 서버가 삭제한다.
	import type { ActivityFeedback, PainLevel } from '$lib/types';
	import { putActivityFeedback } from '$lib/api/activityFeedback';

	let { activityId, existing = null, onSaved, onClose }: {
		activityId: number;
		existing?: ActivityFeedback | null;
		onSaved?: (fb: ActivityFeedback | null) => void;
		onClose?: () => void;
	} = $props();

	const RPE = Array.from({ length: 10 }, (_, i) => i + 1);
	const PAIN: { value: PainLevel; label: string }[] = [
		{ value: 'none', label: '없음' }, { value: 'mild', label: '경미' },
		{ value: 'moderate', label: '중간' }, { value: 'severe', label: '심함' }
	];
	const SITES: [string, string][] = [
		['foot', '발'], ['ankle', '발목'], ['achilles', '아킬레스'], ['calf', '종아리'],
		['shin', '정강이'], ['knee', '무릎'], ['it_band', '장경인대'], ['hamstring', '햄스트링'],
		['quad', '허벅지 앞'], ['hip', '고관절'], ['lower_back', '허리'], ['other', '기타']
	];

	let rpe = $state<number | null>(existing?.rpe ?? null);
	let pain = $state<PainLevel | null>(existing?.pain ?? null);
	let sites = $state<string[]>(existing?.pain_sites ?? []);
	let note = $state(existing?.note ?? '');
	let saving = $state(false);
	let error = $state('');

	const showSites = $derived(pain != null && pain !== 'none');

	function toggleSite(s: string) {
		if (sites.includes(s)) sites = sites.filter((x) => x !== s);
		else if (sites.length < 3) sites = [...sites, s];
	}

	async function save() {
		saving = true;
		error = '';
		try {
			const fb = await putActivityFeedback(activityId, {
				rpe, pain, pain_sites: showSites ? sites : [], note: note.trim() || null
			});
			onSaved?.(fb);
			onClose?.();
		} catch {
			error = '저장하지 못했어요. 잠시 후 다시 시도해 주세요.';
		} finally {
			saving = false;
		}
	}
</script>

<div class="flex flex-col gap-3 rounded-lg border border-border-subtle bg-surface-2 p-4" data-testid="activity-feedback-sheet">
	<div class="flex items-center justify-between">
		<p class="text-sm font-medium text-fg-primary">이 운동은 어땠나요?</p>
		<button type="button" onclick={onClose} class="h-11 px-2 text-xs text-fg-muted hover:text-fg-primary">닫기</button>
	</div>
	<p class="text-xs text-fg-muted">운동 강도 체감(RPE)</p>
	<div role="radiogroup" aria-label="운동 강도 체감 (1 매우 쉬움 ~ 10 최대)" class="grid grid-cols-10 gap-1">
		{#each RPE as n (n)}
			<button type="button" aria-pressed={rpe === n} aria-label={`RPE ${n}`}
				onclick={() => (rpe = rpe === n ? null : n)}
				class="h-11 rounded border border-border-subtle text-sm {rpe === n ? 'bg-semantic-teal text-white' : 'bg-surface-1 text-fg-secondary hover:bg-surface-3'}">{n}</button>
		{/each}
	</div>
	<div class="-mt-2 flex justify-between text-xs text-fg-muted" aria-hidden="true"><span>1 매우 쉬움</span><span>10 최대</span></div>
	<div role="radiogroup" aria-label="통증 수준" class="flex flex-wrap gap-1">
		{#each PAIN as p (p.value)}
			<button type="button" aria-pressed={pain === p.value} onclick={() => (pain = pain === p.value ? null : p.value)}
				class="h-11 rounded border border-border-subtle px-3 text-sm {pain === p.value ? 'bg-semantic-amber text-white' : 'bg-surface-1 text-fg-secondary hover:bg-surface-3'}">{p.label}</button>
		{/each}
	</div>
	{#if showSites}
		<p class="text-xs text-fg-muted">아픈 부위 (최대 3곳)</p>
		<div class="flex flex-wrap gap-1">
			{#each SITES as [slug, label] (slug)}
				<button type="button" aria-pressed={sites.includes(slug)} onclick={() => toggleSite(slug)}
					class="h-11 rounded-full border border-border-subtle px-3 text-sm {sites.includes(slug) ? 'bg-semantic-amber text-white' : 'bg-surface-1 text-fg-secondary hover:bg-surface-3'}">{label}</button>
			{/each}
		</div>
	{/if}
	<textarea bind:value={note} maxlength="500" rows="2" placeholder="메모 (선택, 500자)"
		class="rounded border border-border-subtle bg-surface-1 px-2 py-1.5 text-sm text-fg-primary placeholder:text-fg-muted"></textarea>
	{#if error}<p class="text-xs text-semantic-red" role="alert">{error}</p>{/if}
	<div class="flex justify-end">
		<button type="button" onclick={save} disabled={saving}
			class="h-11 rounded bg-semantic-teal px-5 text-sm font-medium text-white disabled:opacity-60">{saving ? '저장 중…' : '저장'}</button>
	</div>
</div>
