"""Genspark AI 채팅 DOM 자동화 — proot + Selenium headless Chromium.

전제 조건:
  1. proot-distro install debian
  2. proot-distro login debian
  3. apt install chromium chromium-driver
  4. pip install selenium

사용:
  from src.ai.genspark_driver import send_and_receive
  response = send_and_receive("오늘 훈련 강도는?")
"""
from __future__ import annotations

import logging
import time

log = logging.getLogger(__name__)

_GENSPARK_URL = "https://www.genspark.ai/agents?type=ai_chat"

# DOM 셀렉터 (Genspark 페이지 구조에 따라 변경 필요)
_INPUT_SELECTOR = 'textarea[placeholder], input[type="text"]'
_SEND_BUTTON_SELECTOR = 'button[type="submit"], button[aria-label="Send"]'
_RESPONSE_SELECTOR = '.message-content, .response-text, .markdown-body'

# 타임아웃 설정
_PAGE_LOAD_TIMEOUT = 30
_RESPONSE_WAIT_TIMEOUT = 120
_POLL_INTERVAL = 2


def _create_driver():
    """Selenium Chrome 드라이버 생성 (headless, no-sandbox)."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1280,720")
    # Termux proot에서 Chromium 경로
    for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"]:
        import os
        if os.path.exists(path):
            options.binary_location = path
            break

    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)


def send_and_receive(prompt: str, timeout: int = _RESPONSE_WAIT_TIMEOUT) -> str:
    """Genspark에 프롬프트를 전송하고 응답을 받아 반환.

    Args:
        prompt: AI에게 보낼 프롬프트.
        timeout: 응답 대기 타임아웃 (초).

    Returns:
        AI 응답 텍스트.

    Raises:
        RuntimeError: DOM 요소를 찾을 수 없거나 타임아웃.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    driver = _create_driver()
    try:
        log.info("Genspark 페이지 로딩...")
        driver.get(_GENSPARK_URL)
        time.sleep(5)  # 초기 로딩 대기

        # 입력창 찾기
        input_el = _find_input(driver)
        if not input_el:
            raise RuntimeError("Genspark 입력창을 찾을 수 없습니다. DOM 구조가 변경되었을 수 있습니다.")

        # 기존 메시지 수 기록 (응답 감지용)
        existing_msgs = _count_messages(driver)

        # 프롬프트 입력 + 전송
        log.info("프롬프트 전송 중...")
        input_el.clear()
        # 긴 프롬프트는 JS로 주입
        driver.execute_script(
            "arguments[0].value = arguments[1]; "
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
            input_el, prompt
        )
        time.sleep(0.5)

        # 전송 버튼 클릭 또는 Enter
        send_btn = _find_send_button(driver)
        if send_btn:
            send_btn.click()
        else:
            input_el.send_keys(Keys.RETURN)

        # 응답 대기
        log.info("응답 대기 (최대 %d초)...", timeout)
        response = _wait_for_response(driver, existing_msgs, timeout)

        if not response:
            raise RuntimeError(f"응답 타임아웃 ({timeout}초)")

        log.info("응답 수신 완료 (%d자)", len(response))
        return response

    finally:
        driver.quit()


def _find_input(driver) -> object | None:
    """입력창 찾기 — 여러 셀렉터 시도."""
    from selenium.webdriver.common.by import By

    selectors = [
        'textarea',
        'input[type="text"]',
        '[contenteditable="true"]',
        _INPUT_SELECTOR,
    ]
    for sel in selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed() and el.is_enabled():
                    return el
        except Exception:
            pass
    return None


def _find_send_button(driver) -> object | None:
    """전송 버튼 찾기."""
    from selenium.webdriver.common.by import By

    selectors = [
        'button[type="submit"]',
        'button[aria-label="Send"]',
        'button[aria-label="전송"]',
        'button svg',  # 아이콘 버튼
    ]
    for sel in selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed() and el.is_enabled():
                    return el
        except Exception:
            pass
    return None


def _count_messages(driver) -> int:
    """현재 메시지 수 카운트."""
    from selenium.webdriver.common.by import By
    try:
        msgs = driver.find_elements(By.CSS_SELECTOR, _RESPONSE_SELECTOR)
        return len(msgs)
    except Exception:
        return 0


def _wait_for_response(driver, prev_count: int, timeout: int) -> str:
    """새 메시지가 나타날 때까지 polling."""
    from selenium.webdriver.common.by import By

    start = time.monotonic()
    last_text = ""
    stable_count = 0

    while time.monotonic() - start < timeout:
        time.sleep(_POLL_INTERVAL)
        try:
            msgs = driver.find_elements(By.CSS_SELECTOR, _RESPONSE_SELECTOR)
            if len(msgs) > prev_count:
                # 마지막 메시지 텍스트
                current_text = msgs[-1].text.strip()
                if current_text == last_text and current_text:
                    stable_count += 1
                    if stable_count >= 3:  # 6초간 변화 없으면 완료
                        return current_text
                else:
                    last_text = current_text
                    stable_count = 0
        except Exception:
            pass

    return last_text  # 타임아웃이어도 마지막 텍스트 반환
