// 빌드 후처리(S4-90) — SPA fallback(build/index.html)에 "라우트 청크 조기 preload + 핵심 API 선요청" 인라인 스크립트를 넣는다.
// 배경: cwv-measurement-2026-11.md — fallback HTML 엔 레이아웃 청크만 modulepreload 되고 라우트(페이지) 노드 청크는
// 라우터 실행 뒤 2차 웨이브로 받는다. 그다음 API(인증 세션·페이지 데이터)가 또 한 번 왕복 → 모바일 LCP 직렬 5단계.
// 이 스크립트는 HTML 파싱 시점에 현재 경로에 맞는 노드 청크(+CSS)를 preload 하고, BOOT_ROUTES 의 GET 을 미리 쏴
// window.__rpBoot 에 둔다(lib/api/bootPrefetch.ts 가 apiFetch 에서 1회 넘겨받음).
// CSP: 인라인 스크립트 해시는 서버가 build/index.html 에서 매번 계산한다(src/web/spa_static.inline_script_hashes).
// 입력은 SvelteKit 서버 산출물(.svelte-kit/output/server/manifest.js·nodes/N.js) — 노드 파일은 실행하지 않고 글자로 읽는다.
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { BOOT_ALWAYS, BOOT_ROUTES } from './bootPrefetchRoutes.mjs';

export const MARKER = 'data-rp-preload';
const DEMO_FLAG = 'runpulse.demo'; // lib/demoMode.ts DEMO_FLAG 와 같아야 한다(테스트 대조)
const API_BASE = '/api/v1'; // lib/api/client.ts API_BASE
const IMMUTABLE = '_app/immutable/';

/** nodes/N.js 글자에서 imports·stylesheets 배열을 읽는다. */
export function parseNodeFile(text) {
	const arr = (name) => {
		const m = text.match(new RegExp(`export const ${name} = (\\[[^\\]]*\\]);`));
		return m ? JSON.parse(m[1]) : [];
	};
	return { imports: arr('imports'), stylesheets: arr('stylesheets') };
}

/** API 경로 템플릿의 `{name}` 을 정규식 그룹 번호 `{n}`(1부터)로 바꾼다. 모르는 이름이면 null(그 경로는 버린다). */
export function templateToGroups(tpl, params) {
	let ok = true;
	const out = tpl.replace(/\{([a-zA-Z_]\w*)\}/g, (_, name) => {
		const i = params.findIndex((p) => p.name === name);
		if (i < 0) ok = false;
		return `{${i + 1}}`;
	});
	return ok ? out : null;
}

/**
 * 라우트 표 생성. routes = manifest._.routes(순서 = SvelteKit 매칭 우선순위), nodeOf(i) = {imports, stylesheets}.
 * `skip` 에 든 파일(이미 HTML 이 preload 하는 레이아웃 청크)은 뺀다. 반환 {files:[href], table:[[src,[fileIdx],[api]]]}.
 * CSS 여부는 확장자(.css)로 가린다.
 */
export function buildRouteTable(routes, nodeOf, skip = new Set(), apiRoutes = BOOT_ROUTES) {
	const files = [];
	const index = new Map();
	const fileId = (href) => {
		if (!index.has(href)) {
			index.set(href, files.length);
			files.push(href);
		}
		return index.get(href);
	};
	const table = [];
	for (const r of routes) {
		if (!r.page) continue;
		const nodes = [...r.page.layouts, r.page.leaf].filter((n) => n !== undefined && n !== null);
		const ids = [];
		for (const n of nodes) {
			const { imports, stylesheets } = nodeOf(n);
			for (const f of [...imports, ...stylesheets]) if (!skip.has(f)) ids.push(fileId(f));
		}
		const api = (apiRoutes[r.id] ?? []).map((t) => templateToGroups(t, r.params ?? [])).filter(Boolean);
		table.push([r.pattern.source, [...new Set(ids)], api]);
	}
	return { files, table };
}

/**
 * 인라인 스크립트 본문. 오류는 삼킨다 — 실패해도 기존 경로(라우터가 청크·API 요청)로 그대로 동작한다.
 * 위치는 injectIntoHtml 설명(첫 stylesheet 링크 앞). 하는 일: 경로 매칭 → 그 라우트 노드 청크(+CSS) link 걸기 + API 선요청.
 */
export function renderInlineScript({ base, files, table, always = BOOT_ALWAYS }) {
	// 모든 파일이 같은 접두사(_app/immutable/)면 떼어 HTML 을 줄인다
	const prefix = files.length && files.every((f) => f.startsWith(IMMUTABLE)) ? IMMUTABLE : '';
	const F = files.map((f) => f.slice(prefix.length));
	const data = JSON.stringify({ P: `${base}/${prefix}`, F, R: table, S: always });
	return `(function(){try{var D=${data},B=${JSON.stringify(base)},d=document,h=d.head,p=location.pathname;` +
		`if(B&&p.indexOf(B)===0)p=p.slice(B.length)||"/";try{p=decodeURI(p)}catch(e){}` +
		`function L(f){var l=d.createElement("link");if(/\\.css$/.test(f)){l.rel="preload";l.as="style"}else l.rel="modulepreload";l.href=D.P+f;h.appendChild(l)}` +
		`var demo=false;try{demo=sessionStorage.getItem(${JSON.stringify(DEMO_FLAG)})==="1"}catch(e){}` +
		`var X=demo?null:(window.__rpBoot={});` +
		`function G(a){if(!X||X[a])return;var q=fetch(${JSON.stringify(API_BASE)}+a,{headers:{"Content-Type":"application/json"},redirect:"manual"});q.catch(function(){});X[a]={p:q,t:performance.now()}}` +
		`for(var i=0;i<D.S.length;i++)G(D.S[i]);` +
		`for(i=0;i<D.R.length;i++){var r=D.R[i],m=new RegExp(r[0]).exec(p);if(!m)continue;` +
		`for(var j=0;j<r[1].length;j++)L(D.F[r[1][j]]);` +
		`for(j=0;j<r[2].length;j++){var bad=0,a=r[2][j].replace(/\\{(\\d+)\\}/g,function(_,n){var v=m[+n]||"";if(!/^\\d+$/.test(v))bad=1;return v});if(!bad)G(a)}` +
		`break}}catch(e){}})();`;
}

/**
 * index.html 의 첫 `<link rel="stylesheet">` 바로 앞(= theme-init·진입/레이아웃 modulepreload 뒤, CSS 앞)에 넣는다. 멱등(있으면 교체).
 * 실측(cwv-measurement-2026-11.md S4-90): theme-init 앞(머리 맨 앞)에 두면 청크·API 가 렌더 차단 CSS 와 대역폭을 다퉈 FCP 가
 * 2.0→4.1s 로 늦었고, API 만 맨 앞에 둬도 요청이 많은 coach 는 FCP +0.8s. stylesheet 뒤에 두면 CSS 도착까지 실행이 밀린다.
 */
export function injectIntoHtml(html, script) {
	const tag = `<script ${MARKER}>${script}</script>`;
	const out = html.replace(new RegExp(`\\s*<script ${MARKER}[^>]*>[\\s\\S]*?</script>`, 'g'), '');
	const css = out.match(/<link href="[^"]+" rel="stylesheet">/);
	if (!css) throw new Error('route-preload: stylesheet 링크를 찾지 못함');
	return out.replace(css[0], () => `${tag}\n\t\t${css[0]}`);
}

/** HTML 이 이미 modulepreload/stylesheet 로 거는 `_app/...` 경로(base 제외). */
export function preloadedFiles(html, base) {
	const out = new Set();
	for (const m of html.matchAll(/<link href="([^"]+)" rel="(?:modulepreload|stylesheet)">/g)) {
		const href = m[1].startsWith(`${base}/`) ? m[1].slice(base.length + 1) : m[1];
		out.add(href);
	}
	return out;
}

async function main() {
	const root = fileURLToPath(new URL('..', import.meta.url));
	const serverDir = `${root}.svelte-kit/output/server`;
	const { manifest } = await import(pathToFileURL(`${serverDir}/manifest.js`).href);
	const base = `/${manifest.appPath.replace(/\/?_app$/, '')}`.replace(/\/$/, '');
	const indexPath = `${root}build/index.html`;
	const html = readFileSync(indexPath, 'utf8');
	const nodeOf = (i) => parseNodeFile(readFileSync(`${serverDir}/nodes/${i}.js`, 'utf8'));
	const { files, table } = buildRouteTable(manifest._.routes, nodeOf, preloadedFiles(html, base));
	const script = renderInlineScript({ base, files, table });
	writeFileSync(indexPath, injectIntoHtml(html, script));
	console.log(`route-preload: ${table.length} routes, ${files.length} files, ${script.length} bytes → build/index.html`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) await main();
