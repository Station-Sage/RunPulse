// A11Y 공통 1단계 — 토큰 대비 계산(순수). WCAG 2.x 상대휘도·대비비, layout.css 테마 블록 파서.
export type Theme = 'dark' | 'light';
export type Tokens = Record<string, string>;

export function parseHex(hex: string): [number, number, number] | null {
	const m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(hex.trim());
	if (!m) return null;
	let h = m[1];
	if (h.length === 3) h = [...h].map((c) => c + c).join('');
	return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)) as [number, number, number];
}

export function relativeLuminance(hex: string): number {
	const rgb = parseHex(hex);
	if (!rgb) throw new Error(`hex 색이 아님: ${hex}`);
	const [r, g, b] = rgb.map((v) => {
		const c = v / 255;
		return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
	});
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrastRatio(a: string, b: string): number {
	const la = relativeLuminance(a);
	const lb = relativeLuminance(b);
	return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

// 중괄호 균형으로 `selector { ... }` 의 본문을 모두 모은다.
function blockBodies(css: string, selector: RegExp): string[] {
	const out: string[] = [];
	const re = new RegExp(selector.source + '\\s*\\{', 'g');
	let m: RegExpExecArray | null;
	while ((m = re.exec(css))) {
		let depth = 1;
		let i = re.lastIndex;
		const start = i;
		while (i < css.length && depth > 0) {
			if (css[i] === '{') depth++;
			else if (css[i] === '}') depth--;
			i++;
		}
		out.push(css.slice(start, i - 1));
		re.lastIndex = i;
	}
	return out;
}

function declarations(body: string): Tokens {
	const t: Tokens = {};
	const re = /(--[\w-]+)\s*:\s*([^;]+);/g;
	let m: RegExpExecArray | null;
	while ((m = re.exec(body.replace(/\/\*[\s\S]*?\*\//g, '')))) t[m[1]] = m[2].trim();
	return t;
}

function resolveVars(t: Tokens): Tokens {
	const out: Tokens = {};
	for (const [k, v] of Object.entries(t)) {
		const m = /^var\((--[\w-]+)\)$/.exec(v);
		out[k] = m && t[m[1]] ? t[m[1]] : v;
	}
	return out;
}

export interface ThemeTokens {
	dark: Tokens;
	light: Tokens | null;
	lightMedia: Tokens | null;
}

// 다크는 @theme(기본), 라이트는 그 위에 [data-theme='light'] 선언을 덮은 값. 라이트 블록이 없으면 null.
export function parseThemeTokens(css: string): ThemeTokens {
	const dark = declarations(blockBodies(css, /@theme/).join('\n'));
	const explicit = blockBodies(css, /:root\[data-theme=['"]light['"]\]/);
	const media = blockBodies(css, /:root:not\(\[data-theme=['"]dark['"]\]\)/);
	const own = (bodies: string[]) => (bodies.length ? declarations(bodies.join('\n')) : null);
	const lightOwn = own(explicit);
	const mediaOwn = own(media);
	return {
		dark: resolveVars(dark),
		light: lightOwn ? resolveVars({ ...dark, ...lightOwn }) : null,
		lightMedia: mediaOwn ? resolveVars({ ...dark, ...mediaOwn }) : null
	};
}
