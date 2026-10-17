"""H-USD 2단계(GPT #454): 달러선물 · 단기채 ETF 종가가 분배금을 반영하는지 확인(성과 안 봄).
입력(git show로 읽음 · 지문 기록):
- 원주가 · 수정주가 · 분배 일정: etf-ohlc/{코드}.json @ OHLC(collect_etf_ohlc.py · 한투 FHKST03010100 ADJ 0/1 · HHKDB669102C0 예탁원 배당일정)
- 탐색에 쓴 종가: etf-data/{코드}.json @ 고정 나무 9743cb802
대조(069500은 분배가 있는 양성 대조):
① 수정 ÷ 원주가 비율이 바뀐 날(계단)과 분배 기준일 전 거래일(분배락)이 맞는지 · 계단 크기 ≈ 분배금 ÷ 전날 원주가
② 탐색 종가의 하루 수익 = 지금 수정 종가의 하루 수익인지(수정주가는 새 분배가 날 때마다 앞 값 전체에 같은 배수가 곱해져 값 자체는 달라질 수 있음 · 수익은 같아야 함)
③ 하루만 튀었다 돌아온 값(±1.5% 넘게 갔다가 다음 날 되돌림 · 단기채는 ±0.15%)과 그 날이 달 마지막 거래일인지(달 수익을 흔드는지)
출력: dist_check_out.json"""
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OHLC, TREE = "51826765c", "9743cb802"
CODES = ("069500", "261240", "138230", "153130", "157450")
BOND = {"153130", "157450"}


def show(rev, path):
    raw = subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True, check=True).stdout
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


out, fps = {}, {}
for c in CODES:
    o, fps[f"{OHLC}:etf-ohlc/{c}.json"] = show(OHLC if c != "069500" else "HEAD", f"etf-ohlc/{c}.json")
    e, fps[f"{TREE}:etf-data/{c}.json"] = show(TREE, f"etf-data/{c}.json")
    adj = {r[0]: r[4] for r in o["adjusted"] if r[4]}
    raw = {r[0]: r[4] for r in o["raw"] if r[4]}
    ks = sorted(set(adj) & set(raw))
    steps, prev = [], None
    for i, k in enumerate(ks):
        q = raw[k] / adj[k]
        if prev is not None and abs(q / prev - 1) > 3e-4:   # 그보다 작은 건 원 단위 반올림
            steps.append({"날": k, "비율 변화": round(q / prev - 1, 5), "전날 원주가": raw[ks[i - 1]]})
        prev = q
    divs = []
    for v in o["dividends"]:
        rd = v["record_date"]
        before = [k for k in ks if k < rd]
        ex = before[-1] if before else None
        st = next((s for s in steps if s["날"] == ex), None)
        exp = -v["per_share_cash"] / st["전날 원주가"] if st else None
        divs.append({"기준일": rd, "분배락(전 거래일)": ex, "주당": v["per_share_cash"], "계단": st["비율 변화"] if st else None,
                     "기대 계단(−분배 ÷ 전날 원주가)": round(exp, 5) if exp is not None else None})
    matched = {d["분배락(전 거래일)"] for d in divs if d["계단"] is not None}
    ed = dict(e["closes"])
    common = [k for k in ks if k in ed]
    same = sum(1 for k in common if abs(ed[k] - adj[k]) < 0.5)
    rd = []   # 같은 날 짝 하루 수익 차이(탐색 종가 대 지금 수정 종가)
    for a, b in zip(common, common[1:]):
        rd.append((b, abs((ed[b] / ed[a]) - (adj[b] / adj[a]))))
    big = [(d, round(x * 100, 4)) for d, x in rd if x > 5e-4]
    ratio = [ed[k] / adj[k] for k in common]
    # ③ 하루 튐
    cl = e["closes"]
    lim = 0.0015 if c in BOND else 0.015
    month_last = {}
    for d, _ in cl:
        month_last[d[:6]] = d
    spikes = []
    for i in range(1, len(cl) - 1):
        a = cl[i][1] / cl[i - 1][1] - 1
        b = cl[i + 1][1] / cl[i][1] - 1
        if abs(a) > lim and abs(b) > lim and a * b < 0 and abs(cl[i + 1][1] / cl[i - 1][1] - 1) < lim / 3:
            spikes.append({"날": cl[i][0], "그날 %": round(a * 100, 3), "다음 날 %": round(b * 100, 3), "달 마지막 거래일": month_last[cl[i][0][:6]] == cl[i][0]})
    out[c] = {"분배 건수": len(divs), "분배": divs, "비율 계단 수": len(steps), "분배와 안 맞는 계단": [s for s in steps if s["날"] not in matched][:20],
              "탐색 종가 = 수정 종가(값)": f"{same}/{len(common)}", "값 배수(탐색 ÷ 지금) 최소 · 최대": [round(min(ratio), 6), round(max(ratio), 6)],
              "하루 수익 차이 > 0.05%p 날": big[:20], "하루 수익 차이 최대 %p": round(max(x for _, x in rd) * 100, 4), "하루 튐": spikes,
              "원주가 첫날 · 끝날": [ks[0], ks[-1]] if ks else None}
out["입력 지문"] = fps
json.dump(out, open(HERE / "dist_check_out.json", "w"), ensure_ascii=False, indent=1)
for c in CODES:
    r = out[c]
    print(c, "분배", r["분배 건수"], "계단", r["비율 계단 수"], "안 맞는 계단", len(r["분배와 안 맞는 계단"]), "값 같음", r["탐색 종가 = 수정 종가(값)"], "배수", r["값 배수(탐색 ÷ 지금) 최소 · 최대"], "수익 차이 큰 날", r["하루 수익 차이 > 0.05%p 날"], "최대", r["하루 수익 차이 최대 %p"], "튐", [(s["날"], s["달 마지막 거래일"]) for s in r["하루 튐"]])
    for d in r["분배"][-4:]:
        print("   ", d)
