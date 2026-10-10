"""Provider 매트릭스 행 정의 SSOT (S6, ADR-021).

SEMANTIC_GROUPS(활동 상세 소스 비교 탭 공용)와 분리된 매트릭스 전용 정의.
행마다 어떤 (metric, provider)를 어떻게 비교할지(kind·compare)와 정의 문구를 가진다.
provider 키는 'garmin'|'intervals'|'strava'|'runpulse' 로 정규화해 쓴다(runpulse:* → runpulse).

kind: pair_activity(같은 러닝 쌍) · pair_daily(같은 날 쌍) · profile(기간 말 최신값) · definition(비교 안 함)
compare: same(% 차이, 임계 초과 시 differs) · scale(척도 비율 ×r, 경고 없음)
"""
from __future__ import annotations

from dataclasses import dataclass, field

SECTIONS = (
    ("activity", "같은 러닝 비교"),
    ("profile", "기준값·프로필"),
    ("definition", "정의가 달라 비교하지 않는 지표"),
)
KIND_SECTION = {"pair_activity": "activity", "pair_daily": "profile", "profile": "profile", "definition": "definition"}


@dataclass(frozen=True)
class MatrixRow:
    key: str
    label: str
    unit: str | None
    format: str
    kind: str
    members: tuple[tuple[str, str, str], ...]  # (metric_name, provider, scope: activity|daily)
    compare: str = "same"
    definitions: dict[str, str] = field(default_factory=dict)
    metric_slugs: tuple[str, ...] = ()
    threshold_pct: float = 15.0

    def providers(self) -> list[str]:
        out: list[str] = []
        for _, p, _ in self.members:
            if p not in out:
                out.append(p)
        return out


ROWS: tuple[MatrixRow, ...] = (
    MatrixRow(
        "training_load", "훈련 부하", "AU", "int", "pair_activity",
        (("training_load", "garmin", "activity"), ("training_load", "intervals", "activity"),
         ("hrss", "runpulse", "activity")),
        compare="scale",
        definitions={"garmin": "EPOC 기반", "intervals": "심박 기반 부하(Intervals 정의)", "runpulse": "HRSS (LTHR 기준)"},
        metric_slugs=("hrss", "training_load"),
    ),
    MatrixRow(
        "normalized_power", "정규화 파워", "W", "int", "pair_activity",
        (("normalized_power", "garmin", "activity"), ("normalized_power", "intervals", "activity"),
         ("normalized_power", "strava", "activity")),
        definitions={"garmin": "Garmin 계산", "intervals": "Intervals 계산", "strava": "Strava 계산"},
        metric_slugs=("normalized_power",),
    ),
    MatrixRow(
        "lthr", "LTHR", "bpm", "int", "profile",
        (("lthr_self", "runpulse", "daily"), ("lthr_ref", "garmin", "daily")),
        definitions={"runpulse": "내 기록에서 추정", "garmin": "Garmin 기준값"},
        metric_slugs=("lthr_self",),
    ),
    MatrixRow(
        "hrmax", "최대심박", "bpm", "int", "profile",
        (("hrmax_self", "runpulse", "daily"), ("hrmax_ref", "garmin", "daily")),
        definitions={"runpulse": "내 기록에서 추정", "garmin": "Garmin 기준값"},
        metric_slugs=("hrmax_self",),
    ),
    MatrixRow(
        "threshold_power", "역치 파워", "W", "int", "profile",
        (("icu_ftp", "intervals", "activity"), ("garmin_ftp", "garmin", "daily"),
         ("critical_power", "runpulse", "daily")),
        definitions={"intervals": "Intervals FTP 설정값", "garmin": "Garmin FTP", "runpulse": "Critical Power 추정"},
        metric_slugs=("critical_power",),
    ),
    MatrixRow(
        "ctl", "CTL (체력 지수)", None, "float1", "pair_daily",
        (("ctl", "runpulse", "daily"), ("ctl", "intervals", "daily")),
        compare="scale",
        definitions={"runpulse": "RunPulse 부하 기준 42일 평균", "intervals": "Intervals 부하 기준 42일 평균"},
        metric_slugs=("ctl",),
    ),
    MatrixRow(
        "vo2max_vdot", "VO2max · VDOT", None, "float1", "definition",
        (("vo2max", "garmin", "daily"), ("runpulse_vdot", "runpulse", "activity")),
        definitions={"garmin": "Garmin VO2max(정밀값, 측정일)", "runpulse": "VDOT(기록 기반 환산)"},
        metric_slugs=("vo2max", "vo2max_activity", "runpulse_vdot"),
    ),
    MatrixRow(
        "efficiency_factor", "효율 지수 (EF)", None, "float2", "definition",
        (("efficiency_factor", "intervals", "activity"), ("efficiency_factor_rp", "runpulse", "activity")),
        definitions={"intervals": "파워/심박 기반", "runpulse": "속도/심박 기반(척도가 다름)"},
        metric_slugs=("efficiency_factor", "efficiency_factor_rp"),
    ),
)

_BY_KEY = {r.key: r for r in ROWS}


def get_row(key: str) -> MatrixRow | None:
    return _BY_KEY.get(key)


def compare_group_for_slug(slug: str) -> dict | None:
    """메트릭 slug가 속한 매트릭스 행 {key,label,provider}. 없으면 None."""
    for r in ROWS:
        if slug in r.metric_slugs:
            prov = next((p for m, p, _ in r.members if m == slug), r.members[0][1])
            return {"key": r.key, "label": r.label, "provider": prov}
    return None


def normalize_provider(provider: str) -> str:
    return "runpulse" if provider.startswith("runpulse") else provider
