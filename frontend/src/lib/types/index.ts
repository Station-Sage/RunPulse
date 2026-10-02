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
	/** 답변 결론과 반대 방향인 근거(점선 테두리 + "반대 신호" 라벨). */
	caveat?: boolean;
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
	note?: string;
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
	/** 지정하면 `✕ 나중에`가 나타나고, 해당 날짜에는 입력 카드를 다시 올리지 않는다(B2). */
	dismissDate?: string;
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
	/** 목록 썸네일용 GPS 미리보기(≤32점 [lat,lng]) — GPS 없으면 null/없음 */
	route?: [number, number][] | null;
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
	status?: SemanticStatus;
	status_label?: string;
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

// activity_laps 행 — activity_service.get_activity_detail()의 laps (lap_index 순).
export interface ActivityLap {
	id: number;
	activity_id: number;
	source: string;
	lap_index: number;
	start_time: string | null;
	duration_sec: number | null;
	distance_m: number | null;
	avg_hr: number | null;
	max_hr: number | null;
	avg_pace_sec_km: number | null;
	avg_cadence: number | null;
	avg_power: number | null;
	max_power: number | null;
	elevation_gain: number | null;
	calories: number | null;
	lap_trigger: string | null;
}

export interface ActivityImpact {
	/** 이 활동의 TRIMP */
	load: number | null;
	/** 활동일 CTL의 전일 대비 변화 */
	ctl_contribution: number | null;
	tsb: number | null;
	tsb_as_of: string | null;
	similar: { basis: string; n: number; pace_rank: number; avg_pace_sec_km: number; pace_diff_sec: number } | null;
	race: { name: string; days_left: number } | null;
}

// ── 활동 상세 3-6: 서버 계산 스플릿·시계열·환경·존·소스 차이·판정 ──

export interface ActivitySplit {
	idx: number;
	dist_m: number;
	moving_sec: number;
	elapsed_sec: number;
	stop_sec: number;
	pace_sec_km: number | null;
	avg_hr: number | null;
	elev_gain_m: number | null;
	partial: boolean;
}

/** 거리 기준 등간격(step_m) 재표본 — 모든 배열 길이 동일(≤600). 타임라인·지도 공유. */
export interface ActivitySeries {
	step_m: number;
	dist_m: number[];
	pace_sec_km: (number | null)[];
	hr: (number | null)[];
	alt_m: (number | null)[];
	lat: (number | null)[];
	lon: (number | null)[];
}

export interface ActivityEnvironment {
	temp_c: number | null;
	dew_point_c: number | null;
	fearp_sec_km: number | null;
	pace_effect_sec_km: number | null;
}

export interface ActivityHrZones {
	provider: string;
	basis: 'intervals_zones' | 'device_zones';
	sec: number[];
}

export interface SourceDiff {
	row: string;
	quantity: string;
	unit: string;
	values: Record<string, number>;
	abs: number;
	pct: number | null;
	significant: boolean;
	threshold: { kind: string; value: number };
	reason: string | null;
}

export interface VerdictEvidence {
	kind: 'info' | 'drill';
	label: string;
	target?: string;
}

export interface ActivityVerdict {
	text: string;
	evidence: VerdictEvidence[];
}

export interface ActivityWorkoutClassBasis {
	hr_pct_max: number | null;
	pace_cv: number | null;
}

export interface ActivityDetail {
	core: ActivityCore;
	metrics_by_category: Record<string, ActivityMetric[]>;
	source_comparison: Record<string, unknown>;
	semantic_groups: Record<string, unknown>;
	/** 기본 응답에서는 null — `?include=streams`일 때만 최대 500포인트 다운샘플. 전체 해상도는 streams 탭의 getActivityStreams. */
	streams: ActivityStreamPoint[] | null;
	/** streams 다운샘플 전 원본 포인트 수 — 화면에 실제 기록 밀도를 보여줄 때 사용. */
	stream_point_count: number;
	laps: ActivityLap[] | null;
	best_efforts: unknown[] | null;
	impact?: ActivityImpact | null;
	splits?: ActivitySplit[];
	series?: ActivitySeries | null;
	siblings?: { id: number; provider: string; is_canonical: boolean }[];
	workout_class?: string | null;
	workout_class_label?: string | null;
	workout_class_basis?: ActivityWorkoutClassBasis | null;
	environment?: ActivityEnvironment | null;
	hr_zones?: ActivityHrZones | null;
	source_diffs?: SourceDiff[];
	verdict?: ActivityVerdict | null;
}

export interface ActivityDetailResponse {
	activity: ActivityDetail;
}

// ── /api/v1/coach 실제 응답 (src/api/routes_coach.py, src/services/coach_service.py 기준) ──

export interface ChatThread {
	id: number;
	title: string;
	created_at: string;
	updated_at: string;
	last_message: string | null;
	last_message_at: string | null;
}

export interface ChatMessage {
	id: number;
	role: 'user' | 'assistant';
	content: string;
	ai_model: string | null;
	created_at?: string;
	evidence?: AnswerEvidence[];
	/** 스냅샷 없는 옛 답변 — 근거가 "당시 Today 근거"(design §7.4). */
	evidence_legacy?: boolean;
	status?: string;
	/** assistant 메시지만 — 답변을 만든 엔진(30-coach-chat design §4.1). */
	engine?: EngineView;
	as_of?: string | null;
	sent_scope?: ScopeItem[] | null;
	/** assistant 메시지만 — 서버가 고른 다음 질문 칩(최대 3, 이미 물은 칩 제외). */
	followups?: CoachChip[];
	/** pending/working 메시지만 — SSE 엔드포인트(S4 상태 기계). */
	stream_url?: string;
	client_msg_id?: string | null;
	parent_message_id?: number | null;
}

/** 서버가 답할 수 있는 질문 칩 — 탭하면 chip_id 로 전송한다(30-coach-chat design §7.3). */
export interface CoachChip {
	chip_id: string;
	text: string;
}

export interface SuggestionsResponse {
	suggestions: CoachChip[];
}

export type EngineStatus =
	| 'ok' | 'fallback' | 'rule_only' | 'rule_by_choice' | 'error' | 'cancelled' | 'legacy_rule';

export interface EngineView {
	status: EngineStatus;
	label: string;
	provider: string | null;
	model: string | null;
	reason: string | null;
}

export interface ScopeItem {
	item: string;
	period: string;
	optional: boolean;
}

export interface CoachConsent {
	provider: string;
	accepted_at: string | null;
	exclude_notes: boolean;
	tools_enabled: boolean;
	fallback_enabled: boolean;
}

export interface EngineHealth {
	consecutive_failures: number;
	last_ok_at: string | null;
	last_error: { provider: string | null; model: string | null; status: number | null; reason: string | null; at: string } | null;
	degraded: boolean;
}

export interface CoachEngine {
	mode: 'llm' | 'rule_only' | 'rule_by_choice';
	selected: { provider: string; model: string | null };
	chain: { provider: string; model: string }[];
	health: EngineHealth;
	consent: CoachConsent | null;
	scope: ScopeItem[];
}

export interface RegenerateResponse {
	message: ChatMessage;
}

export interface ThreadsListResponse {
	threads: ChatThread[];
}

export interface ThreadDetail {
	id: number;
	title: string;
	created_at: string;
	updated_at: string;
	context?: CoachThreadContext | null;
}

export interface ThreadDetailResponse {
	thread: ThreadDetail;
	messages: ChatMessage[];
}

/** 전송 계열 응답 — 사용자 메시지와 pending 답변을 즉시 돌려준다(design §6.2). */
export interface SentMessages {
	user_message: ChatMessage;
	assistant_message: ChatMessage;
}

/** `/coach/activity-context` — 활동 근거 카드 + 훈련 유형별 추천 질문 3개. */
export interface CoachActivityContext {
	id: number;
	name: string | null;
	date: string | null;
	workout_class: string | null;
	workout_class_label: string | null;
	distance_km: number | null;
	pace: string | null;
	decoupling_pct: number | null;
	tsb: number | null;
	suggestions: string[];
}

export interface CoachThreadContext {
	kind: string;
	ref: string;
}

export interface CreateThreadResponse extends SentMessages {
	thread: { id: number; title: string };
}

export type AddMessageResponse = SentMessages;

// ── /api/v1/today 실제 응답 (src/api/routes_today.py, src/services/today_service.py 기준) ──

// 서버 등급(src/metrics/bands.py) — 프론트는 경계값 없이 렌더만 한다.
export interface Grade {
	status: SemanticStatus;
	label: string;
}

export interface MetricEntry {
	value: number | null;
	level?: string;
	status?: SemanticStatus | null;
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
	grades?: { tsb?: Grade | null; acwr?: Grade | null };
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

export interface EvidenceDrill {
	scope_type: string;
	scope_id: string;
}

/** Coach 답변 근거 v2 — 저장 시점 스냅샷과 조회 시점 현재값(design §4.4). */
export interface AnswerEvidence {
	type: 'metric' | 'wellness' | 'plan' | 'user_input';
	metric: string;
	value: number | string | null;
	label: string;
	status?: string;
	status_label?: string;
	pinned?: boolean;
	role: 'supports' | 'caveat' | 'legacy';
	drill?: EvidenceDrill | null;
	snapshot?: { value: number | string | null; computed_at: string | null; version: string | null; as_of: string | null };
	current?: { value: number | string; display: string; computed_at: string | null; version: string | null } | null;
	drifted?: boolean;
}

export interface BriefingEvidence {
	type: 'metric';
	metric: string;
	value: number | string;
	label: string;
	drill?: EvidenceDrill | null;
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
	route?: [number, number][] | null;
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

// ── MetricBreakdown (C3 축소판 — 실제 API 응답 기준) ────────────────────────

export interface MetricBreakdownNode {
	name: string;
	label: string;
	value: number | string | null;
	unit: string;
	provider: ProviderKey | null;
	confidence: number | null;
}

export interface MetricBreakdownData {
	slug: string;
	label: string;
	value: number | string | null;
	unit: string;
	provider: ProviderKey | null;
	confidence: number | null;
	children: MetricBreakdownNode[];
	inputs: MetricBreakdownNode[];
}

// ── 분해 v2 (§C3.2, explain=1) — TSB/CTL/ATL/UTRS/CIRS/RRI만 지원 ──────────
// term 형태는 메트릭 종류마다 다르다: TSB/CTL/ATL은 sign+contribution(합),
// UTRS/CIRS는 weight+contribution+loss(가중 평균), RRI는 ratio+role="factor"(곱).

export interface MetricExplainBand {
	max: number | null; // null = 마지막 구간(상한 없음)
	status: SemanticStatus;
	label: string;
}

export interface MetricExplainTerm {
	slug: string;
	label: string;
	raw: number | string | null;
	normalized?: number | null;
	weight?: number | null;
	contribution?: number | null;
	loss?: number | null;
	sign?: '+' | '-';
	ratio?: number | null;
	role?: 'factor';
	target?: number | null;
	drill?: string; // 있으면 행 탭으로 스택 push 가능(§C3.3 토큰, 예: "m.ctl")
}

export interface MetricExplainSource {
	type: 'activity' | 'wellness_day' | 'metric';
	id?: number;
	date?: string;
	slug?: string;
	label: string;
	value: number | string | null;
	unit: string;
	effect: string;
}

export interface MetricExplainData {
	slug: string;
	name_ko: string;
	abbr: string;
	scope: { type: string; id: string; basis: string };
	value: number | null;
	display: number | null;
	unit: string;
	status: SemanticStatus | null;
	status_label: string | null;
	higher_is_better: boolean | null;
	meaning: {
		what: string;
		bands: MetricExplainBand[];
		baseline: { avg_7d: number | null; delta_1d: number | null };
		so_what: string;
	};
	formula: {
		text: string;
		version: string;
		computed_at: string;
		terms: MetricExplainTerm[];
	};
	sources: MetricExplainSource[];
	provider: { kind: string; version: string; computed_at: string };
	compare: unknown[];
	links: { trend: string };
}

// ── /api/v1/today/narrative 실제 응답 ─────────────────────────────────────

export interface MilestoneEntry {
	id: number;
	type: 'distance_threshold' | 'pb' | 'metric_recompute';
	date: string;
	title: string;
	detail: string | null;
	activity_id: number | null;
}

export interface NarrativeHighlights {
	total_distance_km: number;
	activity_count: number;
	longest_run_km: number;
	peak_ctl: number | null;
}

export interface NarrativeResponse {
	date: string;
	text: string;
	source: 'ai' | 'rule';
	evidence: BriefingEvidence[];
	milestones: MilestoneEntry[];
	highlights: NarrativeHighlights;
}

// ── Today v2 확장 (src/services/today_hero.py · today_readiness.py) ──

export type BriefingState = 'pre' | 'done' | 'extra' | 'rest' | 'no_plan' | 'race_week' | 'race_day';

export interface BriefingSession {
	id: number | null;
	date: string | null;
	workout_type: string | null;
	title: string | null;
	distance_m: number | null;
	pace_min: number | null;
	pace_max: number | null;
	zone: string | number | null;
}

export interface BriefingCaveat {
	code: string;
	provider?: string;
	days?: number;
}

export interface BriefingStateFields {
	state: BriefingState;
	target_date: string;
	verdict: 'as_planned' | 'down' | 'up';
	today_result: { activity_id: number; distance_m: number; outcome_label: string | null; plan_ratio_pct: number | null } | null;
	session: BriefingSession | null;
	adjustment: { reason: string | null; from: string; to: string } | null;
	caveats: BriefingCaveat[];
}

export interface GaugeEntry {
	value: number;
	delta_1d: number | null;
	status: SemanticStatus | null;
	status_label: string | null;
	provider: ProviderKey | null;
	version: string;
}

export interface TodayReadinessV2 {
	utrs: GaugeEntry | null;
	cirs: GaugeEntry | null;
	tsb: GaugeEntry | null;
}

export type WeekDayState = 'pre_plan' | 'rest' | 'done' | 'partial' | 'missed' | 'upcoming';

export interface WeekDay {
	date: string;
	state: WeekDayState;
	workout_type: string | null;
	title: string | null;
	planned_km: number | null;
	session_id: number | null;
	activity_id: number | null;
	substituted: boolean;
	today: boolean;
}

export interface WeekCompliance {
	done_km: number;
	plan_km: number;
	key_done: number;
	key_total: number;
	days: WeekDay[];
}

export interface TodayResponse {
	status: TodayStatus;
	briefing: TodayBriefing & Partial<BriefingStateFields>;
	recent_activities: RecentActivity[];
	checkin: CheckinRow | null;
	data_health?: DataHealth;
	as_of?: { basis: 'morning'; date: string; computed_at: string };
	readiness?: TodayReadinessV2;
	week_compliance?: WeekCompliance;
	race_summary?: RaceSummary | null;
}

/** B4 한 줄용 레이스 요약(src/services/today_hero.py build_race_summary). 목표 없으면 null. */
export interface RaceSummary {
	days_left: number;
	name: string | null;
	distance_km: number | null;
	pred_sec: number | null;
	low_sec: number | null;
	high_sec: number | null;
	range_kind: 'model_envelope' | 'calibrated80' | null;
	confidence: number | null;
	target_sec: number | null;
}

export interface DataHealth {
	window_days: number;
	runs: number;
	missing: number;
	missing_ratio: number;
}

// ── ActivityStreams (3-D — /api/v1/library/activities/:id/streams) ────────────

export interface ActivityStreamPoint {
	elapsed_sec: number;
	distance_m: number | null;
	heart_rate: number | null;
	cadence: number | null;
	power_watts: number | null;
	altitude_m: number | null;
	speed_ms: number | null;
	grade_pct: number | null;
	source: string;
	latitude?: number | null;
	longitude?: number | null;
}

// ── ProviderComparison (C4 — /api/v1/library/activities/:id/providers) ───────

export interface ComparisonCell {
	value: number | string | null;
	available: boolean;
}

export interface ComparisonDiscrepancy {
	detected: boolean;
	maxDiff: number;
	maxDiffPct: number;
	severity: 'info' | 'warning';
}

export interface ComparisonPrimaryReason {
	provider: ProviderKey;
	ruleType: 'static_priority' | 'runpulse_always';
	rule: string;
}

export interface ComparisonRow {
	slug: string;
	label: string;
	unit: string | null;
	values: Record<string, ComparisonCell>;
	discrepancy: ComparisonDiscrepancy | null;
	preferredProvider: ProviderKey | null;
	primaryReason: ComparisonPrimaryReason | null;
}

export interface ProviderComparisonData {
	mode: 'activity' | 'period';
	activity_id?: number;
	days?: number;
	state: 'loaded' | 'single_provider' | 'no_data';
	rows: ComparisonRow[];
}

// ── MetricBrowser (3-E — /api/v1/library/metrics) ──────────────────────────

export interface MetricBrowserEntry {
	name: string;
	label: string;
	value: number | string | null;
	unit: string;
	provider: string | null;
	confidence: number | null;
	sparkline: number[];
	status?: SemanticStatus;
	status_label?: string;
}

export interface MetricBrowserCategory {
	category: string;
	label: string;
	metrics: MetricBrowserEntry[];
}

export interface MetricBrowserData {
	date: string;
	categories: MetricBrowserCategory[];
}

// ── MetricTrend (3-F — /api/v1/library/metrics/:slug/trend) ─────────────────

export interface MetricTrendPoint {
	date: string;
	value: number;
}

export interface MetricTrendData {
	slug: string;
	label: string;
	unit: string;
	current: number | null;
	peak: { value: number; date: string } | null;
	change_pct: number | null;
	points: MetricTrendPoint[];
}

// ── Wellness (3-G — /api/v1/library/wellness) ────────────────────────────────

export interface WellnessCore {
	date?: string;
	sleep_score?: number | null;
	sleep_duration_sec?: number | null;
	hrv_last_night?: number | null;
	hrv_weekly_avg?: number | null;
	resting_hr?: number | null;
	body_battery_high?: number | null;
	body_battery_low?: number | null;
	avg_stress?: number | null;
	steps?: number | null;
	weight_kg?: number | null;
	[key: string]: unknown;
}

export interface WellnessMetricEntry {
	metric_name: string;
	numeric_value: number | null;
	text_value: string | null;
	json_value: string | null;
	provider: string | null;
	confidence: number | null;
	unit: string;
	description: string;
}

export interface WellnessDetailData {
	date: string;
	core: WellnessCore;
	metrics_by_category: Record<string, WellnessMetricEntry[]>;
	readiness_summary: {
		utrs: { value: number | null; confidence: number | null } | null;
		cirs: { value: number | null; confidence: number | null } | null;
	};
}

export interface WellnessTrendData {
	dates: string[];
	sleep_score: (number | null)[];
	hrv_last_night: (number | null)[];
	resting_hr: (number | null)[];
	body_battery_high: (number | null)[];
	avg_stress: (number | null)[];
	weight_kg: (number | null)[];
	utrs: (number | null)[];
}

// ── Coach Plan (5-F — /api/v1/coach/plan/:id) ────────────────────────────────

export interface PlannedWorkout {
	id: number;
	date: string;
	workout_type: string;
	distance_km: number | null;
	target_pace_min: number | null;
	target_pace_max: number | null;
	target_hr_zone: string | null;
	description: string | null;
	rationale: string | null;
	completed: number; // 0 or 1
	source: string | null;
	ai_model: string | null;
	interval_prescription: string | null;
	matched_activity_id?: number | null;
	outcome_label?: string | null;
	dist_ratio?: number | null;
	actual_dist_km?: number | null;
	compliance_pct?: number | null; // 세트·구간 페이스까지 본 이행률(0~100)
	superseded?: boolean; // 같은 날 다른 계획(Garmin 저장 워크아웃 등)이 실제 활동을 가져감
}

export interface PlanGoal {
	id: number;
	name: string;
	race_date: string | null;
	distance_km: number;
	target_time_sec: number | null;
	plan_weeks: number | null;
	status: string;
}

// 이행 수치(src/training/week_compliance.py) — 한 숫자로 합치지 않는다
export interface PlanCompliance {
	sessions: { done: number; total: number };
	volume: { actual_km: number; planned_km: number; pct: number | null; days_without_target: number };
	quality: { done: number; total: number };
}

export type PlanDayState = 'done' | 'partial' | 'missed' | 'upcoming' | 'rest' | 'pre_plan';

export interface PlanDay {
	date: string;
	state: PlanDayState;
	effective?: { id: number; source: string; workout_type: string; distance_km: number | null };
	planned_km?: number | null;
	alternatives?: number[];
	substituted?: boolean;
	label?: string;
	status?: SemanticStatus;
	status_label?: string;
	today?: boolean;
}

export interface PlanWeek {
	days: PlanDay[];
	unplanned_runs: { date: string; activity_id: number; distance_km: number }[];
	compliance: PlanCompliance;
}

export interface ActivePlan {
	goal: PlanGoal;
	week_index: number;
	workouts: PlannedWorkout[];
	next_session?: PlannedWorkout | null; // 오늘 이후 첫 미완료 세션(다음 주 포함)
	ctl_current: number | null;
	compliance_pct: number | null;
	compliance?: PlanCompliance | null;
	week?: PlanWeek;
}

// ── Coach Plan Templates (5-D/5-E — /api/v1/coach/plan/templates) ────────────

export interface PlanTemplate {
	weeks: number;
	label: string;
	weekly_km_target: number | null;
	achievability_pct: number | null;
	projected_time_end: number | null;
	risk_level: '낮음' | '중간' | '높음' | null;
	status_summary: string;
}

export interface CreatePlanPayload {
	distance_km: number;
	race_date: string | null;
	weeks: number;
	target_time_sec?: number;
	name?: string;
}

export interface TodaysAdjustment {
	id: number;
	date: string;
	workout_type: string;
	distance_km: number | null;
	target_pace_min: number | null;
	target_pace_max: number | null;
	description: string | null;
	original_type: string;
	adjusted_type: string;
	adjusted: boolean;
	adjustment_reason: string | null;
	fatigue_level: string;
	volume_boost: boolean;
}

// ── Coach Plan Session Detail (5-G — /api/v1/coach/plan/:id/session/:date) ───

export interface SessionAdjustment {
	id: number;
	date: string;
	workout_type: string;
	distance_km: number | null;
	target_pace_min: number | null;
	target_pace_max: number | null;
	description: string | null;
	original_type: string;
	adjusted_type: string;
	adjusted: boolean;
	adjustment_reason: string | null;
	adjustment_reason_parts: string[];
	fatigue_level: string;
	volume_boost: boolean;
}

export interface SessionDetail {
	goal: PlanGoal;
	week_index: number;
	workout: PlannedWorkout;
	adjustment: SessionAdjustment | null;
	note: string | null;
}

// ── PlanAdaptation (5-F — /api/v1/coach/plan/adaptation) ─────────────────────
export interface PlanAdaptation {
	date: string;
	acwr: { value: number; zone: string; date: string } | null;
	hrv: { value: number; baseline: number | null; delta_pct: number | null; zone: string | null } | null;
	fatigue_avg: { value: number; n: number } | null;
}

// ── RaceHub (P7-IMPL-RACE-HUB-UI — /api/v1/today/race-hub) ──────────────────

export interface RaceHubGoal {
	id: number;
	name: string;
	race_date: string;
	distance_km: number;
	target_time_sec: number | null;
	target_pace_sec_km: number | null;
	days_left: number;
	weeks_left: number;
}

export interface RaceHubPredictionPoint {
	date: string;
	value: number;
}

export interface RaceHubPrediction {
	bucket: string;
	value_sec: number;
	as_of: string;
	gap_sec: number | null;
	history: RaceHubPredictionPoint[];
	compare?: PredictionCompare | null;
}

/** P7-PRED-71 레이스 예측 3경로 비교 — (a) garmin, (b) ref(기기 심박 기준), (c) self(자체 추정)
 * + 값이 있으면 r4 섀도 후보(candidate=true, P7-PRED-72 r4 추가). */
export interface PredictionCompareRow {
	key: 'garmin' | 'ref' | 'self' | 'r4' | 'r4_asym';
	label: string;
	provider: string;
	value_sec: number | null;
	as_of?: string;
	stale_days?: number;
	low_sec?: number | null;
	high_sec?: number | null;
	confidence?: number | null;
	reasons?: string[];
	contributions?: Record<string, number> | null;
	candidate?: boolean;
}

export interface PredictionCompare {
	bucket: string;
	as_of: string;
	rows: PredictionCompareRow[];
	hr_basis: { self_lthr: number | null; ref_lthr: number | null; lthr_gap: number | null };
	notes: string[];
}

export type ZoneBounds = [number, number][];

/** P7-PRED-74 예측 근거 — hr_profile·heat_model·training_response 최신 json(없으면 null). */
export interface PredictionProfile {
	as_of: string;
	hr_profile: {
		date: string;
		self: { hrmax: number | null; lthr: number; lthr_source: 'races' | 'hrmax_ratio'; rhr: number | null };
		ref: { source: string; lthr: number | null; hrmax: number | null } | null;
		zones: { self: { hrr: ZoneBounds | null; lthr: ZoneBounds }; ref?: { hrr: ZoneBounds | null; lthr: ZoneBounds | null } };
		lthr_gap: number | null;
	} | null;
	heat_model: { date: string; heat: number; cold: number; n: number; weight: number } | null;
	training_response: {
		date: string;
		weekly_zone_min: { R: number[]; I: number[]; T: number[]; M: number[]; sessions: number[] };
		quality_min_avg_8w: number;
		quality_min_avg_prev_8w: number | null;
		quality_sessions_avg_8w: number;
		long_mp_km_8w?: number;
		trend: { n: number; slope_4w: number | null };
	} | null;
}

export type RaceEffort = 'allout' | 'paced' | 'fun' | 'dnf';

export interface RaceCandidate {
	activity_id: number;
	date: string;
	name: string | null;
	distance_m: number;
	time_sec: number | null;
	confirmed_effort: RaceEffort | null;
}

export interface RaceHubForm {
	ctl: number | null;
	tsb: number | null;
}

export interface RaceProjectionScenario {
	key: 'taper' | 'keep';
	label: string;
	ctl: number;
	atl: number;
	tsb: number;
	series: { date: string; value: number }[];
	status?: SemanticStatus;
	status_label?: string;
}

export interface RaceProjection {
	as_of: string;
	race_date: string;
	days_left: number;
	base_daily_load: number;
	current: { ctl: number; atl: number; tsb: number };
	assumptions: string;
	scenarios: RaceProjectionScenario[];
}

export interface RaceHubData {
	goal: RaceHubGoal | null;
	prediction: RaceHubPrediction | null;
	form: RaceHubForm | null;
	projection: RaceProjection | null;
}

// ── ProviderStatus (3-A — /api/v1/library/providers/status) ──────────────────
// DECISIONS.md [P7-IMPL-PROVIDER-STATUS]: 자격증명 확인 없음, 저장 데이터 유무만 표기.

export interface ProviderStatusItem {
	provider: ProviderKey;
	has_data: boolean;
	last_synced_at: string | null;
	activity_count: number;
}

export interface ProviderStatusResponse {
	providers: ProviderStatusItem[];
}

// ── ProviderCoverage (N2 — /api/v1/library/providers/coverage) ───────────────
export interface ProviderCoverageItem { provider: ProviderKey; counts: number[]; total: number; sync_enabled?: boolean }
export interface ProviderCoverage { months: string[]; providers: ProviderCoverageItem[] }

// ── Archive (Library 홈 — /api/v1/library/archive) ───────────────────────────
export interface ArchiveTotals {
	runs: number;
	distance_km: number;
	hours: number;
	since: string;
	active_days_365: number;
}
export interface ArchivePb {
	key: string;
	label: string;
	time_sec: number;
	date: string;
	activity_id: number;
	source?: string; // '대회' | '구간 기록'(활동 안 최고 구간)
}
export interface ArchiveData {
	as_of: string;
	totals: ArchiveTotals | null;
	longest: { id: number; name: string; date: string; distance_km: number } | null;
	monthly: { month: string; km: number; runs: number }[];
	heatmap: { date: string; km: number }[];
	personal_bests: ArchivePb[];
}
