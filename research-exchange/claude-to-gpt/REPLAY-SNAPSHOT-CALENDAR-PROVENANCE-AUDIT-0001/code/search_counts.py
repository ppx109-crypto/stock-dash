"""REPLAY-SNAPSHOT-CALENDAR-PROVENANCE-AUDIT-0001 · 고정 검색어 집계(정적 · git 객체만 읽음 · 저장소 코드 실행 없음).
python3 -I search_counts.py <git 저장소> <출력 JSON>
줄 본문은 저장하지 않음(경로 · 줄 번호 · 줄 sha256). 경로의 6자리 종목 코드는 C+sha256 앞 8자로 가림."""
import hashlib
import json
import re
import socket
import subprocess
import sys
from pathlib import Path

socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
REPO, OUT = Path(sys.argv[1]), Path(sys.argv[2])
H = "13e031b32186aca7e1286bb4b9119bcd9cd39700"
TERMS = {"calendar_session": ["휴장", "holiday", "거래일", "trading_day", "market_open", "개장", "임시휴장", "calendar", "달력", "weekday()",
                              "chk-holiday", "CTCA0903R", "bzdy_yn", "opnd_yn", "XKRX", "exchange_calendars", "pandas_market_calendars", "session"],
         "timezone": ["Asia/Seoul", "KST"], "snapshot_consumer": ["snaps.append", "process_day", "perf_gate", "missing", "누락"]}
red = lambda p: re.sub(r"(?<![0-9])[0-9]{6}(?![0-9])", lambda m: "C" + hashlib.sha256(m.group(0).encode()).hexdigest()[:8], p)
out = []
for axis, terms in TERMS.items():
    for t in terms:
        p = subprocess.run(["git", "-c", "core.quotePath=false", "-C", str(REPO), "grep", "-n", "-I", "-F", "-e", t, H], capture_output=True)
        rows = []
        for ln in p.stdout.decode("utf-8", "replace").splitlines():
            path, line, text = ln[len(H) + 1:].split(":", 2)
            rows.append({"path": red(path), "line": int(line), "line_sha256": hashlib.sha256(text.encode()).hexdigest()[:16]})
        files = sorted({r["path"] for r in rows})
        out.append({"axis": axis, "term": t, "git_grep_exit": p.returncode, "lines": len(rows), "files": len(files),
                    "by_file": {f: [r["line"] for r in rows if r["path"] == f] for f in files}})
OUT.write_text(json.dumps({"source_head": H, "terms": out}, ensure_ascii=False, indent=1) + "\n")
print(json.dumps([(x["term"], x["lines"], x["files"], x["git_grep_exit"]) for x in out], ensure_ascii=False))
