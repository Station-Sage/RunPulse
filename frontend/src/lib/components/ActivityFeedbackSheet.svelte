<script lang="ts">
	import { say } from '$lib/a11y/say';
	// U15d — 활동별 RPE·통증·메모 입력(ADR-022). 저장은 PUT, 전부 비우면 서버가 삭제한다.
	import type { ActivityFeedback, PainLevel } from '$lib/types';
	import ToggleGroup from '$lib/components/ui/ToggleGroup.svelte';
	import TextField from '$lib/components/ui/TextField.svelte';
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
	<ToggleGroup
		label="운동 강도 체감 (1 매우 쉬움 ~ 10 최대)"
		items={RPE.map((n) => ({ value: String(n), label: String(n) }))}
		selected={rpe == null ? null : String(rpe)}
		onchange={(v) => (rpe = v == null ? null : Number(v))}
		clearable
		class="grid grid-cols-5 gap-1"
	/>
	<div class="-mt-2 flex justify-between text-xs text-fg-muted" aria-hidden="true"><span>1 매우 쉬움</span><span>10 최대</span></div>
	<ToggleGroup
		label="통증 수준"
		items={PAIN}
		selected={pain}
		onchange={(v) => (pain = v as PainLevel | null)}
		clearable
	/>
	{#if showSites}
		<p class="text-xs text-fg-muted">아픈 부위 (최대 3곳)</p>
		<ToggleGroup
			mode="multi"
			label="아픈 부위 (최대 3곳)"
			items={SITES.map(([value, label]) => ({ value, label, disabled: sites.length >= 3 && !sites.includes(value) }))}
			selected={sites}
			onchange={(v) => (sites = v as string[])}
		/>
	{/if}
	<TextField label="메모" labelHidden multiline bind:value={note} maxlength={500} rows={2} placeholder="메모 (선택, 500자)"
		class="w-full rounded border border-border-subtle bg-surface-1 px-2 py-1.5 text-sm text-fg-primary placeholder:text-fg-muted" />
	{#if error}<p class="text-xs text-semantic-red" use:say={{ text: error, level: 'assertive' }}>{error}</p>{/if}
	<div class="flex justify-end">
		<button type="button" onclick={save} disabled={saving}
			class="h-11 rounded bg-semantic-teal px-5 text-sm font-medium text-fg-on-accent disabled:opacity-60">{saving ? '저장 중…' : '저장'}</button>
	</div>
</div>
