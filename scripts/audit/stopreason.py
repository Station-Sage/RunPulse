"""루프 정지 사유 enum — 자유 문자열 매칭 대신 cycle_state.json 의 stop_reason 으로 정지/자동 재개를 판단한다.

사유별 재개 정책(타이머 발화 시 `resume`):
  pacing·step_cap : 그대로 재개(상태 유지)    round_done : 새 라운드(감사)로 재개
  failed          : 타이머는 재개 안 함(알림만), 사람이 콘솔로 재개하면 fails 초기화 후 이어감
  stop_flag       : 타이머는 재개 안 함, 사람이 콘솔로 재개하면 정지 순간(resume_at)부터 이어감
정지 순간의 단계·항목·라운드는 stop() 이 st["resume_at"] 에 한 번만 기록하고, 재개(타이머·콘솔 공통 resume)는 그 값만 쓴다.
await_decision : 버전 계획·이니셔티브 승인 등 사용자 결정이 있어야 이어갈 수 있는 정지 — 자동 재개 안 함(결정 반영 시 콘솔이 해제)
role_pause : 콘솔 역할 패널의 역할 일시정지 — 자동 재개 안 함, 사람이 '재개'하면 단계(phase)를 유지한 채 이어간다
항목 단위 needs_decision 은 정지 사유가 아니다 — 그 항목만 건너뛰고 진행하며 state["pending_decisions"] 로만 노출한다.
"""
from __future__ import annotations

PACING, ROUND_DONE, FAILED, STOP_FLAG, STEP_CAP = "pacing", "round_done", "failed", "stop_flag", "step_cap"
AWAIT_DECISION = "await_decision"
ROLE_PAUSE = "role_pause"
ALL = (PACING, ROUND_DONE, FAILED, STOP_FLAG, STEP_CAP, AWAIT_DECISION, ROLE_PAUSE)
AUTO_RESUME = (PACING, ROUND_DONE, STEP_CAP)


def stop(st: dict, reason: str) -> None:
    if reason not in ALL:
        raise ValueError(f"알 수 없는 정지 사유: {reason}")
    if st.get("stop_reason") is None and st.get("phase") not in ("stopped", "halted"):
        st["resume_at"] = {"phase": st.get("phase"), "unit": st.get("unit"), "round": st.get("round")}
    st["stop_reason"] = reason


def is_stopped(st: dict) -> bool:
    return st.get("stop_reason") is not None


HUMAN_RESUME = AUTO_RESUME + (FAILED, STOP_FLAG, ROLE_PAUSE)


def resume(st: dict, human: bool = False) -> bool:
    """정지를 풀고 resume_at 지점(없으면 감사)부터 이어간다. 타이머는 AUTO_RESUME 사유만, 사람(콘솔)은 HUMAN_RESUME 까지(fails 초기화).
    그 외 사유(await_decision 등)는 타이머면 상태 유지 후 False, 사람이면 감사부터 다시 시작한다."""
    r = st.get("stop_reason")
    if r is None and st.get("phase") not in ("stopped", "halted"):
        st.pop("resume_at", None)
        return True
    if r not in (HUMAN_RESUME if human else AUTO_RESUME):
        if not human:
            return False
        st.update(phase="audit", fails=0, unit=None, stop_reason=None, cursor=None)
        st.pop("resume_at", None)
        return True
    at = st.pop("resume_at", None) or st.get("cursor") or {}
    st["stop_reason"] = None
    if st.get("phase") in ("stopped", "halted"):
        st["phase"], st["unit"] = at.get("phase") or "audit", at.get("unit")
    if human:
        st["fails"] = 0
    return True
