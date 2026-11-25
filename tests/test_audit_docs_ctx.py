from scripts.audit import docs_ctx, vision


def _tree(tmp_path):
    (tmp_path / "v2" / "initiatives" / "INI-x").mkdir(parents=True)
    (tmp_path / "VISION.md").write_text("# t\n\n> n\n\n본질", encoding="utf-8")
    (tmp_path / "v2" / "PLAN.md").write_text("계획", encoding="utf-8")
    (tmp_path / "v2" / "initiatives" / "INI-x" / "DESIGN.md").write_text("설계", encoding="utf-8")
    return tmp_path


def test_vision_text_strips_header(tmp_path):
    assert docs_ctx.vision_text(_tree(tmp_path)) == "본질"


def test_context_by_role(tmp_path):
    r = _tree(tmp_path)
    c = docs_ctx.context("designer", "v2", "INI-x", root=r)
    assert "본질" in c and "계획" in c and "설계" in c
    assert docs_ctx.context("developer", "v2", "INI-x", root=r).count("[문서:") == 1


def test_context_skips_missing_and_unsafe(tmp_path):
    r = _tree(tmp_path)
    assert docs_ctx.context("planner", "v2", root=r).count("[문서:") == 2  # retro 없음
    assert "design" not in docs_ctx.paths("v2", "../x", r)


def test_vision_constant_loaded():
    assert "Evidence-First" in vision.VISION


def test_augment_appends_docs_or_passthrough(tmp_path, monkeypatch):
    from scripts.audit import release_plan
    r = _tree(tmp_path)
    monkeypatch.setattr(docs_ctx, "RELEASES", r)
    monkeypatch.setattr(docs_ctx, "ROOT", r)
    monkeypatch.setattr(release_plan, "load", lambda p=None: {"current": "v2", "versions": {"v2": {}}})
    out = docs_ctx.augment("PROMPT", "auditor")
    assert out.startswith("PROMPT") and "참고 문서" in out and "본질" in out and "계획" in out
    monkeypatch.setattr(docs_ctx, "RELEASES", tmp_path / "none")
    assert docs_ctx.augment("PROMPT", "auditor") == "PROMPT"
