"""분해 v2 결론 한 줄(`conclusion{top_loss,text}`, 21 §7.2(c)) — UTRS·CIRS·RRI만.

terms에서 점수를 가장 크게 깎은(UTRS: loss, CIRS: contribution=위험 기여, RRI: 비율이 가장 낮은 요인)
항목을 골라 문장으로 만든다. 판단할 항목이 없으면 None(키 생략).
"""
from __future__ import annotations


def build_conclusion(slug: str, terms: list[dict]) -> dict | None:
    if not terms:
        return None
    if slug == "utrs":
        top = max(terms, key=lambda t: t.get("loss") or 0)
        loss = top.get("loss") or 0
        if loss <= 0:
            return None
        return {"top_loss": top["slug"], "text": f"{top['label']}이(가) 가장 크게 깎았어요 (−{loss:.0f}점)"}
    if slug == "cirs":
        top = max(terms, key=lambda t: t.get("contribution") or 0)
        contrib = top.get("contribution") or 0
        if contrib <= 0:
            return None
        return {"top_loss": top["slug"], "text": f"{top['label']}이(가) 위험을 가장 많이 올렸어요 (+{contrib:.0f}점)"}
    if slug == "rri":
        factors = [t for t in terms if t.get("role") == "factor" and t.get("ratio") is not None]
        if not factors:
            return None
        top = min(factors, key=lambda t: t["ratio"])
        if top["ratio"] >= 1.0:
            return None
        return {"top_loss": top["slug"], "text": f"{top['label']}이(가) {top['ratio'] * 100:.0f}%로 가장 낮아요"}
    return None
