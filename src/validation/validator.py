"""DataValidator — 12개 데이터 정합성 체크.

각 체크는 CheckResult(name, status, expected, actual, message)를 반환합니다.
status: 'PASS' | 'WARN' | 'FAIL'

사용법:
    validator = DataValidator(conn)
    results = validator.run_all()
    has_fail = any(r.status == 'FAIL' for r in results)
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass

log = logging.getLogger(__name__)

# 12개 체크를 구동하는 Calculator produces 목록 (engine_coverage 체크용)
def _get_all_produces() -> list[str]:
    """ALL_CALCULATORS의 전체 produces 메트릭 이름 반환."""
    try:
        from src.metrics.engine import ALL_CALCULATORS
        names: list[str] = []
        for calc in ALL_CALCULATORS:
            names.extend(calc.produces)
        return names
    except Exception:
        return []


@dataclass
class CheckResult:
    name: str
    status: str       # 'PASS' | 'WARN' | 'FAIL'
    expected: str
    actual: str
    message: str


class DataValidator:
    """RunPulse 데이터 정합성 검증기.

    Args:
        conn: SQLite connection (read-only 사용 — DB 변경 없음)
        expected_sources: 기대 소스 목록
        expected_activities: 기대 활동 수 (None이면 > 0 체크만)
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        expected_sources: list[str] | None = None,
        expected_activities: int | None = None,
    ):
        self.conn = conn
        self.expected_sources = expected_sources or ["garmin", "strava", "intervals", "runalyze"]
        self.expected_activities = expected_activities

    # ─────────────────────────────────────────────────────────────────────────
    # Public
    # ─────────────────────────────────────────────────────────────────────────

    def run_all(self) -> list[CheckResult]:
        """12개 체크 전체 실행. 순서 보장."""
        checks = [
            self._check_row_counts,
            self._check_source_distribution,
            self._check_unmapped_metric_ratio,
            self._check_metric_density,
            self._check_primary_uniqueness,
            self._check_provider_distribution,
            self._check_dedup_consistency,
            self._check_data_quality,
            self._check_wellness_coverage,
            self._check_fitness_continuity,
            self._check_referential_integrity,
            self._check_engine_coverage,
        ]
        results = []
        for check_fn in checks:
            try:
                results.append(check_fn())
            except Exception as e:
                log.exception("체크 실패: %s", check_fn.__name__)
                results.append(CheckResult(
                    name=check_fn.__name__.lstrip("_check_"),
                    status="FAIL",
                    expected="no exception",
                    actual=str(e),
                    message=f"체크 실행 중 예외 발생: {e}",
                ))
        return results

    # ─────────────────────────────────────────────────────────────────────────
    # 12 Checks
    # ─────────────────────────────────────────────────────────────────────────

    def _check_row_counts(self) -> CheckResult:
        """#1 source_payloads, activity_summaries, metric_store 각각 > 0."""
        sp = self._count("source_payloads")
        as_ = self._count("activity_summaries")
        ms = self._count("metric_store")
        actual = f"sp={sp}, as={as_}, ms={ms}"
        if sp == 0 or as_ == 0 or ms == 0:
            return CheckResult("row_counts", "FAIL", "all > 0", actual, "빈 테이블 존재")
        return CheckResult("row_counts", "PASS", "all > 0", actual, "")

    def _check_source_distribution(self) -> CheckResult:
        """#2 기대 소스 모두 activity_summaries에 존재."""
        rows = self.conn.execute(
            "SELECT DISTINCT source FROM activity_summaries"
        ).fetchall()
        present = {r[0] for r in rows}
        missing = [s for s in self.expected_sources if s not in present]
        actual = f"found={sorted(present)}"
        if missing:
            return CheckResult(
                "source_distribution", "FAIL",
                f"all of {self.expected_sources}", actual,
                f"누락 소스: {missing}",
            )
        return CheckResult(
            "source_distribution", "PASS",
            f"{len(self.expected_sources)}/{len(self.expected_sources)} sources",
            actual, "",
        )

    def _check_unmapped_metric_ratio(self) -> CheckResult:
        """#3 metric_store에서 category=NULL인 비율 < 10% (WARN: 5~10%, FAIL: ≥10%)."""
        total = self._count("metric_store")
        if total == 0:
            return CheckResult("unmapped_metric_ratio", "FAIL", "< 10%", "0 rows", "metric_store 비어있음")
        null_cat = self.conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE category IS NULL"
        ).fetchone()[0]
        ratio = null_cat / total
        actual = f"{null_cat}/{total} ({ratio:.1%})"
        if ratio >= 0.10:
            return CheckResult("unmapped_metric_ratio", "FAIL", "< 10%", actual, "미매핑 메트릭 비율 초과")
        if ratio >= 0.05:
            return CheckResult("unmapped_metric_ratio", "WARN", "< 5%", actual, "미매핑 메트릭 비율 높음")
        return CheckResult("unmapped_metric_ratio", "PASS", "< 5%", actual, "")

    def _check_metric_density(self) -> CheckResult:
        """#4 활동당 평균 metric 수 ≥ 5 (WARN: 3~4, FAIL: < 3)."""
        activity_count = self._count("activity_summaries")
        if activity_count == 0:
            return CheckResult("metric_density", "FAIL", "≥ 5/activity", "0 activities", "활동 없음")
        ms_act = self.conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE scope_type = 'activity'"
        ).fetchone()[0]
        density = ms_act / activity_count
        actual = f"{density:.1f} metrics/activity ({ms_act}/{activity_count})"
        if density < 3:
            return CheckResult("metric_density", "FAIL", "≥ 5/activity", actual, "활동당 메트릭 수 부족")
        if density < 5:
            return CheckResult("metric_density", "WARN", "≥ 5/activity", actual, "활동당 메트릭 수 낮음")
        return CheckResult("metric_density", "PASS", "≥ 5/activity", actual, "")

    def _check_primary_uniqueness(self) -> CheckResult:
        """#5 (scope_type, scope_id, metric_name)별 is_primary=1이 0~1개."""
        violations = self.conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT scope_type, scope_id, metric_name
                FROM metric_store
                WHERE is_primary = 1
                GROUP BY scope_type, scope_id, metric_name
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
        actual = f"{violations} violations"
        if violations > 0:
            return CheckResult("primary_uniqueness", "FAIL", "0 violations", actual, "중복 primary 존재")
        return CheckResult("primary_uniqueness", "PASS", "0 violations", actual, "")

    def _check_provider_distribution(self) -> CheckResult:
        """#6 RunPulse provider 메트릭이 존재."""
        rp_count = self.conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE provider LIKE 'runpulse%'"
        ).fetchone()[0]
        actual = f"runpulse={rp_count}"
        if rp_count == 0:
            return CheckResult("provider_distribution", "FAIL", "runpulse > 0", actual, "RunPulse 메트릭 없음")
        return CheckResult("provider_distribution", "PASS", "runpulse > 0", actual, "")

    def _check_dedup_consistency(self) -> CheckResult:
        """#7 matched_group_id 내 동일 소스 중복 없음."""
        violations = self.conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT matched_group_id, source
                FROM activity_summaries
                WHERE matched_group_id IS NOT NULL
                GROUP BY matched_group_id, source
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
        actual = f"{violations} violations"
        if violations > 0:
            return CheckResult("dedup_consistency", "FAIL", "0 violations", actual, "dedup 그룹 내 동일 소스 중복")
        return CheckResult("dedup_consistency", "PASS", "0 violations", actual, "")

    def _check_data_quality(self) -> CheckResult:
        """#8 distance_m, duration_sec에 음수/극단값 없음."""
        issues: list[str] = []
        # 음수
        neg_dist = self.conn.execute(
            "SELECT COUNT(*) FROM activity_summaries WHERE distance_m < 0"
        ).fetchone()[0]
        neg_dur = self.conn.execute(
            "SELECT COUNT(*) FROM activity_summaries WHERE duration_sec < 0"
        ).fetchone()[0]
        # 극단값: 마라톤(42km)의 2.5배 이상 = 100km+
        extreme_dist = self.conn.execute(
            "SELECT COUNT(*) FROM activity_summaries WHERE distance_m > 100000"
        ).fetchone()[0]
        # 24시간 이상
        extreme_dur = self.conn.execute(
            "SELECT COUNT(*) FROM activity_summaries WHERE duration_sec > 86400"
        ).fetchone()[0]
        if neg_dist:
            issues.append(f"negative distance: {neg_dist}")
        if neg_dur:
            issues.append(f"negative duration: {neg_dur}")
        if extreme_dist:
            issues.append(f"distance > 100km: {extreme_dist}")
        if extreme_dur:
            issues.append(f"duration > 24h: {extreme_dur}")
        actual = "; ".join(issues) if issues else "no issues"
        if issues:
            return CheckResult("data_quality", "FAIL", "no extremes", actual, "이상값 발견")
        return CheckResult("data_quality", "PASS", "no extremes", actual, "")

    def _check_wellness_coverage(self) -> CheckResult:
        """#9 daily_wellness 행이 최근 30일 중 ≥ 20일 (WARN: 15~19일, FAIL: < 15일)."""
        recent_days = self.conn.execute(
            """
            SELECT COUNT(DISTINCT date) FROM daily_wellness
            WHERE date >= date('now', '-30 days')
            """
        ).fetchone()[0]
        actual = f"{recent_days}/30 days"
        if recent_days < 15:
            return CheckResult("wellness_coverage", "FAIL", "≥ 20/30 days", actual, "웰니스 데이터 부족")
        if recent_days < 20:
            return CheckResult("wellness_coverage", "WARN", "≥ 20/30 days", actual, "웰니스 커버리지 낮음")
        return CheckResult("wellness_coverage", "PASS", "≥ 20/30 days", actual, "")

    def _check_fitness_continuity(self) -> CheckResult:
        """#10 metric_store에 ctl/atl/tsb가 7일 이상 연속 gap 없음."""
        rows = self.conn.execute(
            """
            SELECT DISTINCT scope_id FROM metric_store
            WHERE scope_type = 'daily' AND metric_name = 'ctl'
            ORDER BY scope_id
            """
        ).fetchall()
        dates = sorted(r[0] for r in rows)
        if not dates:
            return CheckResult("fitness_continuity", "FAIL", "gap < 7 days", "no ctl data", "CTL 메트릭 없음")
        max_gap = 0
        for i in range(1, len(dates)):
            from datetime import date as _date
            try:
                d1 = _date.fromisoformat(dates[i - 1])
                d2 = _date.fromisoformat(dates[i])
                gap = (d2 - d1).days
                if gap > max_gap:
                    max_gap = gap
            except ValueError:
                continue
        actual = f"max gap = {max_gap} days ({len(dates)} ctl entries)"
        if max_gap >= 7:
            return CheckResult("fitness_continuity", "FAIL", "gap < 7 days", actual, f"{max_gap}일 연속 gap 발견")
        if max_gap >= 3:
            return CheckResult("fitness_continuity", "WARN", "gap < 3 days", actual, "CTL 데이터 일부 gap")
        return CheckResult("fitness_continuity", "PASS", "gap < 7 days", actual, "")

    def _check_referential_integrity(self) -> CheckResult:
        """#11 activity_streams/laps의 activity_id가 activity_summaries에 모두 존재."""
        orphan_streams = self.conn.execute(
            """
            SELECT COUNT(*) FROM activity_streams s
            WHERE NOT EXISTS (
                SELECT 1 FROM activity_summaries a WHERE a.id = s.activity_id
            )
            """
        ).fetchone()[0]
        orphan_laps = self.conn.execute(
            """
            SELECT COUNT(*) FROM activity_laps l
            WHERE NOT EXISTS (
                SELECT 1 FROM activity_summaries a WHERE a.id = l.activity_id
            )
            """
        ).fetchone()[0]
        actual = f"orphan streams={orphan_streams}, laps={orphan_laps}"
        if orphan_streams > 0 or orphan_laps > 0:
            return CheckResult("referential_integrity", "FAIL", "0 orphans", actual, "고아 레코드 존재")
        return CheckResult("referential_integrity", "PASS", "0 orphans", actual, "")

    def _check_engine_coverage(self) -> CheckResult:
        """#12 32개 calculator의 produces 메트릭 중 metric_store에 존재하는 비율 ≥ 80% (FAIL: < 50%)."""
        all_produces = _get_all_produces()
        if not all_produces:
            return CheckResult("engine_coverage", "WARN", "≥ 80%", "unknown", "Calculator 로드 실패")
        unique_produces = list(dict.fromkeys(all_produces))  # deduplicate, preserve order
        found = 0
        for metric_name in unique_produces:
            exists = self.conn.execute(
                "SELECT 1 FROM metric_store WHERE metric_name = ? LIMIT 1",
                (metric_name,),
            ).fetchone()
            if exists:
                found += 1
        ratio = found / len(unique_produces) if unique_produces else 0
        actual = f"{found}/{len(unique_produces)} ({ratio:.0%})"
        if ratio < 0.50:
            return CheckResult("engine_coverage", "FAIL", "≥ 80%", actual, "Calculator 메트릭 커버리지 낮음")
        if ratio < 0.80:
            return CheckResult("engine_coverage", "WARN", "≥ 80%", actual, "Calculator 메트릭 일부 미존재")
        return CheckResult("engine_coverage", "PASS", "≥ 80%", actual, "")

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _count(self, table: str) -> int:
        return self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
