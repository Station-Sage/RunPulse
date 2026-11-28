"""verify 실패 처리 — 실패를 진단해 재시도(환경 복구·범위 자동 확장 포함) 또는 사용자 결정 카드로 분기한다.

run_unit 에서 분리(300줄 규칙). 반환은 (다음 stage, 추가 필드).
"""
from __future__ import annotations

import re

from scripts.audit import decisions

from . import fail_handling, queue, settings, verify_card, verify_doctor, worktree


def _scope_target(kind: str, cmd: str, out: str, item: queue.QueueItem) -> str:
    t = verify_doctor.fix_target(kind, out, item.scope)
    return t or (verify_doctor.hit_target(cmd, item.scope, settings.WORKTREE_DIR) if kind == "absence_hit" else "")


def _widen(extra: dict, item: queue.QueueItem, target: str) -> None:
    extra["scope"] = list(item.scope) + [target]
    extra["fail_reason"] = f"{extra['fail_reason']} [scope+{target}]"[:600]


def handle(item: queue.QueueItem, note: str) -> tuple[str, dict]:
    """verify 실패를 진단해 재시도(복구 조치 포함) 또는 실패 카드로 분기."""
    m = re.match(r"`(.*)` 종료코드 (\d+)\n?", note, re.S)
    cmd, rc, out = (m.group(1), int(m.group(2)), note[m.end():]) if m else ("", None, note)
    kind = verify_doctor.diagnose(cmd, rc, out)
    done = item.attempts + 1
    extra: dict = {"fail_kind": "env" if kind == "env" else "verify", "fail_reason": verify_doctor.tag_reason(kind, out)}
    if kind == "env":
        fixed = worktree.provision() if done < 3 else []  # 환경 원인(링크 누락) 복구 — 못 고치면 재시도해도 같다
        if fixed:
            extra["fail_reason"] = f"환경 자동 복구({', '.join(fixed)}) 후 재시도: {out[:200]}"
            return "queued", extra
        eco, pkg = verify_doctor.missing_package(out)
        if pkg:  # 링크로 못 고치는 외부 패키지 부재 — 임의 설치·맹목 재시도 대신 사용자에게 설치 여부를 묻는다
            reason = f"verify 가 의존성 `{pkg}` 를 찾지 못함: {out[:300]}"
            decisions.append([fail_handling.build_dep_card(item.item_id, eco, pkg, reason, item.text)])
            extra.update(fail_kind="env", fail_reason=verify_doctor.tag_reason("env", out))
            return "needs_decision", extra
    elif not verify_doctor.should_stop(done, kind, item.fail_reason):
        if kind == "missing_target":  # 없는 테스트 파일은 개발자가 만들어야 하므로 scope 에 허용
            target = verify_doctor.missing_file(cmd, out)
            if target and target not in item.scope:
                extra["scope"] = list(item.scope) + [target]
        elif kind == "absence_hit" and (target := _scope_target(kind, cmd, out, item)):  # 범위 밖 적중 파일을 scope 에 넣고 재시도
            _widen(extra, item, target)
        return "queued", extra
    target = verify_doctor.missing_file(cmd, out) if kind == "missing_target" else _scope_target(kind, cmd, out, item)
    if target and kind != "missing_target" and f"scope+{target}" not in item.fail_reason:  # 사람에게 묻기 전에 범위를 넓혀 한 번 더
        _widen(extra, item, target)
        return "queued", extra
    reason = f"[진단 {kind}] 자동 재시도 {done}회 후 중단({verify_doctor.STOP_NOTE.get(kind, '재시도 한도 도달')}). {note}"
    decisions.append([verify_card.build_verify_card(item.item_id, kind, reason, item.text, target)], fresh=True)
    return "needs_decision", extra
