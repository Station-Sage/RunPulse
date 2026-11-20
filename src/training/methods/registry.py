"""PlanMethod 정의·레지스트리와 목표별 유효 방식 조회."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Callable

from . import (first_run3, gundalf_10k_base, gundalf_sub3, hansons, higdon_novice, hr_z2, marathon_specific,
               threshold_tempo, threshold_vo2)

DEFAULT_METHOD = "balanced"


@dataclass(frozen=True)
class PlanMethod:
    id: str
    label: str
    summary: str
    distances: frozenset[str]            # resolve_distance_label 결과 ('10k','half','full' 등)
    pros: tuple[str, ...] = ()
    cons: tuple[str, ...] = ()
    target_runners: str = ""
    sources: tuple[str, ...] = ()
    min_run_days: int = 1                # 후보 가드: 선택 가능 러닝 요일이 이보다 적으면 후보 제외
    adjust: Callable[[list[dict], dict], list[dict]] | None = None   # 주간 계획 후처리 훅(balanced 는 None=무변경)


METHODS: dict[str, PlanMethod] = {
    "balanced": PlanMethod(
        id="balanced", label="균형형(기본)",
        summary="80/20 강도 배분과 Q-day 기반 현행 규칙. 대회 역산 주기화.",
        distances=frozenset({"5k", "10k", "half", "full"}),
        pros=("부상 위험이 낮음", "검증된 기본 구성"), cons=("거리별 특이성은 보통",),
        target_runners="처음이거나 어떤 방식이 맞는지 모르는 러너",
        sources=("planner v2 (papers-based)",),
    ),
    "gundalf_sub3": PlanMethod(
        id="gundalf_sub3", label="건달프 서브3",
        summary="화 400m 인터벌·수 AR·토 하프 지속주/장거리 교대·금 휴식. 팀 DBS(A) 토요일 표와 같은 골격.",
        distances=frozenset({"full"}), min_run_days=5,
        pros=("마라톤 페이스 지속 능력 직접 훈련", "토요일 장거리 구성이 명확"),
        cons=("주 80~110km 전제라 볼륨 낮으면 부담", "주 5일 이상 필요", "부상 위험 높음"),
        target_runners="서브3 안팎을 노리는 주 5일 이상 고볼륨 러너",
        sources=("건달프 서브3 훈련법", "Team DBS (A) 17주 표"),
        adjust=gundalf_sub3.adjust,
    ),
    "gundalf_10k_base": PlanMethod(
        id="gundalf_10k_base", label="건달프 10K 베이스",
        summary="화 5K·토 10K 기준 달리기와 이지 조깅 중심. 지난주 결과로 다음 주 목표 페이스를 올리거나 내린다.",
        distances=frozenset({"10k"}), min_run_days=4,
        pros=("복잡한 인터벌 없이 꾸준한 향상", "결과에 따라 목표가 자동 조정"),
        cons=("서브3:10보다 빠른 러너에겐 자극 부족", "기준 달리기 2회에 의존"),
        target_runners="10K 기록을 꾸준히 줄이려는 서브3:10보다 느린 러너",
        sources=("건달프 10K 베이스 블록",),
        adjust=gundalf_10k_base.adjust,
    ),
    "threshold_vo2": PlanMethod(
        id="threshold_vo2", label="임계값+VO2max",
        summary="T 크루즈 인터벌(5분 반복)과 I 페이스 반복 중심, 롱런은 이지. 빌드·피크에 VO2max 추가.",
        distances=frozenset({'10k'}), min_run_days=4,
        pros=("10K 레이스 페이스 직결 자극","세션 구성이 명확"), cons=("인터벌 강도가 높아 부상·피로 위험","주 4일 이상 필요"),
        target_runners="속도를 끌어올리고 싶은 중급 이상 10K 러너",
        sources=("Daniels Running Formula(2차 자료로 확인, 일부 수치는 일반 규칙으로 보완)",),
        adjust=threshold_vo2.adjust,
    ),
    "threshold_tempo": PlanMethod(
        id="threshold_tempo", label="임계값 템포",
        summary="지속 템포(T 페이스 20→40분)와 크루즈 인터벌 중심, 롱런은 이지.",
        distances=frozenset({'half'}), min_run_days=4,
        pros=("하프 레이스 지속 능력 향상","강도 관리가 쉬움"), cons=("속도 자극이 적음","주 4일 이상 필요"),
        target_runners="하프 기록 단축을 노리는 주 4일 이상 러너",
        sources=("Daniels Running Formula(2차 자료, 20분 초과 지속 템포는 일반 규칙으로 보완)",),
        adjust=threshold_tempo.adjust,
    ),
    "hr_z2": PlanMethod(
        id="hr_z2", label="심박 Z2 중심",
        summary="대부분 존2 이지, 빌드·피크에 짧은 템포 1회. 롱런도 존2.",
        distances=frozenset({'full'}), min_run_days=3,
        pros=("부상 위험 낮음","유산소 기반 확장"), cons=("속도·레이스 특이 자극 부족","기록 단축 속도는 느림"),
        target_runners="부상 이력이 있거나 유산소 기반이 부족한 마라토너",
        sources=("Maffetone·80/20 계열 일반 원칙(일반 규칙으로 보완)",),
        adjust=hr_z2.adjust,
    ),
    "marathon_specific": PlanMethod(
        id="marathon_specific", label="마라톤 특이성",
        summary="LT 데이·미디엄롱·마라톤 페이스 구간 롱런·롱런 다음날 회복 구성(Pfitzinger 계열).",
        distances=frozenset({'full'}), min_run_days=4,
        pros=("마라톤 특이 지구력 직접 훈련","주기화가 체계적"), cons=("주중 장거리 포함 부담","주 4일 이상 필요"),
        target_runners="주 55km 이상, 서브4 안팎 기록을 노리는 마라토너",
        sources=("Pfitzinger Advanced Marathoning 18/55 구조(2차 자료, 수치는 일반 규칙으로 보완)",),
        adjust=marathon_specific.adjust,
    ),
    "hansons": PlanMethod(
        id="hansons", label="Hansons",
        summary="SOS 3세션(스피드/스트렝스·마라톤 페이스 템포·롱런)+이지 6일, 롱런 26km 이내.",
        distances=frozenset({'full'}), min_run_days=6,
        pros=("롱런을 짧게 유지해 부상 부담 완화","레이스 페이스 적응"), cons=("주 6일 러닝 필요","누적 피로 속 훈련으로 컨디션 관리 필요"),
        target_runners="주 6일 달릴 수 있고 레이스 페이스 적응을 원하는 마라토너",
        sources=("Hansons Marathon Method(2차 자료, 세부 거리는 일반 규칙으로 보완)",),
        adjust=hansons.adjust,
    ),
    "first_run3": PlanMethod(
        id="first_run3", label="FIRST 주3",
        summary="러닝 주 3회(트랙 반복·템포·롱런)+교차훈련 2회. 질 높은 3세션만 수행.",
        distances=frozenset({'10k', 'half', 'full'}), min_run_days=3,
        pros=("러닝 횟수가 적어 시간·관절 부담 적음","세션 목적이 뚜렷"), cons=("세션 강도가 높아 컨디션 관리 필요","러닝 볼륨이 작음"),
        target_runners="주 3일만 달리고 교차훈련을 병행할 수 있는 러너",
        sources=("Run Less Run Faster(FIRST, 2차 자료, 세부 수치는 일반 규칙으로 보완)",),
        adjust=first_run3.adjust,
    ),
    "higdon_novice": PlanMethod(
        id="higdon_novice", label="Higdon 노비스",
        summary="속도훈련 없이 이지 위주 주 4회, 점진 롱런. 완주가 목표인 입문 플랜.",
        distances=frozenset({'half', 'full'}), min_run_days=3,
        pros=("부담 낮고 따라 하기 쉬움","완주 중심"), cons=("기록 단축 자극 부족","고급 러너에겐 부족"),
        target_runners="첫 하프·풀 완주가 목표인 입문 러너",
        sources=("Hal Higdon Novice 1(2차 자료, 일반 규칙으로 보완)",),
        adjust=higdon_novice.adjust,
    ),
}


def get_method(method_id: str | None) -> PlanMethod:
    """알 수 없거나 비어 있으면 balanced."""
    return METHODS.get(method_id or DEFAULT_METHOD, METHODS[DEFAULT_METHOD])


def candidates_for(distance_label: str, run_days: int | None = None) -> list[PlanMethod]:
    """거리·러닝 요일 수 하드 가드를 통과한 방식(추천 후보). 경고성 부적합은 여기서 거르지 않는다."""
    out = [m for m in METHODS.values()
           if distance_label in m.distances and (run_days is None or run_days >= m.min_run_days)]
    return out or [METHODS[DEFAULT_METHOD]]


def goal_method(conn: sqlite3.Connection, goal_id: int | None) -> str:
    """goals.plan_method (컬럼·행이 없으면 balanced)."""
    if goal_id is None:
        return DEFAULT_METHOD
    try:
        row = conn.execute("SELECT plan_method FROM goals WHERE id = ?", (goal_id,)).fetchone()
    except sqlite3.OperationalError:
        return DEFAULT_METHOD
    return get_method(row[0] if row else None).id


def effective_method(conn: sqlite3.Connection, goal_id: int | None, week_start=None) -> str:
    """주 기준 유효 방식: 그 주 이전(포함) 마지막 applied 재계획 anchor 의 plan_method, 없으면 목표 값.

    week_start 가 None 이면 날짜와 무관하게 마지막 applied anchor 를 쓴다(과거 주는 과거 방식 유지, undo 는 status 로 반영)."""
    if goal_id is None:
        return DEFAULT_METHOD
    q = "SELECT plan_method FROM plan_replans WHERE goal_id = ? AND status = 'applied' AND plan_method IS NOT NULL"
    args: list = [goal_id]
    if week_start is not None:
        q += " AND anchor_monday <= ?"
        args.append(week_start.isoformat() if hasattr(week_start, "isoformat") else week_start)
    try:
        row = conn.execute(q + " ORDER BY anchor_monday DESC, id DESC LIMIT 1", args).fetchone()
    except sqlite3.OperationalError:
        row = None
    return get_method(row[0]).id if row else goal_method(conn, goal_id)
