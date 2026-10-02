"""DART에서 규칙 재료로 더 쓸 만한 것이 있는지 찔러 봅니다(조회 전용, 저장하지 않음 · 사용자 요청 2026-10-02).

찍는 것: 공시 갈래별 건수(제목만 · 공개 정보) · 각 API가 주는 줄 수 · 칸 이름 · 가장 옛날과 최근 날짜 · 계정 이름.
값(금액 · 지분율 등)과 키는 찍지 않습니다.
"""
import os
import re
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from providers import DataError, Official

CODES = ["005930", "000660", "035420", "005380", "051910", "068270", "247540", "196170", "086520", "028300"]
TYPES = {"A": "정기공시", "B": "주요사항보고", "C": "발행공시", "D": "지분공시", "E": "기타공시",
         "F": "외부감사관련", "I": "거래소공시", "J": "공정위공시"}


def norm(title):
    t = re.sub(r"\s+", "", str(title or ""))
    t = re.sub(r"^\[[^\]]*\]", "", t)                 # [기재정정] 등
    t = re.sub(r"\((자회사의주요경영사항|안내공시|공정공시|자율공시|종속회사의주요경영사항)\)", "", t)
    t = re.sub(r"\(\d{4}\.\d{2}\)", "", t)             # (2024.03) 같은 기간
    t = re.sub(r"제\d+기", "", t)
    return t[:40]


def ask(o, ep, **kw):
    time.sleep(0.12)
    try:
        return o.dart(ep, **kw)
    except DataError as e:
        return {"_err": str(e)[:60]}


def span(rows, key="rcept_no"):
    days = sorted(str(r.get(key, ""))[:8] for r in rows if str(r.get(key, ""))[:8].isdigit())
    return f"{days[0]}~{days[-1]}" if days else "-"


def main():
    o = Official()
    o.corp("005930")
    corp = {c: o.corps.get(c) for c in CODES}
    print("== 1. 공시 종류별 건수(2017-01 ~ 2026-09, 종목 10개 합) ==", flush=True)
    for ty, nm in TYPES.items():
        n = 0
        for c in CODES[:5]:
            p = ask(o, "list.json", corp_code=corp[c], bgn_de="20170101", end_de="20260930", pblntf_ty=ty, page_count=1)
            n += int((p or {}).get("total_count") or 0)
        print(f"  {ty} {nm}: 큰 종목 5개 합 {n}건", flush=True)
    print("\n== 2. 제목 갈래 전부(종목 10개 · 2017~ · 정기공시 빼고) ==", flush=True)
    titles, first = Counter(), {}
    for c in CODES:
        for year in range(2017, 2027):
            page = 1
            while True:
                p = ask(o, "list.json", corp_code=corp[c], bgn_de=f"{year}0101", end_de=f"{year}1231", page_no=page, page_count=100)
                rows = (p or {}).get("list") or []
                for r in rows:
                    t = norm(r.get("report_nm"))
                    if not t or t.startswith(("분기보고서", "반기보고서", "사업보고서")):
                        continue
                    titles[t] += 1
                    first[t] = min(first.get(t, "9999"), str(r.get("rcept_dt", ""))[:4])
                if page >= int((p or {}).get("total_page") or 1) or not rows:
                    break
                page += 1
    print(f"  갈래 {len(titles)}개 · 모두 {sum(titles.values())}건", flush=True)
    for t, n in titles.most_common(90):
        print(f"  {n:5d} · {first[t]}~ · {t}", flush=True)
    print("\n== 3. 지분공시(대량보유 · 임원 소유) 몇 해치 주나 ==", flush=True)
    for ep in ("majorstock.json", "elestock.json"):
        for c in CODES[:4]:
            p = ask(o, ep, corp_code=corp[c])
            rows = (p or {}).get("list") or []
            cols = ", ".join(sorted(rows[0]))[:300] if rows else (p or {}).get("_err", "")
            print(f"  {ep} {c}: 줄 {len(rows)} · {span(rows)} · 칸: {cols}", flush=True)
    print("\n== 4. 전체 재무제표(fnlttSinglAcntAll) — 현금흐름 · 재고 · 매출채권 있나 ==", flush=True)
    for year, rc in (("2016", "11013"), ("2017", "11013"), ("2019", "11012"), ("2024", "11014")):
        for c in ("005930", "247540"):
            p = ask(o, "fnlttSinglAcntAll.json", corp_code=corp[c], bsns_year=year, reprt_code=rc, fs_div="CFS")
            rows = (p or {}).get("list") or []
            sj = Counter(r.get("sj_div") for r in rows)
            names = [r.get("account_nm", "") for r in rows]
            want = ["영업활동", "재고자산", "매출채권", "유형자산의취득", "연구개발", "배당금"]
            hit = {w: any(w in re.sub(r"\s", "", n) for n in names) for w in want}
            print(f"  {year}-{rc} {c}: 줄 {len(rows)} · 표 {dict(sj)} · " + " ".join(f"{w}{'○' if v else '×'}" for w, v in hit.items())
                  + (f" · {p.get('_err')}" if isinstance(p, dict) and p.get('_err') else ""), flush=True)
    print("\n== 5. 주요 재무지표(fnlttSinglIndx) 언제부터 ==", flush=True)
    for year, rc in (("2022", "11011"), ("2023", "11014"), ("2024", "11011"), ("2025", "11012")):
        for idx in ("M210000", "M220000", "M230000", "M240000"):
            p = ask(o, "fnlttSinglIndx.json", corp_code=corp["005930"], bsns_year=year, reprt_code=rc, idx_cl_code=idx)
            rows = (p or {}).get("list") or []
            print(f"  {year}-{rc} {idx}: 줄 {len(rows)} · 지표 {', '.join(r.get('idx_nm', '') for r in rows)[:200]}", flush=True)
    print("\n== 6. 사업보고서 주요정보(DS002) 2015 · 2017 · 2020 있나 ==", flush=True)
    for ep, nm in (("hyslrSttus.json", "최대주주"), ("mrhlSttus.json", "소액주주"), ("empSttus.json", "직원"),
                   ("alotMatter.json", "배당"), ("tesstkAcqsDspsSttus.json", "자기주식"), ("stockTotqySttus.json", "주식총수"),
                   ("otrCprInvstmntSttus.json", "타법인출자"), ("accnutAdtorNmNdAdtOpinion.json", "감사의견"),
                   ("cprndNrdmpBlce.json", "회사채 미상환"), ("pssrpCptalUseDtls.json", "공모자금 사용")):
        for year in ("2015", "2017", "2020"):
            for rc in ("11011", "11012"):
                p = ask(o, ep, corp_code=corp["000660"], bsns_year=year, reprt_code=rc)
                rows = (p or {}).get("list") or []
                cols = ", ".join(sorted(rows[0]))[:220] if rows else (p or {}).get("_err", "")
                print(f"  {nm} {year}-{rc}: 줄 {len(rows)} · {cols}", flush=True)
    print("\n== 7. 증권신고서(지분증권) ==", flush=True)
    for c in CODES:
        p = ask(o, "estkRs.json", corp_code=corp[c], bgn_de="20170101", end_de="20260930")
        groups = (p or {}).get("group") or []
        print(f"  {c}: 묶음 {len(groups)} · {(p or {}).get('_err', '')}", flush=True)
    print("끝", flush=True)


if __name__ == "__main__":
    if not os.environ.get("DART_CRTFC_KEY", "").strip():
        print("DART 키가 없습니다.")
        sys.exit(1)
    main()
