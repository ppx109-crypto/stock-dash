"""장 마감 뒤 하루 한 번, 모아 둔 종목의 DART 자료를 다시 받습니다.

받을 종목은 public-data에 이미 있는 종목입니다. PUBLIC_CODES로 직접 지정할 수도
있습니다. DART 한 번에 묻는 수를 25개로 제한하고 있어, 나눠서 차례로 받습니다.

내용이 달라지지 않은 파일은 다시 쓰지 않습니다. 수집일(fetched)만 바뀐 파일까지
저장하면 매일 커밋이 생기고, 커밋할 때마다 Streamlit이 다시 시작돼 저장해 둔
관심종목과 투자일지가 지워집니다. 실제로 바뀐 것이 있을 때만 남깁니다.
"""
import json
import os
import re
from pathlib import Path

from collect_public_dart import Official, collect

CHUNK = 25
FOLDER = Path("public-data")


def stored_codes():
    return sorted(p.stem for p in FOLDER.glob("*.json")
                  if re.fullmatch(r"[0-9]{6}", p.stem))


def same_apart_from_fetched(old, new):
    """수집일만 다르고 내용이 같은지 봅니다."""
    return {k: v for k, v in old.items() if k != "fetched"} == \
           {k: v for k, v in new.items() if k != "fetched"}


def run(codes=None):
    codes = codes or stored_codes()
    if not codes:
        print("받을 종목이 없습니다.")
        return 0, 0, 0
    FOLDER.mkdir(exist_ok=True)
    shared = Official()
    changed, same, failed = 0, 0, 0
    for start in range(0, len(codes), CHUNK):
        for code in codes[start:start + CHUNK]:
            target = FOLDER / f"{code}.json"
            try:
                data = collect(code, shared)
            except Exception as error:
                failed += 1
                print(f"{code} 수집 실패 · 기존 파일 유지 · {str(error)[:60]}")
                continue
            if target.exists():
                try:
                    old = json.loads(target.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    old = None
                if old and same_apart_from_fetched(old, data):
                    same += 1
                    continue
            target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            changed += 1
            print(f"{code} 갱신")
    print(f"갱신 {changed} · 변화 없음 {same} · 실패 {failed} · 대상 {len(codes)}종목")
    return changed, same, failed


if __name__ == "__main__":
    picked = [c.strip() for c in os.getenv("PUBLIC_CODES", "").split(",") if c.strip()]
    if picked and any(not re.fullmatch(r"[0-9]{6}", c) for c in picked):
        raise SystemExit("종목코드는 숫자 6자리여야 합니다.")
    changed, same, failed = run(picked or None)
    if changed:
        from build_research_bundle import build
        path, count = build()
        print(f"조사 파일 갱신 · {path} · {count}종목")
    else:
        print("바뀐 자료가 없어 조사 파일은 그대로 둡니다.")
    # 전부 실패했을 때만 실패로 끝냅니다.
    raise SystemExit(1 if failed and not changed and not same else 0)
