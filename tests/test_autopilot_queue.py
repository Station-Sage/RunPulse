"""scripts/autopilot/queue.py 테스트 — kind="code" 확장(scope/verify) 라운드트립 중심.

기존 docs 전용 큐 파싱은 이미 여러 세션의 실제 운영(P7-AUTO-*)으로 검증됐으므로,
이번에 추가한 kind/scope/verify 필드가 parse()→update_item()→재parse()를 거쳐도
안 없어지는지, docs 항목의 메타 줄 모양이 그대로 유지되는지를 검증한다.
"""
from __future__ import annotations

import pytest

from scripts.autopilot import queue


def _write(path, text):
    path.write_text(text, encoding="utf-8")


class TestParseKindDefault:
    def test_missing_kind_defaults_to_docs(self, tmp_path):
        p = tmp_path / "BACKLOG.md"
        _write(p, (
            "- **[X]** 설명\n"
            '  <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[]} -->\n'
        ))
        items = queue.parse(p)
        assert items[0].kind == "docs"
        assert items[0].scope == []
        assert items[0].verify == []


class TestParseCodeKind:
    def test_reads_kind_scope_verify(self, tmp_path):
        p = tmp_path / "BACKLOG.md"
        _write(p, (
            "- **[Y]** 설명\n"
            '  <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[],'
            '"kind":"code","scope":["src/metrics/pmc.py"],'
            '"verify":["python3 -m pytest tests/test_pmc.py -q"]} -->\n'
        ))
        items = queue.parse(p)
        item = items[0]
        assert item.kind == "code"
        assert item.scope == ["src/metrics/pmc.py"]
        assert item.verify == ["python3 -m pytest tests/test_pmc.py -q"]


class TestUpdateItemPreservesCodeFields:
    def test_stage_update_keeps_scope_and_verify(self, tmp_path):
        p = tmp_path / "BACKLOG.md"
        _write(p, (
            "- **[Y]** 설명\n"
            '  <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[],'
            '"kind":"code","scope":["src/metrics/pmc.py"],'
            '"verify":["python3 -m pytest tests/test_pmc.py -q"]} -->\n'
        ))
        queue.update_item(p, "Y", stage="in_progress", attempts=1)

        items = queue.parse(p)
        item = items[0]
        assert item.stage == "in_progress"
        assert item.attempts == 1
        assert item.kind == "code"
        assert item.scope == ["src/metrics/pmc.py"]
        assert item.verify == ["python3 -m pytest tests/test_pmc.py -q"]

    def test_docs_item_meta_shape_unchanged(self, tmp_path):
        """kind="docs"(기본값) 항목은 kind/scope/verify 키를 아예 안 적어 기존 포맷 유지."""
        p = tmp_path / "BACKLOG.md"
        _write(p, (
            "- **[X]** 설명\n"
            '  <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[]} -->\n'
        ))
        queue.update_item(p, "X", stage="review")
        text = p.read_text(encoding="utf-8")
        assert '"kind"' not in text
        assert '"scope"' not in text
        assert '"verify"' not in text


class TestFindMalformedMeta:
    def test_wrapped_meta_flagged(self, tmp_path):
        p = tmp_path / "BACKLOG.md"
        _write(p, (
            "- **[Z]** 설명\n"
            '  <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,\n'
            '       "deps":[]} -->\n'
        ))
        warnings = queue.find_malformed_meta(p)
        assert len(warnings) == 1
        assert "2행" in warnings[0]  # 줄 번호(1-indexed)만 보장, ID 파싱은 안 함

    def test_wellformed_meta_not_flagged(self, tmp_path):
        p = tmp_path / "BACKLOG.md"
        _write(p, (
            "- **[Z]** 설명\n"
            '  <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[]} -->\n'
        ))
        assert queue.find_malformed_meta(p) == []

    def test_wrapped_meta_item_silently_becomes_manual(self, tmp_path):
        """find_malformed_meta가 왜 필요한지 보여주는 회귀 테스트 — 줄바꿈된 메타는
        parse()가 예외 없이 mode="manual"로 삼켜버린다(이번 세션에서 실제로 겪은 버그)."""
        p = tmp_path / "BACKLOG.md"
        _write(p, (
            "- **[Z]** 설명\n"
            '  <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,\n'
            '       "deps":[]} -->\n'
        ))
        items = queue.parse(p)
        assert items[0].mode == "manual"  # 의도한 auto가 아니라 manual로 조용히 빠짐
        assert queue.find_malformed_meta(p) != []  # 그래서 이 함수가 미리 잡아야 함


class TestMissingMeta:
    def test_find_and_add_meta(self, tmp_path):
        p = tmp_path / "BACKLOG.md"
        _write(p, "- **[A]** 설명\n  이어진 줄\n\n- **[B]** 다른\n")
        assert [w for w in queue.find_missing_meta(p)] == ["1행 [A]", "4행 [B]"]
        queue.add_meta(p, "A", stage="done")
        items = queue.parse(p)
        assert items[0].stage == "done" and items[0].mode == "manual"
        assert items[1].meta_line_no < 0
        assert queue.find_missing_meta(p) == ["5행 [B]"]
        assert p.read_text(encoding="utf-8").splitlines()[2].lstrip().startswith("<!-- autopilot:")

    def test_add_meta_rejects_existing(self, tmp_path):
        p = tmp_path / "BACKLOG.md"
        _write(p, '- **[A]** x\n  <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[]} -->\n')
        with pytest.raises(ValueError):
            queue.add_meta(p, "A")


class TestNextRunnableIgnoresKind:
    def test_code_and_docs_both_runnable(self, tmp_path):
        p = tmp_path / "BACKLOG.md"
        _write(p, (
            "- **[A]** docs 항목\n"
            '  <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[]} -->\n'
            "- **[B]** code 항목\n"
            '  <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[],'
            '"kind":"code"} -->\n'
        ))
        items = queue.parse(p)
        first = queue.next_runnable(items)
        assert first.item_id == "A"  # 먼저 나온 순서대로, kind는 선택에 영향 없음


class TestMoveItem:
    @staticmethod
    def _q(tmp_path):
        p = tmp_path / "BACKLOG.md"
        rows = [("A", "queued"), ("B", "done"), ("C", "queued"), ("D", "queued")]
        _write(p, "".join(f'- **[{i}]** 설명 {i}\n  <!-- autopilot: {{"stage":"{s}","mode":"auto","attempts":0,"deps":[]}} -->\n\n' for i, s in rows))
        return p

    def test_up_swaps_with_previous_queued_skipping_done(self, tmp_path):
        p = self._q(tmp_path)
        assert queue.move_item(p, "C", "up") == ""
        assert [i.item_id for i in queue.parse(p)] == ["C", "A", "B", "D"]

    def test_top_moves_before_first_queued_and_keeps_meta(self, tmp_path):
        p = self._q(tmp_path)
        assert queue.move_item(p, "D", "top") == ""
        items = queue.parse(p)
        assert [i.item_id for i in items] == ["D", "A", "B", "C"]
        assert all(i.mode == "auto" for i in items)

    def test_first_and_non_queued_rejected(self, tmp_path):
        p = self._q(tmp_path)
        assert queue.move_item(p, "A", "top") == "이미 맨 앞"
        assert queue.move_item(p, "B", "up") == "대기 항목이 아님"
        assert queue.move_item(p, "D", "down") == "없는 동작"
