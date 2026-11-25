"""제품 본질·비전 블록 — 모든 감사·설계·검토 프롬프트에 주입한다(원본: v0.3/data/releases/VISION.md, 파일이 없으면 내장 사본)."""
from scripts.audit import docs_ctx

_FALLBACK = """[제품 본질] RunPulse 는 '개인 러닝 인텔리전스 플랫폼'이다."""
VISION = docs_ctx.vision_text() or _FALLBACK
