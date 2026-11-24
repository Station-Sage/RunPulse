// PageHead heading={null} 허용목록 계약 — null 은 "자식이 h1 을 그린다"는 약속이므로 목록에 없는 라우트는 금지(ratchet).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

function walk(dir, out = []) {
	for (const n of readdirSync(dir)) {
		const p = join(dir, n);
		if (statSync(p).isDirectory()) walk(p, out);
		else if (/\+(page|error)\.svelte$/.test(p)) out.push(p);
	}
	return out;
}
const routes = walk('src/routes');
const NULL_HEADING = /<PageHead(?:er)?\b[^>]*heading=\{null\}/;

// 무조건 null 허용 라우트 — 줄어들 수만 있다. today 는 분기별(pageHeading)이라 여기 없다.
const ALLOWED = new Set([
	'src/routes/coach/+page.svelte',
	'src/routes/coach/[threadId]/+page.svelte',
	'src/routes/coach/new/+page.svelte',
	'src/routes/coach/plan/+page.svelte',
	'src/routes/coach/plan/[id]/+page.svelte',
	'src/routes/coach/plan/compare/+page.svelte',
	'src/routes/data/+page.svelte',
	'src/routes/data/export/+page.svelte',
	'src/routes/data/import/+page.svelte',
	'src/routes/data/settings/+page.svelte',
	'src/routes/data/settings/ai/+page.svelte',
	'src/routes/data/settings/profile/+page.svelte',
	'src/routes/data/sources/+page.svelte',
	'src/routes/data/sources/[provider]/+page.svelte',
	'src/routes/data/sync/+page.svelte',
	'src/routes/demo/+page.svelte',
	'src/routes/library/+page.svelte',
	'src/routes/library/[id]/laps/+page.svelte',
	'src/routes/library/[id]/metrics/+page.svelte',
	'src/routes/library/[id]/providers/+page.svelte',
	'src/routes/library/[id]/streams/+page.svelte',
	'src/routes/library/activities/+page.svelte',
	'src/routes/library/balance/+page.svelte',
	'src/routes/library/metrics/+page.svelte',
	'src/routes/library/metrics/[slug]/+page.svelte',
	'src/routes/library/milestones/+page.svelte',
	'src/routes/library/providers/+page.svelte',
	'src/routes/library/providers/[group]/+page.svelte',
	'src/routes/library/shoes/+page.svelte',
	'src/routes/library/shoes/[id]/+page.svelte',
	'src/routes/library/wellness/[date]/+page.svelte',
	'src/routes/today/month/[ym]/+page.svelte',
	'src/routes/welcome/+page.svelte'
]);

test('heading={null} 은 허용목록 라우트에만', () => {
	const nulls = routes.filter((f) => NULL_HEADING.test(readFileSync(f, 'utf8'))).sort();
	assert.deepEqual(nulls.filter((f) => !ALLOWED.has(f)), [], '새 heading={null} — pageHeading 으로 분기하거나 근거와 함께 허용목록에 추가');
	assert.deepEqual([...ALLOWED].filter((f) => !nulls.includes(f)).sort(), [], '개선됨 — 허용목록에서 제거');
});

test('today: pageHeading(childOwns=[ok]) 로 empty·failed 가 보이는 h1 소유', () => {
	const s = readFileSync('src/routes/today/+page.svelte', 'utf8');
	assert.match(s, /import \{ pageHeading \} from '\$lib\/a11y\/pageHeading'/);
	assert.match(s, /<PageHead title="Today" heading=\{pageHeading\([^}]*'Today', \['ok'\]\)\}/);
	assert.doesNotMatch(s, /<PageHead[^>]*heading=\{null\}/);
});

test('library/[id]: 활동 없음 분기는 PageHead 가 보이는 h1 소유(ok 만 레이아웃 위임)', () => {
	const s = readFileSync('src/routes/library/[id]/+page.svelte', 'utf8');
	assert.match(s, /import \{ pageHeading \} from '\$lib\/a11y\/pageHeading'/);
	assert.match(s, /heading=\{pageHeading\(core \? 'ok' : 'failed', '활동 상세', \['ok'\]\)\}/);
	assert.doesNotMatch(s, /<PageHead[^>]*heading=\{null\}/);
});
