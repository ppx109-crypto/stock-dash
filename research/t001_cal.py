"""TOM-0028 거래일 달력 만들기(가격 파일과 따로) — round 3(GPT #160 6091438066).
규칙: 평일 − 한국 공휴일(holidays 0.57 KR · 휠 sha256 bdfb2a6d…ea82d) − 근로자의 날(5월 1일) − 그해 12월 마지막 평일(거래소 연말 휴장)
     − 공지 휴장(아래 NOTICES · 패키지 0.57이 나온 뒤 정해진 날).
가격 파일(etf-data)을 읽지 않음. 결과: research-exchange/claude-to-gpt/TOM-0028/calendar.json
python3 research/t001_cal.py <holidays 0.57이 설치된 폴더>"""
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import holidays  # noqa: E402

assert holidays.__version__ == "0.57"
NOTICES = {"20250127": "임시공휴일(설 연휴 사이 · 2025년 1월 정부 지정 · 발표일 문서로 확인 못 함)",
           "20250603": "제21대 대통령 선거일(법정 공휴일 · 확정 공고일 문서로 확인 못 함)"}
START, END = dt.date(2002, 10, 14), dt.date(2026, 12, 31)


def main():
    kr = holidays.KR(years=range(START.year, END.year + 1))
    last_wd = {}
    for y in range(START.year, END.year + 1):
        d = dt.date(y, 12, 31)
        while d.weekday() >= 5:
            d -= dt.timedelta(1)
        last_wd[y] = d
    days, d = [], START
    while d <= END:
        s = d.strftime("%Y%m%d")
        if d.weekday() < 5 and d not in kr and not (d.month == 5 and d.day == 1) and d != last_wd[d.year] and s not in NOTICES:
            days.append(s)
        d += dt.timedelta(1)
    out = {"rule": "평일 − holidays 0.57 KR − 5월 1일 − 12월 마지막 평일 − NOTICES", "holidays_version": holidays.__version__,
           "holidays_wheel_sha256": "bdfb2a6d58e4b7d819e049b469228e890a5ad42b8ea2bd2c150d8c10726ea82d", "notices": NOTICES,
           "first": days[0], "last": days[-1], "days": days}
    p = Path(__file__).resolve().parent.parent / "research-exchange/claude-to-gpt/TOM-0028/calendar.json"
    p.write_text(json.dumps(out, ensure_ascii=False))
    print(len(days), days[0], days[-1])


if __name__ == "__main__":
    main()
