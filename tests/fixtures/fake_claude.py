"""session_pool 테스트용 가짜 claude CLI — stream-json 다중 턴·interrupt 흉내."""
import json
import select
import sys
import time

sid = sys.argv[sys.argv.index("--session-id") + 1] if "--session-id" in sys.argv else (
    sys.argv[sys.argv.index("--resume") + 1] if "--resume" in sys.argv else "none")
if "--resume" in sys.argv and "BADRESUME" in " ".join(sys.argv):
    sys.exit(1)
turn = 0


def out(o):
    sys.stdout.write(json.dumps(o) + "\n")
    sys.stdout.flush()


out({"type": "system", "subtype": "init", "session_id": sid})
for line in sys.stdin:
    m = json.loads(line)
    if m.get("type") == "control_request":
        continue
    text = m["message"]["content"]
    turn += 1
    if "SLOW" in text:
        t0 = time.time()
        while time.time() - t0 < 30:
            if select.select([sys.stdin], [], [], 0.05)[0]:
                if json.loads(sys.stdin.readline()).get("type") == "control_request":
                    out({"type": "result", "subtype": "success", "session_id": sid, "result": None, "usage": {}})
                    break
        continue
    for _ in range(3 if "TOOLS" in text else 0):
        out({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "x"}]}})
    out({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "a"}}})
    out({"type": "result", "subtype": "success", "session_id": sid, "result": f"turn{turn}:{text[:20]}",
         "usage": {"input_tokens": 10, "output_tokens": 5}})
