"""코스닥 상장 전체의 일봉(시가 · 고가 · 저가 · 종가 · 거래량 · 거래대금)을 kosdaq-data/에 따로 모읍니다(코스닥 갈래 연구 · 사용자 2026-10-02).

운영이 읽는 price-data/ · volume-data/와 섞지 않습니다(그 폴더는 운영 도구 · 자료 확인 장치가 통째로 읽음).
종목 목록: 한투 공개 종목 목록(kosdaq_code.mst · 키 없이 받는 공개 파일)에서 주식(ST)만 · 스팩 뺌 → study/kosdaq_codes.json.
수정주가 · 2015-01부터. 한 종목을 다 받으면 그 자리에서 저장하고, 다시 돌리면 끝까지 받은 종목은 앞쪽 새 날만 붙입니다. 조회 전용 · 주문과 무관.
쓰는 법: python collect_kosdaq.py list   → 종목 목록을 만들고 묶음(쉼표)을 줄마다 찍음
         KOSDAQ_CODES=a,b,c python collect_kosdaq.py   → 그 종목들을 받음"""
import concurrent.futures
import io
import json
import os
import re
import sys
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

OUT = Path("kosdaq-data")
LIST = Path("study") / "kosdaq_codes.json"
MASTER = "https://new.real.download.dws.co.kr/common/master/kosdaq_code.mst.zip"
SINCE = os.getenv("KOSDAQ_SINCE", "20150101")


def parse_master(raw: bytes):
    """kosdaq_code.mst 줄 → [(코드, 이름)]. 줄 끝 222바이트는 뒷칸(첫 두 글자 = 증권 그룹: ST 주식)."""
    found = []
    for line in raw.splitlines():
        if len(line) < 240:
            continue
        head, tail = line[:-222], line[-222:]
        code = head[0:9].decode("cp949", "ignore").strip()
        name = head[21:].decode("cp949", "ignore").strip()
        group = tail[0:2].decode("cp949", "ignore").strip()
        if re.fullmatch(r"[0-9]{6}", code) and group == "ST" and "스팩" not in name:
            found.append((code, name))
    return found


def make_list():
    with urllib.request.urlopen(MASTER, timeout=60) as resp:
        body = resp.read()
    with zipfile.ZipFile(io.BytesIO(body)) as zf:
        raw = zf.read(zf.namelist()[0])
    rows = parse_master(raw)
    if len(rows) < 1000:
        raise SystemExit(f"코스닥 종목 목록이 너무 적습니다({len(rows)}) · 파일 꼴이 바뀌었을 수 있음")
    LIST.write_text(json.dumps({"made": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M"),
                                "codes": [c for c, _ in rows], "names": dict(rows)}, ensure_ascii=False), encoding="utf-8")
    return [c for c, _ in rows]


def load(code):
    try:
        return json.loads((OUT / f"{code}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save(code, name, rows):
    OUT.mkdir(exist_ok=True)
    cols = ["date", "시가", "고가", "저가", "종가", "거래량", "거래대금"]
    lines = ",\n".join(json.dumps([d] + [g.get(c) for c in cols[1:]], ensure_ascii=False) for d, g in rows)
    head = json.dumps({"code": code, "name": name, "cols": cols,
                       "fetched": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")}, ensure_ascii=False)
    (OUT / f"{code}.json").write_text(head[:-1] + ', "rows": [\n' + lines + "\n]}\n", encoding="utf-8")


def fetch(client, code):
    """있으면 마지막 날 뒤만, 없으면 SINCE부터 끝까지."""
    old = load(code)
    have = {r[0]: dict(zip(old["cols"][1:], r[1:])) for r in old["rows"]} if old else {}
    start = (max(have) if have else SINCE)
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d")
    if have and start >= today:
        return None
    first = datetime.strptime(SINCE, "%Y%m%d").date()
    days = (datetime.now(ZoneInfo("Asia/Seoul")).date() - (datetime.strptime(start, "%Y%m%d").date() if have else first)).days + 5
    got = client.history(code, days=days, detail=True)
    for d, g in got:
        if d >= SINCE:
            have[d] = g
    return sorted(have.items())


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        codes = make_list()
        size = int(os.getenv("KOSDAQ_BATCH", "60"))
        # 아직 안 받은 종목 먼저
        codes = [c for c in codes if not (OUT / f"{c}.json").exists()] + [c for c in codes if (OUT / f"{c}.json").exists()]
        for k in range(0, len(codes), size):
            print(",".join(codes[k:k + size]))
        return 0
    import broker_kis
    codes = [c.strip() for c in os.getenv("KOSDAQ_CODES", "").split(",") if re.fullmatch(r"[0-9]{6}", c.strip())]
    names = json.loads(LIST.read_text(encoding="utf-8")).get("names", {}) if LIST.exists() else {}
    try:
        client = broker_kis.market()
    except broker_kis.BrokerError as error:
        print("증권사 연결을 만들지 못했습니다 ·", error)
        return 1
    lanes = max(1, int(os.getenv("KOSDAQ_LANES", "4")))
    ok = fail = 0
    in_a_row = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=lanes) as pool:
        tasks = {pool.submit(fetch, client, c): c for c in codes}
        for t in concurrent.futures.as_completed(tasks):
            c = tasks[t]
            try:
                rows = t.result()
            except broker_kis.BrokerError as error:
                fail += 1
                in_a_row += 1
                print(f"{c} · 실패 · {str(error)[:60]}", flush=True)
                if in_a_row >= 8:
                    print("잇달아 실패해 멈춥니다.", flush=True)
                    return 2
                continue
            in_a_row = 0
            if rows is None:
                continue
            if rows:
                save(c, names.get(c, c), rows)
                ok += 1
                print(f"{c} · {len(rows)}일 · {rows[0][0]}~{rows[-1][0]}", flush=True)
    print(f"끝 · 저장 {ok} · 실패 {fail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
