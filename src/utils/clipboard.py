"""termux-clipboard-set 래퍼 유틸리티."""

import subprocess


def copy_to_clipboard(text: str) -> bool:
    """termux-clipboard-set으로 텍스트를 클립보드에 복사.

    Args:
        text: 복사할 텍스트.

    Returns:
        성공이면 True, 실패이면 False.
    """
    try:
        result = subprocess.run(
            ["termux-clipboard-set"],
            input=text,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except FileNotFoundError:
        print("termux-clipboard-set을 찾을 수 없습니다. termux-api 패키지를 설치하세요.")
        return False
    except subprocess.TimeoutExpired:
        print("클립보드 복사 시간 초과.")
        return False


def handle_clipboard_option(text: str, use_clipboard: bool) -> None:
    """--clipboard 플래그에 따라 출력 또는 클립보드 복사.

    Args:
        text: 출력할 텍스트.
        use_clipboard: True이면 클립보드 복사, False이면 stdout 출력.
    """
    print(text)
    if use_clipboard:
        if copy_to_clipboard(text):
            print("\n📋 클립보드에 복사되었습니다.")
        else:
            print("\n⚠️ 클립보드 복사에 실패했습니다.")
