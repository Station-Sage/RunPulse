<script lang="ts">
	import { patchAiSettings, testAiConnection, type AiPatch, type AiSettings } from '$lib/api/data';
	import { engineSummary, keyStateText, providerName, usageText } from '$lib/aiSettings';
	import type { AiPageData } from './+page';

	let { data }: { data: AiPageData } = $props();
	let s = $state<AiSettings | null>(data.settings);
	let drafts = $state<Record<string, string>>({});
	let results = $state<Record<string, string>>({});
	let message = $state('');
	let busy = $state(false);

	async function save(patch: AiPatch) {
		busy = true;
		message = '';
		try {
			s = await patchAiSettings(patch);
			drafts = {};
			message = '저장했어요';
		} catch (e) {
			message = e instanceof Error ? e.message : '저장하지 못했어요';
		} finally {
			busy = false;
		}
	}

	async function test(p: string) {
		results[p] = '확인 중…';
		try {
			const r = await testAiConnection(p);
			results[p] = r.ok ? r.label : `실패 · ${r.label}`;
		} catch (e) {
			results[p] = e instanceof Error ? e.message : '확인하지 못했어요';
		}
	}
</script>

<svelte:head><title>AI 설정 · RunPulse</title></svelte:head>

{#if !s}
	<p class="px-4 py-6 text-sm text-fg-secondary">AI 설정을 불러오지 못했어요. 잠시 뒤 다시 열어 주세요.</p>
{:else}
	<div class="flex flex-col gap-4 px-4 py-4">
		<section class="rounded-lg border border-border-subtle bg-surface-2 p-3">
			<h2 class="text-sm text-fg-primary">지금 Coach 답변 방식</h2>
			<p class="mt-1 text-sm text-fg-primary">{engineSummary(s)}</p>
			<p class="mt-1 text-xs text-fg-secondary">{usageText(s.usage_7d)}</p>
		</section>

		<section class="flex flex-col gap-2">
			<h2 class="text-sm text-fg-primary">AI 제공자</h2>
			<label class="flex items-center gap-2 text-sm text-fg-primary">
				<input type="radio" name="prov" checked={s.provider === 'rule'} disabled={busy}
					onchange={() => save({ provider: 'rule' })} />
				사용 안 함 (규칙 기반)
			</label>
			{#each s.providers as p (p.provider)}
				<div class="rounded-lg border border-border-subtle bg-surface-2 p-3">
					<label class="flex items-center gap-2 text-sm text-fg-primary">
						<input type="radio" name="prov" checked={s.provider === p.provider}
							disabled={busy || p.key_state === 'missing'} onchange={() => save({ provider: p.provider })} />
						{providerName(p.provider)}
						<span class="text-xs text-fg-secondary">{p.model}</span>
					</label>
					<p class="mt-1 text-xs text-fg-secondary">
						{keyStateText(p.key_state)}{p.key_mask ? ` · ${p.key_mask}` : ''}
					</p>
					<div class="mt-2 flex gap-2">
						<input type="password" autocomplete="off" placeholder="새 API 키" bind:value={drafts[p.provider]}
							class="min-w-0 flex-1 rounded border border-border-subtle bg-surface-1 px-2 py-1 text-sm" />
						<button class="rounded border border-border-subtle px-2 py-1 text-sm disabled:opacity-40"
							disabled={busy || !drafts[p.provider]?.trim()}
							onclick={() => save({ keys: { [p.provider]: drafts[p.provider] } })}>저장</button>
						<button class="rounded border border-border-subtle px-2 py-1 text-sm disabled:opacity-40"
							disabled={p.key_state === 'missing'} onclick={() => test(p.provider)}>연결 테스트</button>
					</div>
					{#if results[p.provider]}<p class="mt-1 text-xs text-fg-secondary">{results[p.provider]}</p>{/if}
				</div>
			{/each}
			<label class="flex items-center gap-2 text-sm text-fg-primary">
				<input type="checkbox" checked={s.fallback_enabled} disabled={busy || s.provider === 'rule'}
					onchange={(e) => save({ fallback_enabled: e.currentTarget.checked })} />
				선택한 제공자가 실패하면 키가 있는 다른 제공자로 대신 답하기
			</label>
		</section>

		<section class="flex flex-col gap-2">
			<h2 class="text-sm text-fg-primary">AI에 보내는 데이터</h2>
			<p class="text-xs text-fg-secondary">GPS 경로와 원본 위치 기록은 보내지 않아요.</p>
			<ul class="flex flex-col gap-1">
				{#each s.scope as it (it.item)}
					<li class="flex items-center gap-2 text-sm text-fg-primary">
						{#if it.optional}
							<input type="checkbox" checked={it.enabled} disabled={busy || s.provider === 'rule'}
								onchange={(e) => save({ exclude_notes: !e.currentTarget.checked })} />
						{:else}
							<input type="checkbox" checked disabled />
						{/if}
						<span>{it.item}</span>
						<span class="text-xs text-fg-secondary">{it.period}</span>
					</li>
				{/each}
			</ul>
		</section>

		{#if message}<p class="text-xs text-fg-secondary" role="status">{message}</p>{/if}
		<a href="/data/settings" class="text-xs text-fg-secondary underline">데이터 설정으로</a>
	</div>
{/if}
