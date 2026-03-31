#!/usr/bin/env python3
"""기존 config.json 파일의 자격증명을 Fernet으로 암호화하는 마이그레이션 스크립트.

사용법:
  # 1. .env에 CREDENTIAL_ENCRYPTION_KEY 설정 후 실행
  python scripts/encrypt_existing_configs.py

  # 2. 드라이런 (실제 파일 변경 없음)
  python scripts/encrypt_existing_configs.py --dry-run

  # 3. 새 키 생성
  python scripts/encrypt_existing_configs.py --generate-key

처리 대상:
  - config.json (프로젝트 루트)
  - data/users/*/config.json (사용자별)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


def _load_dotenv() -> None:
    """프로젝트 루트 .env 파일 로드."""
    env_path = _PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    import os
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _collect_config_paths() -> list[Path]:
    """암호화 대상 config.json 경로 목록 반환."""
    paths: list[Path] = []

    root_config = _PROJECT_ROOT / "config.json"
    if root_config.exists():
        paths.append(root_config)

    users_dir = _PROJECT_ROOT / "data" / "users"
    if users_dir.exists():
        for user_dir in sorted(users_dir.iterdir()):
            if user_dir.is_dir():
                user_config = user_dir / "config.json"
                if user_config.exists():
                    paths.append(user_config)

    return paths


def _encrypt_file(config_path: Path, dry_run: bool) -> tuple[int, int]:
    """단일 config.json 암호화. (암호화된 필드 수, 이미 암호화된 필드 수) 반환."""
    from src.utils.credential_store import encrypt_config_credentials, _ENC_PREFIX

    with open(config_path, encoding="utf-8") as f:
        original = json.load(f)

    encrypted = encrypt_config_credentials(original)

    # 변경된 필드 수 계산
    n_encrypted = 0
    n_already = 0
    for service, section in encrypted.items():
        if not isinstance(section, dict):
            continue
        orig_section = original.get(service, {})
        if not isinstance(orig_section, dict):
            continue
        for key, new_val in section.items():
            orig_val = orig_section.get(key, "")
            if isinstance(new_val, str) and new_val.startswith(_ENC_PREFIX):
                if isinstance(orig_val, str) and orig_val.startswith(_ENC_PREFIX):
                    n_already += 1
                else:
                    n_encrypted += 1

    if n_encrypted == 0:
        return 0, n_already

    if not dry_run:
        backup = config_path.with_suffix(".json.bak")
        config_path.rename(backup)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(encrypted, f, indent=2, ensure_ascii=False)
        print(f"  백업: {backup.name}")

    return n_encrypted, n_already


def main() -> None:
    parser = argparse.ArgumentParser(description="config.json 자격증명 암호화 마이그레이션")
    parser.add_argument("--dry-run", action="store_true", help="실제 파일 변경 없이 미리보기")
    parser.add_argument("--generate-key", action="store_true", help="새 Fernet 키 생성 후 종료")
    args = parser.parse_args()

    if args.generate_key:
        from src.utils.credential_store import generate_key
        key = generate_key()
        print(f"\n새 CREDENTIAL_ENCRYPTION_KEY:\n  {key}")
        print("\n.env 파일에 다음 줄을 추가하세요:")
        print(f"  CREDENTIAL_ENCRYPTION_KEY={key}\n")
        return

    _load_dotenv()

    import os
    if not os.environ.get("CREDENTIAL_ENCRYPTION_KEY"):
        print("오류: CREDENTIAL_ENCRYPTION_KEY 환경변수가 설정되지 않았습니다.")
        print("먼저 키를 생성하세요: python scripts/encrypt_existing_configs.py --generate-key")
        sys.exit(1)

    paths = _collect_config_paths()
    if not paths:
        print("암호화할 config.json 파일이 없습니다.")
        return

    print(f"{'[DRY-RUN] ' if args.dry_run else ''}총 {len(paths)}개 파일 처리\n")

    total_encrypted = 0
    total_already = 0
    for path in paths:
        rel = path.relative_to(_PROJECT_ROOT)
        n_enc, n_already = _encrypt_file(path, dry_run=args.dry_run)
        if n_enc > 0:
            action = "암호화 예정" if args.dry_run else "암호화 완료"
            print(f"  [{action}] {rel}: {n_enc}개 필드")
        elif n_already > 0:
            print(f"  [건너뜀] {rel}: {n_already}개 이미 암호화됨")
        else:
            print(f"  [변경없음] {rel}: 민감 필드 없음")
        total_encrypted += n_enc
        total_already += n_already

    print(f"\n완료: 암호화 {total_encrypted}개, 기존 {total_already}개")
    if args.dry_run:
        print("(--dry-run 모드: 실제 파일 변경 없음)")


if __name__ == "__main__":
    main()
