"""REPLAY-CA-INPUT-PROVENANCE-AUDIT-0001 · INVENTORY 경로 안 6자리 종목 코드 가리기(감사 재실행 아님 · 출력만 결정적으로 바꿈).
python3 -I redact_paths.py <INVENTORY.json>
6자리 숫자 → 'C' + sha256(숫자) 앞 8자. blob sha는 그대로라 저장소 트리와 대조 가능."""
import hashlib
import re
import sys
from pathlib import Path

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
pat = re.compile(r'("path": ")([^"]*)(")')
n = 0


def red(m):
    global n
    new = re.sub(r"(?<![0-9])[0-9]{6}(?![0-9])", lambda d: "C" + hashlib.sha256(d.group(0).encode()).hexdigest()[:8], m.group(2))
    n += new != m.group(2)
    return m.group(1) + new + m.group(3)


p.write_text(pat.sub(red, s), encoding="utf-8")
print({"redacted_paths": n})
