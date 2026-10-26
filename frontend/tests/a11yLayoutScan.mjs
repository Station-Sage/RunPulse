// A11Y-L 정적 가드 검사기(순수). 파일 내용 → 검사 기호별 위반 수. a11yLayout.test.mjs 가 baseline 과 비교한다.
export const CHECKS = {
	a: '역할 status/alert 와 aria-live 동시 사용',
	b: '{#if} 직하 role=status|alert',
	c: 'live 요소 안의 button/a/input',
	d: '라우트 order-N·-reverse',
	e: '+layout 순서(skip link < header < lg nav < main#main)',
	f: 'role=dialog 에 aria-labelledby 없음',
	g: 'role=group 안의 live',
	h: 'role=alert 사용',
	i: '<p uppercase> 단독 섹션 이름',
	j: 'role=slider 에 onkeydown 없음'
};

const tags = (s, re) => [...s.matchAll(re)].map((m) => m[0]);
const LIVE = /\brole="(?:status|alert)"|\baria-live=/;

export function scan(path, s) {
	const out = {};
	const add = (k, n = 1) => n > 0 && (out[k] = (out[k] ?? 0) + n);
	const openTags = tags(s, /<[a-zA-Z][\w.:-]*\b(?:[^<>{}]|\{(?:[^{}]|\{[^{}]*\})*\})*>/g);
	add('a', openTags.filter((t) => /\brole="(?:status|alert)"/.test(t) && /\baria-live=/.test(t)).length);
	add('b', [...s.matchAll(/\{#if[^}]*\}\s*<[a-zA-Z][\w-]*\b(?:[^<>{}]|\{(?:[^{}]|\{[^{}]*\})*\})*?\brole="(?:status|alert)"/g)].length);
	add('c', [...s.matchAll(/<(\w+)\b(?:[^<>{}]|\{(?:[^{}]|\{[^{}]*\})*\})*?(?:role="(?:status|alert)"|aria-live=)(?:[^<>{}]|\{(?:[^{}]|\{[^{}]*\})*\})*>([\s\S]*?)<\/\1>/g)]
		.filter((m) => /<(?:button|a|input)\b/.test(m[2])).length);
	if (path.startsWith('src/routes/')) add('d', openTags.filter((t) => /\border-\d|-reverse\b/.test(t.replace(/class:[^=]*=/g, ''))).length);
	add('f', openTags.filter((t) => /\brole="dialog"/.test(t) && !/aria-labelledby=/.test(t)).length);
	add('g', [...s.matchAll(/<(\w+)\b(?:[^<>{}]|\{(?:[^{}]|\{[^{}]*\})*\})*?role="group"(?:[^<>{}]|\{(?:[^{}]|\{[^{}]*\})*\})*>([\s\S]*?)<\/\1>/g)]
		.filter((m) => LIVE.test(m[2])).length);
	add('h', openTags.filter((t) => /\brole="alert"/.test(t)).length);
	add('i', [...s.matchAll(/<p\b[^>]*\buppercase\b[^>]*>/g)].length);
	add('j', openTags.filter((t) => /\brole="slider"/.test(t) && !/onkeydown=/.test(t)).length);
	if (path === 'src/routes/+layout.svelte') {
		const at = (re) => s.search(re);
		const order = [at(/href="#main"/), at(/<header\b/), at(/ShellNav[^>]*variant="side"/), at(/<main\b[^>]*id="main"/)];
		add('e', order.some((n) => n < 0) || order.some((n, i) => i && n < order[i - 1]) ? 1 : 0);
	}
	return out;
}
