"""Genspark AI 채팅 DOM 자동화 — proot subprocess 브릿지.

Termux에서 실행되는 RunPulse가 proot-distro debian 안의
Selenium + Chromium을 subprocess로 호출합니다.

전제 조건:
  1. proot-distro install debian
  2. proot-distro login debian -- apt install chromium chromium-driver python3-full
  3. python3 -m venv /root/selenium-env
  4. /root/selenium-env/bin/pip install selenium
"""
from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

_GENSPARK_URL = "https://www.genspark.ai/agents?type=ai_chat"
_PROOT_PYTHON = "/root/selenium-env/bin/python3"
_RESPONSE_TIMEOUT = 120

# proot 안에서 실행될 Selenium 스크립트
_SELENIUM_SCRIPT = r'''
import json
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

GENSPARK_URL = "https://www.genspark.ai/agents?type=ai_chat"
TIMEOUT = int(sys.argv[2]) if len(sys.argv) > 2 else 120
POLL = 2

def find_input(driver):
    for sel in ["textarea", "input[type='text']", "[contenteditable='true']"]:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed() and el.is_enabled():
                    return el
        except Exception:
            pass
    return None

def find_send_btn(driver):
    for sel in ["button[type='submit']", "button[aria-label='Send']", "button[aria-label='전송']"]:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                if el.is_displayed() and el.is_enabled():
                    return el
        except Exception:
            pass
    return None

def count_msgs(driver):
    try:
        return len(driver.find_elements(By.CSS_SELECTOR, ".message-content, .response-text, .markdown-body, [class*='message']"))
    except Exception:
        return 0

def main():
    prompt = sys.argv[1]

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1280,720")
    for p in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        import os
        if os.path.exists(p):
            options.binary_location = p
            break

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(GENSPARK_URL)
        time.sleep(5)

        inp = find_input(driver)
        if not inp:
            print(json.dumps({"error": "입력창을 찾을 수 없습니다"}))
            return

        prev = count_msgs(driver)

        driver.execute_script(
            "arguments[0].value = arguments[1]; "
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
            inp, prompt
        )
        time.sleep(0.5)

        btn = find_send_btn(driver)
        if btn:
            btn.click()
        else:
            inp.send_keys(Keys.RETURN)

        start = time.monotonic()
        last_text = ""
        stable = 0

        while time.monotonic() - start < TIMEOUT:
            time.sleep(POLL)
            try:
                msgs = driver.find_elements(By.CSS_SELECTOR, ".message-content, .response-text, .markdown-body, [class*='message']")
                if len(msgs) > prev:
                    txt = msgs[-1].text.strip()
                    if txt == last_text and txt:
                        stable += 1
                        if stable >= 3:
                            print(json.dumps({"response": txt}))
                            return
                    else:
                        last_text = txt
                        stable = 0
            except Exception:
                pass

        print(json.dumps({"response": last_text or "", "timeout": True}))
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
'''


def _is_inside_proot() -> bool:
    """현재 환경이 proot 내부인지 감지."""
    import os
    # proot 안에서는 /etc/debian_version이 존재하고 Termux 환경변수가 없음
    if os.path.exists("/etc/debian_version") and not os.environ.get("TERMUX_VERSION"):
        return True
    # Selenium import 가능하면 proot 안
    try:
        import selenium  # noqa: F401
        return True
    except ImportError:
        return False


def send_and_receive(prompt: str, timeout: int = _RESPONSE_TIMEOUT) -> str:
    """Genspark에 프롬프트를 전송하고 응답을 받아 반환.

    환경 자동 감지:
    - proot 안이면 → Selenium 직접 실행
    - Termux이면 → proot subprocess 호출

    Args:
        prompt: AI에게 보낼 프롬프트.
        timeout: 응답 대기 타임아웃 (초).

    Returns:
        AI 응답 텍스트.
    """
    if _is_inside_proot():
        return _run_selenium_direct(prompt, timeout)
    return _run_via_proot(prompt, timeout)


def _run_selenium_direct(prompt: str, timeout: int) -> str:
    """proot 안에서 직접 Selenium 실행."""
    import json as _json
    import time

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    import os
    for p in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(p):
            options.binary_location = p
            break

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.get(_GENSPARK_URL)
        time.sleep(5)

        # 입력창 찾기
        inp = None
        for sel in ["textarea", "input[type='text']", "[contenteditable='true']"]:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els:
                    if el.is_displayed() and el.is_enabled():
                        inp = el
                        break
            except Exception:
                pass
            if inp:
                break
        if not inp:
            return "Genspark 입력창을 찾을 수 없습니다."

        prev = len(driver.find_elements(By.CSS_SELECTOR, ".message-content, .response-text, .markdown-body, [class*='message']"))

        driver.execute_script(
            "arguments[0].value = arguments[1]; "
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
            inp, prompt
        )
        time.sleep(0.5)

        # 전송
        btn = None
        for sel in ["button[type='submit']", "button[aria-label='Send']"]:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els:
                    if el.is_displayed():
                        btn = el
                        break
            except Exception:
                pass
            if btn:
                break
        if btn:
            btn.click()
        else:
            inp.send_keys(Keys.RETURN)

        # 응답 대기
        start = time.monotonic()
        last_text = ""
        stable = 0
        while time.monotonic() - start < timeout:
            time.sleep(2)
            try:
                msgs = driver.find_elements(By.CSS_SELECTOR, ".message-content, .response-text, .markdown-body, [class*='message']")
                if len(msgs) > prev:
                    txt = msgs[-1].text.strip()
                    if txt == last_text and txt:
                        stable += 1
                        if stable >= 3:
                            return txt
                    else:
                        last_text = txt
                        stable = 0
            except Exception:
                pass
        return last_text or "Genspark 응답 타임아웃"
    finally:
        driver.quit()


def _run_via_proot(prompt: str, timeout: int) -> str:
    """Termux에서 proot subprocess로 Selenium 실행."""
    # 임시 파일에 스크립트 저장
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(_SELENIUM_SCRIPT)
        script_path = f.name

    try:
        log.info("Genspark 자동 모드 시작 (proot + Selenium)...")
        result = subprocess.run(
            [
                "proot-distro", "login", "debian", "--",
                _PROOT_PYTHON, script_path, prompt, str(timeout),
            ],
            capture_output=True,
            text=True,
            timeout=timeout + 30,  # subprocess 타임아웃은 넉넉하게
        )

        if result.returncode != 0:
            log.warning("proot Selenium 오류: %s", result.stderr[:300])
            return f"Genspark 자동 모드 오류: {result.stderr[:200]}"

        # JSON 파싱
        output = result.stdout.strip()
        if not output:
            return "Genspark에서 응답이 없습니다."

        try:
            data = json.loads(output)
            if "error" in data:
                return f"Genspark 오류: {data['error']}"
            response = data.get("response", "")
            if data.get("timeout"):
                response += "\n\n⚠️ 응답 대기 타임아웃 (일부 응답일 수 있습니다)"
            return response or "Genspark에서 빈 응답을 받았습니다."
        except json.JSONDecodeError:
            # JSON이 아니면 그대로 반환
            return output

    except subprocess.TimeoutExpired:
        return f"Genspark 자동 모드 타임아웃 ({timeout + 30}초)"
    except FileNotFoundError:
        return "proot-distro가 설치되지 않았습니다. pkg install proot-distro"
    except Exception as exc:
        log.warning("Genspark 자동 모드 실패: %s", exc)
        return f"Genspark 자동 모드 실패: {exc}"
    finally:
        Path(script_path).unlink(missing_ok=True)
