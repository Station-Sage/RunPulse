// scripts/route-preload.mjs(빌드 후처리) + lib/api/bootPrefetch.ts — 첫 로드 라우트 청크 preload·API 선요청 (S4-90).
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync, readdirSync } from 'node:fs';
import {
	parseNodeFile, templateToGroups, buildRouteTable, renderInlineScript, injectIntoHtml, preloadedFiles, MARKER
} from '../scripts/route-preload.mjs';
import { BOOT_ALWAYS, BOOT_ROUTES } from '../scripts/bootPrefetchRoutes.mjs';
import { takeBootResponse, clearBootPrefetch, BOOT_KEY, BOOT_MAX_AGE_MS } from '../src/lib/api/bootPrefetch.ts';

const IM = '_app/immutable/';
const NODES = {
	0: { imports: [`${IM}nodes/0.js`, `${IM}chunks/shared.js`], stylesheets: [`${IM}assets/0.css`] },
	1: { imports: [`${IM}nodes/1.js`], stylesheets: [] },
	5: { imports: [`${IM}nodes/5.js`, `${IM}chunks/shared.js`, `${IM}chunks/today.js`], stylesheets: [`${IM}assets/5.css`] },
	6: { imports: [`${IM}nodes/6.js`, `${IM}chunks/act.js`], stylesheets: [] },
	7: { imports: [`${IM}nodes/7.js`], stylesheets: [] }
};
const P = (name) => ({ name, optional: false, rest: false, chained: false });
const ROUTES = [
	{ id: '/today', pattern: /^\/today\/?$/, params: [], page: { layouts: [0], errors: [1], leaf: 5 } },
	{ id: '/library/activities', pattern: /^\/library\/activities\/?$/, params: [], page: { layouts: [0], errors: [1], leaf: 7 } },
	{ id: '/library/[id]', pattern: /^\/library\/([^/]+?)\/?$/, params: [P('id')], page: { layouts: [0, 6], errors: [1, undefined], leaf: 7 } },
	{ id: '/api-ish', pattern: /^\/x\/?$/, params: [], page: null }
];
const SKIP = new Set([`${IM}nodes/0.js`, `${IM}chunks/shared.js`, `${IM}assets/0.css`]);
const API = { '/today': ['/today'], '/library/[id]': ['/library/activities/{id}'] };

function table() {
	return buildRouteTable(ROUTES, (i) => NODES[i], SKIP, API);
}

/** 인라인 스크립트를 가짜 DOM 에서 실행 — 걸린 link 와 fetch 호출을 돌려준다. */
function run(pathname, { demo = false } = {}) {
	const { files, table: t } = table();
	const src = renderInlineScript({ base: '/v2', files, table: t, always: ['/auth/session'] });
	const links = [];
	const fetches = [];
	const win = {};
	const ctx = {
		window: win, location: { pathname }, performance: { now: () => 5 },
		sessionStorage: { getItem: (k) => (demo && k === 'runpulse.demo' ? '1' : null) },
		document: { createElement: () => ({}), head: { appendChild: (l) => links.push(l) } },
		fetch: (url, init) => { fetches.push([url, init]); return Promise.resolve({ ok: true }); }
	};
	vm.runInNewContext(src, ctx);
	return { links, fetches, win };
}

test('parseNodeFile: imports·stylesheets 배열만 읽는다(실행하지 않음)', () => {
	const text = 'export const index = 3;\nexport const imports = ["a.js","b.js"];\nexport const stylesheets = ["c.css"];\nexport const fonts = [];';
	assert.deepEqual(parseNodeFile(text), { imports: ['a.js', 'b.js'], stylesheets: ['c.css'] });
	assert.deepEqual(parseNodeFile('export const index = 1;'), { imports: [], stylesheets: [] });
});

test('templateToGroups: 파라미터 이름 → 그룹 번호, 모르는 이름은 null', () => {
	assert.equal(templateToGroups('/coach/plan/{id}', [P('id')]), '/coach/plan/{1}');
	assert.equal(templateToGroups('/a/{x}/{id}', [P('id'), P('x')]), '/a/{2}/{1}');
	assert.equal(templateToGroups('/a/{nope}', [P('id')]), null);
	assert.equal(templateToGroups('/today', []), '/today');
});

test('buildRouteTable: 페이지 없는 라우트 제외, HTML 이 이미 거는 레이아웃 파일 제외·중복 제거', () => {
	const { files, table: t } = table();
	assert.equal(t.length, 3);
	const today = t[0];
	assert.equal(today[0], '^\\/today\\/?$');
	assert.deepEqual(today[1].map((i) => files[i]), [`${IM}nodes/5.js`, `${IM}chunks/today.js`, `${IM}assets/5.css`]);
	assert.deepEqual(today[2], ['/today']);
	assert.deepEqual(t[2][2], ['/library/activities/{1}']);
	assert.equal(new Set(files).size, files.length);
	assert.ok(!files.some((f) => SKIP.has(f)));
});

test('인라인 스크립트: 경로에 맞는 청크(+CSS preload)와 API 를 건다', () => {
	const { links, fetches, win } = run('/v2/today');
	assert.deepEqual(links.map((l) => [l.rel, l.href]), [
		['modulepreload', `/v2/${IM}nodes/5.js`], ['modulepreload', `/v2/${IM}chunks/today.js`], ['preload', `/v2/${IM}assets/5.css`]
	]);
	assert.equal(links[2].as, 'style');
	assert.deepEqual(fetches.map((f) => f[0]), ['/api/v1/auth/session', '/api/v1/today']);
	assert.equal(JSON.stringify(fetches[0][1]), JSON.stringify({ headers: { 'Content-Type': 'application/json' }, redirect: 'manual' }));
	assert.equal(JSON.stringify(Object.keys(win.__rpBoot)), JSON.stringify(['/auth/session', '/today']));
	assert.equal(win.__rpBoot['/today'].t, 5);
});

test('인라인 스크립트: 먼저 맞는 라우트 하나만, 숫자 아닌 파라미터는 API 선요청 안 함', () => {
	const act = run('/v2/library/100');
	assert.deepEqual(act.fetches.map((f) => f[0]), ['/api/v1/auth/session', '/api/v1/library/activities/100']);
	assert.ok(act.links.some((l) => l.href.endsWith('chunks/act.js')));
	const list = run('/v2/library/activities');
	assert.deepEqual(list.fetches.map((f) => f[0]), ['/api/v1/auth/session']);
	assert.ok(!list.links.some((l) => l.href.endsWith('chunks/act.js')));
	const bad = run('/v2/library/abc');
	assert.deepEqual(bad.fetches.map((f) => f[0]), ['/api/v1/auth/session']);
});

test('인라인 스크립트: 데모 중엔 API 선요청 없음(스냅샷 fetch 층 우회 방지), 청크 preload 는 유지', () => {
	const { links, fetches, win } = run('/v2/today', { demo: true });
	assert.equal(fetches.length, 0);
	assert.equal(win.__rpBoot, undefined);
	assert.ok(links.length > 0);
});

test('injectIntoHtml: 첫 stylesheet 앞에 넣고 다시 돌려도 하나만(멱등)', () => {
	const html = '<head>\n\t\t<script src="/v2/theme-init.js"></script>\n\t\t<link href="/v2/a.js" rel="modulepreload">\n\t\t<link href="/v2/x.css" rel="stylesheet">\n</head>';
	const once = injectIntoHtml(html, 'A()');
	assert.ok(once.indexOf(`<script ${MARKER}>A()</script>`) < once.indexOf('x.css'));
	assert.ok(once.indexOf('theme-init') < once.indexOf(MARKER));
	const twice = injectIntoHtml(once, 'B()');
	assert.equal(twice.split(MARKER).length, 2);
	assert.ok(twice.includes('B()') && !twice.includes('A()'));
	assert.throws(() => injectIntoHtml('<head></head>', 'A()'));
});

test('preloadedFiles: HTML 이 거는 modulepreload·stylesheet 를 base 없이', () => {
	const html = '<link href="/v2/_app/a.js" rel="modulepreload"><link href="/v2/_app/b.css" rel="stylesheet"><link href="/v2/f.ico" rel="icon">';
	assert.deepEqual([...preloadedFiles(html, '/v2')], ['_app/a.js', '_app/b.css']);
});

test('선요청 표의 경로는 lib/api 의 apiFetch 경로와 글자 그대로 같다(다르면 apiFetch 가 넘겨받지 못함)', () => {
	const src = ['api', 'auth'].flatMap((d) => {
		const dir = new URL(`../src/lib/${d}/`, import.meta.url);
		return readdirSync(dir).filter((f) => f.endsWith('.ts')).map((f) => readFileSync(new URL(f, dir), 'utf8'));
	}).join('\n');
	for (const path of [...BOOT_ALWAYS, ...Object.values(BOOT_ROUTES).flat()]) {
		const literal = path.includes('{') ? `\`${path.replace(/\{\w+\}/g, '${')}` : `'${path}'`;
		assert.ok(src.includes(literal), `${path} 가 lib/api 에 없음`);
	}
	const demo = readFileSync(new URL('../src/lib/demoMode.ts', import.meta.url), 'utf8');
	assert.match(demo, /export const DEMO_FLAG = 'runpulse\.demo'/);
	const client = readFileSync(new URL('../src/lib/api/client.ts', import.meta.url), 'utf8');
	assert.match(client, /const API_BASE = '\/api\/v1'/);
});

test('takeBootResponse: 1회용, init 지정·오래된 항목·상자 없음이면 null', async () => {
	const res = Promise.resolve({ ok: true });
	const host = { [BOOT_KEY]: { '/today': { p: res, t: 0 }, '/old': { p: res, t: 0 } } };
	assert.equal(takeBootResponse('/today', { method: 'POST' }, host, 10), null);
	assert.equal(takeBootResponse('/today', undefined, host, 10), res);
	assert.equal(takeBootResponse('/today', undefined, host, 10), null);
	assert.equal(takeBootResponse('/old', undefined, host, BOOT_MAX_AGE_MS + 1), null);
	assert.equal(takeBootResponse('/x', undefined, {}, 0), null);
	clearBootPrefetch(host);
	assert.equal(host[BOOT_KEY], undefined);
});
