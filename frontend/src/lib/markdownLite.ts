/**
 * Minimal markdown parser for Coach chat responses.
 * XSS-safe: produces structured tokens, no HTML output.
 * Supported syntax: bold (**text**), headings (#/##/###), bullet lists (- or *).
 */

export type Span = { type: 'text'; text: string } | { type: 'bold'; text: string };

export type Token =
	| { type: 'heading'; level: 1 | 2 | 3; spans: Span[] }
	| { type: 'list_item'; spans: Span[] }
	| { type: 'paragraph'; spans: Span[] }
	| { type: 'blank' };

/** Parse inline bold markers (**text** or *text*) into Span[]. */
function parseInline(text: string): Span[] {
	const spans: Span[] = [];
	const re = /\*\*(.+?)\*\*|\*(.+?)\*/g;
	let last = 0;
	let m: RegExpExecArray | null;
	while ((m = re.exec(text)) !== null) {
		if (m.index > last) {
			spans.push({ type: 'text', text: text.slice(last, m.index) });
		}
		spans.push({ type: 'bold', text: m[1] ?? m[2] });
		last = m.index + m[0].length;
	}
	if (last < text.length) {
		spans.push({ type: 'text', text: text.slice(last) });
	}
	return spans.length > 0 ? spans : [{ type: 'text', text }];
}

/** Parse markdown text into structured tokens for rendering. */
export function parseMarkdown(text: string): Token[] {
	const tokens: Token[] = [];
	for (const line of text.split('\n')) {
		const trimmed = line.trim();
		if (!trimmed) {
			tokens.push({ type: 'blank' });
			continue;
		}
		const headingMatch = trimmed.match(/^(#{1,3})\s+(.*)/);
		if (headingMatch) {
			tokens.push({
				type: 'heading',
				level: headingMatch[1].length as 1 | 2 | 3,
				spans: parseInline(headingMatch[2])
			});
			continue;
		}
		const listMatch = trimmed.match(/^[-*]\s+(.*)/);
		if (listMatch) {
			tokens.push({ type: 'list_item', spans: parseInline(listMatch[1]) });
			continue;
		}
		tokens.push({ type: 'paragraph', spans: parseInline(trimmed) });
	}
	return tokens;
}

/** Strip markdown symbols for plain-text preview (e.g. thread list). */
export function stripMarkdown(text: string): string {
	return text
		.replace(/#{1,3}\s+/g, '')
		.replace(/\*\*(.+?)\*\*/g, '$1')
		.replace(/\*(.+?)\*/g, '$1')
		.replace(/^[-*]\s+/gm, '')
		.replace(/\n+/g, ' ')
		.trim();
}

/** Translate internal ai_model codes to user-facing labels. */
export function localizeSource(aiModel: string | null): string | null {
	if (!aiModel) return null;
	if (aiModel === 'rule') return '규칙 기반 답변';
	return aiModel;
}
