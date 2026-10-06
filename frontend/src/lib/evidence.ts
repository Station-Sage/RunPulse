// adaptEvidence — BriefingEvidence → EvidenceQuoteProps 변환 + 드릴 콜백 연결.
// 여러 컴포넌트(Today 페이지, 월간 라우트)에서 중복 정의되던 로직을 통합.
import type { BriefingEvidence, EvidenceQuoteProps } from '$lib/types';

export interface DrillTarget {
	slug: string;
	scopeType: string;
	scopeId: string;
}

export function adaptEvidence(
	ev: BriefingEvidence,
	onDrill?: (t: DrillTarget) => void
): EvidenceQuoteProps {
	const base: EvidenceQuoteProps = {
		type: 'metric',
		label: ev.label,
		metric: { slug: ev.metric, value: ev.value }
	};
	if (ev.drill && onDrill) {
		base.onOpen = () =>
			onDrill({ slug: ev.metric, scopeType: ev.drill!.scope_type, scopeId: ev.drill!.scope_id });
	}
	return base;
}
