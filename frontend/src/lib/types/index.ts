// 04-component-catalog.md 기준 공유 타입 — Phase 7a(Today) 몫만.
// MetricBreakdown/ProviderComparison/TimelineNarrative 관련 타입은 7b에서 추가한다.

export type ProviderKey =
	| 'garmin'
	| 'strava'
	| 'intervals'
	| 'runalyze'
	| 'runpulse'
	| `runpulse:${string}`;

export type PainLevel = 'none' | 'mild' | 'moderate' | 'severe';

export type SemanticStatus = 'excellent' | 'good' | 'neutral' | 'caution' | 'poor';

// ── C1: EvidenceQuote ──────────────────────────────────────────────────────

export interface EvidenceQuoteProps {
	type: 'metric' | 'activity' | 'wellness' | 'user_input';
	label?: string;
	metric?: {
		slug: string;
		value: number | string;
		unit?: string;
		date?: string;
		provider?: ProviderKey;
	};
	activity?: { id: number; field: string; value: number | string; unit?: string };
	user_input?: { field: string; value: number | string; date: string };
	unavailable?: boolean;
	// 클릭 시 원천 데이터 패널을 여는 콜백. 7a엔 MetricBreakdown 패널이 없어 보통 생략된다 —
	// 생략되면 칩은 비대화형(span)으로 렌더링된다.
	onOpen?: (payload: EvidenceQuoteProps) => void;
}

// ── C2: MetricCell ──────────────────────────────────────────────────────────

export interface MetricCellTrend {
	direction: 'up' | 'down' | 'flat';
	data: number[];
	change?: string;
}

export interface MetricCellProps {
	slug: string;
	label: string;
	value: number | string | null;
	unit?: string;
	provider: ProviderKey | null;
	status?: SemanticStatus;
	trend?: MetricCellTrend;
	size?: 'sm' | 'md' | 'lg';
	// 7a엔 MetricBreakdown 패널이 없어 항상 false로 렌더링한다(07-migration-roadmap.md 7a 체크리스트).
	drillable?: boolean;
	unavailable?: boolean;
	onDrill?: (payload: { slug: string; provider: ProviderKey | null }) => void;
}

// ── C5: QuickInput ────────────────────────────────────────────────────────

export interface QuickInputExisting {
	fatigue?: number;
	pain?: PainLevel;
	note?: string;
	timestamp?: string;
}

export interface QuickInputProps {
	existing?: QuickInputExisting;
	compact?: boolean;
	saving?: boolean;
	onSave?: (value: { fatigue?: number; pain?: PainLevel; note?: string }) => void;
}

// ── C6: RecommendationCard ───────────────────────────────────────────────

export interface RecommendationAction {
	label: string;
	href?: string;
	variant: 'primary' | 'ghost';
	onClick?: () => void;
}

export interface RecommendationCardProps {
	recommendation: {
		title?: string;
		body: string;
		evidence: EvidenceQuoteProps[];
	};
	actions?: RecommendationAction[];
	variant?: 'default' | 'warning' | 'positive';
	loading?: boolean;
}

// ── /api/v1/library 실제 응답 (src/api/routes_library.py, src/services/activity_service.py) ──

// v_canonical_activities의 행 — activity_service.get_activity_list() 기준.
export interface ActivitySummary {
	id: number;
	name: string;
	activity_type: string;
	start_time: string;
	distance_m: number | null;
	duration_sec: number | null;
	avg_hr: number | null;
	avg_pace_sec_km: number | null;
	elevation_gain: number | null;
	source: string;
}

export interface ActivitiesListResponse {
	activities: ActivitySummary[];
	total: number;
	has_more: boolean;
}

// activity_service._build_metrics_by_category()의 각 항목.
export interface ActivityMetric {
	metric_name: string;
	numeric_value: number | null;
	text_value: string | null;
	json_value: string | null;
	provider: string | null;
	confidence: number | null;
	unit: string;
	description: string;
}

// activity_summaries 행 (공통 필드 + 인덱스 시그니처).
export interface ActivityCore {
	id: number;
	name: string;
	activity_type: string;
	start_time: string;
	distance_m: number | null;
	duration_sec: number | null;
	avg_hr: number | null;
	avg_pace_sec_km: number | null;
	elevation_gain: number | null;
	source: string;
	[key: string]: unknown;
}

export interface ActivityDetail {
	core: ActivityCore;
	metrics_by_category: Record<string, ActivityMetric[]>;
	source_comparison: Record<string, unknown>;
	semantic_groups: Record<string, unknown>;
	streams: unknown[] | null;
	laps: unknown[] | null;
	best_efforts: unknown[] | null;
}

export interface ActivityDetailResponse {
	activity: ActivityDetail;
}

// ── /api/v1/today 실제 응답 (src/api/routes_today.py, src/services/today_service.py 기준) ──

export interface MetricEntry {
	value: number | null;
	level?: string;
	components?: Record<string, unknown>;
	confidence?: number;
}

export interface TodayReadiness {
	utrs: MetricEntry | null;
	cirs: MetricEntry | null;
	crs: MetricEntry | null;
}

export interface TodayTrainingStatus {
	ctl: number | null;
	atl: number | null;
	tsb: number | null;
	ramp_rate: number | null;
	acwr: number | null;
	training_phase?: string;
}

export interface TodayProviders {
	utrs?: ProviderKey;
	cirs?: ProviderKey;
	tsb?: ProviderKey;
}

export interface TodayStatus {
	date: string;
	readiness: TodayReadiness;
	training_status: TodayTrainingStatus;
	providers: TodayProviders;
}

export interface BriefingEvidence {
	type: 'metric';
	metric: string;
	value: number | string;
	label: string;
}

export interface TodayBriefing {
	date: string;
	headline: string;
	evidence: BriefingEvidence[];
}

export interface RecentActivity {
	id: number;
	name: string;
	activity_type: string;
	start_time: string;
	distance_m: number;
	duration_sec: number;
	source: string;
}

export interface CheckinPayload {
	fatigue?: number;
	pain?: PainLevel;
	note?: string;
}

export interface CheckinRow {
	id: number;
	input_date: string;
	input_type: string;
	fatigue: number | null;
	pain: PainLevel | null;
	note: string | null;
	activity_id: number | null;
	created_at: string;
}

export type CheckinResult = CheckinRow & { saved_at: string };

export interface TodayResponse {
	status: TodayStatus;
	briefing: TodayBriefing;
	recent_activities: RecentActivity[];
	checkin: CheckinRow | null;
}
