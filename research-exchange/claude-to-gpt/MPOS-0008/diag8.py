"""MPOS-0008 진단 다시 셈(GPT #420 §2) — MPOS-0007 표를 코드로 다시: 달력 114달(2017-03 ~ 2026-08) 분모 · 원정밀도 +/0/− ·
바탕(d0.5_b0.3 · 덧붙임 없음) · KODEX 200 · 잔차 진단(바탕 − β60 × KODEX 200 · β는 그날 전 60일만 · 비용 없음 · 실행 불가 = 원인 증거 아님) ·
1일봉 장부 거래 수(판 날 기준 · 114달 분모와 거래 있는 달 분모 따로). 고르기 · 판정 없음.
python3 diag8.py <바탕 csv> <z055 장부> <069500.json>"""
import csv
import json
import statistics as S
import sys


def months(navs):
    ds = sorted(navs)
    mo = {}
    for j in range(1, len(ds)):
        m = ds[j][:6]
        mo[m] = mo.get(m, 1.0) * (navs[ds[j]] / navs[ds[j - 1]])
    return {m: v - 1 for m, v in mo.items()}


def cnt(full):
    return dict(달=len(full), 이익=sum(v > 0 for v in full.values()), 영=sum(v == 0 for v in full.values()), 손실=sum(v < 0 for v in full.values()),
                최악달=round(min(full.values()) * 100, 4))


def main(base_csv, led_path, k200_path):
    base = {r["날"]: float(r["NAV"]) for r in csv.DictReader(open(base_csv, encoding="utf-8"))}
    k = {str(d): float(c) for d, c in json.load(open(k200_path))["closes"] if c}
    ds = sorted(d for d in base if d in k)
    MON = [m for m in sorted({d[:6] for d in ds}) if "201703" <= m <= "202608"]
    out = {"달 목록": [MON[0], MON[-1], len(MON)], "바탕 날 중 KODEX 값 없는 날": sorted(d for d in base if d not in k)}
    b = months({d: base[d] for d in ds})
    kk = months({d: k[d] for d in ds})
    rb = {ds[j]: base[ds[j]] / base[ds[j - 1]] - 1 for j in range(1, len(ds))}
    rk = {ds[j]: k[ds[j]] / k[ds[j - 1]] - 1 for j in range(1, len(ds))}
    h, nav, beta_days = {}, 1.0, 0
    rd = sorted(rb)
    h[rd[0]] = nav
    for j, d in enumerate(rd):
        if j >= 60:
            xs, ys = [rk[x] for x in rd[j - 60:j]], [rb[x] for x in rd[j - 60:j]]
            mx, my = S.mean(xs), S.mean(ys)
            vx = sum((x - mx) ** 2 for x in xs)
            beta = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / vx if vx > 0 else 0.0
            beta_days += 1
        else:
            beta = 0.0
        nav *= 1 + rb[d] - beta * rk[d]
        h[d] = nav
    hh = months(h)
    for nm, mo in (("바탕(덧붙임 없음)", b), ("잔차 진단(β60 · 비용 없음 · 실행 불가)", hh), ("KODEX 200", kk)):
        out[nm] = cnt({m: mo[m] for m in MON})
    out["잔차 진단 β 쓴 날"] = beta_days
    led = json.load(open(led_path))
    by = {}
    for c, bd, e, p, s in led:
        by.setdefault(e[:6], []).append(p)
    n = [len(by.get(m, [])) for m in MON]
    tm = [m for m in MON if by.get(m)]
    allp = [p for m in MON for p in by.get(m, [])]
    out["1일봉 장부(판 날 기준)"] = dict(거래=len(allp), 거래있는달=len(tm), 무거래달=len(MON) - len(tm),
                                    달평균_114분모=round(len(allp) / len(MON), 2), 달평균_거래달분모=round(len(allp) / len(tm), 2),
                                    중앙_거래달=S.median(len(by[m]) for m in tm), 최소_거래달=min(len(by[m]) for m in tm),
                                    승률=round(sum(p > 0 for p in allp) / len(allp) * 100, 2), 평균=round(S.mean(allp), 3),
                                    PF=round(sum(p for p in allp if p > 0) / -sum(p for p in allp if p < 0), 3))
    out["무거래 달 계좌 처리"] = "바탕 계좌는 날마다 평가(MTM) · 무거래 달도 114달 분모에 남음(보유 평가손익 · 다른 봇 · 현금 포함)"
    return out


if __name__ == "__main__":
    print(json.dumps(main(*sys.argv[1:4]), ensure_ascii=False, indent=1))
