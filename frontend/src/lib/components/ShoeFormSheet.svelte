<script lang="ts">
	// 신발 추가·수정 폼(V2-SHOES). 저장 실패는 시트 안 인라인 오류 — 400/409 는 서버 문구, 그 외 failureMessage.
	import { say } from '$lib/a11y/say';
	import { createShoe, updateShoe, type Shoe, type ShoeDetail } from '$lib/api/shoes';
	import { CATEGORY_OPTIONS, KIND_OPTIONS, emptyForm, formToInput, shoeWriteError, validateShoeForm } from '$lib/shoeView';
	import TextField from '$lib/components/ui/TextField.svelte';
	import ToggleGroup from '$lib/components/ui/ToggleGroup.svelte';

	let { shoe = null, onSaved, onClose }: {
		shoe?: Shoe | null;
		onSaved?: (s: ShoeDetail) => void;
		onClose?: () => void;
	} = $props();

	// svelte-ignore state_referenced_locally
	let form = $state(emptyForm(shoe));
	let errors = $state<Record<string, string>>({});
	let saving = $state(false);
	let error = $state('');
	const input = 'w-full rounded border border-border-subtle bg-surface-1 px-2 py-1.5 text-sm text-fg-primary';

	async function save() {
		errors = validateShoeForm(form);
		if (Object.keys(errors).length) return;
		saving = true;
		error = '';
		try {
			const body = formToInput(form);
			const saved = shoe ? await updateShoe(shoe.id, body) : await createShoe(body);
			onSaved?.(saved);
			onClose?.();
		} catch (e) {
			error = shoeWriteError(e);
		} finally {
			saving = false;
		}
	}
</script>

<form class="flex flex-col gap-3 rounded-lg border border-border-subtle bg-surface-2 p-4" data-testid="shoe-form"
	onsubmit={(e) => { e.preventDefault(); save(); }}>
	<div class="flex items-center justify-between">
		<p class="text-sm font-medium text-fg-primary">{shoe ? '신발 수정' : '신발 추가'}</p>
		<button type="button" onclick={onClose} class="h-11 px-2 text-xs text-fg-muted hover:text-fg-primary">닫기</button>
	</div>
	<div>
		<TextField label="이름 (별명)" bind:value={form.name} maxlength={60} class={input} aria-invalid={!!errors.name} />
		{#if errors.name}<p class="mt-1 text-xs text-semantic-red">{errors.name}</p>{/if}
	</div>
	<div class="grid grid-cols-2 gap-2">
		<div><TextField label="브랜드" bind:value={form.brand} maxlength={60} class={input} /></div>
		<div><TextField label="모델" bind:value={form.model} maxlength={60} class={input} /></div>
	</div>
	<p class="text-xs text-fg-secondary">카테고리</p>
	<ToggleGroup label="카테고리" items={CATEGORY_OPTIONS} selected={form.category}
		onchange={(v) => (form.category = (v as typeof form.category) ?? 'daily')} />
	<div class="grid grid-cols-2 gap-2">
		<div><TextField label="개시일" type="date" bind:value={form.start_date} class={input} /></div>
		<div>
			<TextField label="시작 거리 (km)" inputmode="decimal" bind:value={form.initial_km} class={input} aria-invalid={!!errors.initial_km} />
			{#if errors.initial_km}<p class="mt-1 text-xs text-semantic-red">{errors.initial_km}</p>{/if}
		</div>
	</div>
	<div>
		<TextField label="교체 기준 (km, 비우면 카테고리 기본값)" inputmode="numeric" bind:value={form.retire_km} class={input} aria-invalid={!!errors.retire_km} />
		{#if errors.retire_km}<p class="mt-1 text-xs text-semantic-red">{errors.retire_km}</p>{/if}
	</div>
	<p class="text-xs text-fg-secondary">기본 신발 (이 종류 러닝에 자동 배정, 지정일 이후부터)</p>
	<ToggleGroup label="기본 신발 종류" items={KIND_OPTIONS} selected={form.default_for || null} clearable
		onchange={(v) => (form.default_for = (v as typeof form.default_for) ?? '')} />
	<TextField label="메모" labelHidden multiline bind:value={form.notes} maxlength={500} rows={2} placeholder="메모 (선택, 500자)" class={input} />
	{#if error}<p class="text-xs text-semantic-red" data-testid="shoe-form-error" use:say={{ text: error, level: 'assertive' }}>{error}</p>{/if}
	<div class="flex justify-end">
		<button type="submit" disabled={saving}
			class="h-11 rounded bg-semantic-teal px-5 text-sm font-medium text-fg-on-accent disabled:opacity-60">{saving ? '저장 중…' : '저장'}</button>
	</div>
</form>
