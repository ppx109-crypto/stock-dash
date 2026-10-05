"""m15-kis에서 한 날짜의 15분봉만 빼고(먼저 따로 보관), 정기 수집(kis-m15)이 그날을 다시 받게 함(사용자 2026-10-05 "1" · "권한 설정해줘").

까닭: 2026-10-02 15분봉의 마지막 칸이 장 마감 단일가(15:30)를 빠뜨려, 424종목 중 356종목 종가가 일봉과 달랐음
(9-29 ~ 10-01은 1~2종목만 다름 · 한투 일봉 · 코스닥 자료 · 수급 자료 세 곳의 종가는 서로 같음).
수집기는 '받은 날은 건너뛰고 빈 날만 묻기' 때문에 그날 줄을 빼면 다음 수집 때 다시 받음.
보관: research/m15_drop_backup_{날}.txt ("파일경로:줄" 그대로 · 되돌릴 때 씀). 그날이 '봉 없음'으로 적힌 empty.txt는 건드리지 않음.
python research/drop_m15_day.py YYYYMMDD
"""
import sys
from pathlib import Path

HOME = Path("m15-kis")


def main(day):
    if len(day) != 8 or not day.isdigit():
        sys.exit("날짜는 YYYYMMDD")
    backup = Path(f"research/m15_drop_backup_{day}.txt")
    kept, files = [], 0
    for f in sorted(HOME.glob("*/*.csv")):
        lines = f.read_text(encoding="utf-8").split("\n")
        mine = [x for x in lines if x.startswith(day)]
        if not mine:
            continue
        kept += [f"{f}:{x}" for x in mine]
        f.write_text("\n".join(x for x in lines if not x.startswith(day)), encoding="utf-8")
        files += 1
    if kept:
        backup.write_text("\n".join(kept) + "\n", encoding="utf-8")
    print(f"{day}: {files}종목에서 {len(kept)}줄을 빼고 {backup}에 보관")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
