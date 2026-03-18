# RunPulse - 브랜치 전략

## 규칙
- main: 프로덕션 전용. 직접 푸시 금지
- dev: 개발 기본 브랜치. 모든 PR의 타겟
- claude/기능명: Claude Code가 자동 생성하는 브랜치. dev에서 분기
- feature/기능명: 수동 기능 개발
- fix/이슈명: 버그 수정
- docs/설명: 문서만 변경 시

## PR 규칙
- 모든 PR은 dev를 타겟으로 한다
- squash merge 사용
- main으로의 merge는 수동 검토 후에만

## 커밋 규칙
- conventional commits: feat: fix: docs: refactor: test: chore:
- 로컬에서 자주 커밋, 푸시 전 squash

## 워크플로 예시

    git checkout dev
    git pull origin dev
    git checkout -b claude/p1-db-setup
    (작업)
    git add -A
    git commit -m "feat: implement SQLite schema setup"
    git push origin claude/p1-db-setup
    (GitHub에서 PR 생성 -> dev)
