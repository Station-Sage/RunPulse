"""Calculator 알고리즘 버전 변경 이력 — ◆ 마커·재계산 캡션의 단일 소스(순수 데이터, SQL 없음).

Calculator의 `version`을 올리면 여기에 항목을 함께 추가한다(tests/test_algo_changelog.py가 누락을 막는다).
날짜는 코드 반영일(커밋 날짜)이며, 사유는 사용자에게 보이는 해요체 한 줄(80자 이하)로 쓴다.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AlgoChange:
    calculator: str          # MetricCalculator.name
    version: str             # 이 항목이 도입한 calc.version
    date: str                # YYYY-MM-DD, 코드 반영일
    reason: str              # 사용자용 한 줄 사유
    prev: str | None = None  # 직전 버전. 신규 Calculator면 None(마커를 만들지 않음)
    adr: str | None = None


CHANGELOG: tuple[AlgoChange, ...] = (
    AlgoChange("runpulse_vdot", "daniels_2005", "2026-04-03", "Daniels 표 기준 VDOT 계산을 도입했어요"),
    AlgoChange("utrs", "pdf_weights_v1", "2026-04-03", "훈련 준비도 가중치를 도입했어요"),
    AlgoChange("workout_type_classified", "2.0", "2026-09-26", "훈련 유형 분류 기준을 새 예측 체계에 맞췄어요", "1.0"),
    AlgoChange("darp", "2.0", "2026-09-26", "레이스 예측 입력을 새 예측 체계(r4)로 갱신했어요", "1.0"),
    AlgoChange("darp_ref", "2.0", "2026-09-26", "레이스 예측 입력을 새 예측 체계(r4)로 갱신했어요"),
    AlgoChange("darp_r4", "4.0", "2026-09-26", "새 예측 체계(r4) 레이스 예측을 도입했어요"),
    AlgoChange("darp_r4_asym", "4.0", "2026-09-26", "새 예측 체계(r4) 비대칭 보정 예측을 도입했어요"),
    AlgoChange("di", "2.0", "2026-09-26", "내구성 지표를 새 예측 체계에 맞춰 다시 계산해요", "1.0"),
    AlgoChange("fearp", "2.0", "2026-09-26", "환경 보정 페이스를 새 예측 체계에 맞춰 다시 계산해요", "1.0"),
    AlgoChange("marathon_shape", "2.0", "2026-09-26", "마라톤 셰이프를 새 예측 체계에 맞춰 다시 계산해요", "1.0"),
    AlgoChange("tids", "2.0", "2026-09-26", "강도 분포 지표를 새 예측 체계에 맞춰 다시 계산해요", "1.0"),
    AlgoChange("training_response", "2.0", "2026-09-26", "훈련 반응 지표를 도입했어요"),
    AlgoChange("trimp", "banister_1991_v2", "2026-09-28", "심박 기반 부하 계수를 교정했어요", "banister_1991"),
    AlgoChange("ctl", "2.0", "2026-09-28", "체력·피로 반영 속도를 표준 식으로 바로잡았어요", "1.0"),
    AlgoChange("relative_effort", "2.0", "2026-09-28", "상대 노력도에 선수 최대심박과 심박 구간을 반영했어요", "1.0"),
    AlgoChange("aerobic_decoupling_rp", "2.0", "2026-09-28", "디커플링을 Friel 방식으로 바로잡았어요", "1.0"),
    AlgoChange("gap_rp", "minetti_2002_v2", "2026-09-28", "경사 보정 페이스를 30m 고도 창 기준으로 교정했어요", "minetti_2002"),
    AlgoChange("trimp_est", "trimp_est_v1", "2026-10-07", "심박이 없는 러닝의 부하를 추정하도록 했어요", adr="ADR-024"),
)


def changes_for(calculator: str) -> list[AlgoChange]:
    """해당 Calculator의 변경 항목(날짜 오름차순)."""
    return sorted((c for c in CHANGELOG if c.calculator == calculator), key=lambda c: c.date)
