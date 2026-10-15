"""MPOS-0013 해부(판정 없음 · 진단): 갈래별 달 손익(바탕 NAV 대비 %) · 1일봉 매매별 달 손익(달 끝 − 달 초 평가 + 흐름)을 계좌 달 손익에 합계 대조.
사례: REPRO_G 계좌 손실 달 40 · 이익 달 74 · MPOS-0012 가운데에서 이익→손실 6달 · 손실→이익 2달(REPRO_G vs F_SIDEDOWN_G).
매매 '나중 결과'(판 날 손익 부호)는 진단 묶음에만 씀 — 규칙에 쓰지 않음."""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/mpos13")   # 계산 폴더
M12 = HERE.parent / "r8/research-exchange/claude-to-gpt/MPOS-0012"
sys.path.insert(0, str(M12))
import mpos12 as M  # noqa: E402

LANES = ("1d", "basket", "engine", "inverse", "park")
raw = json.load(open(M.RAW))
diag = json.load(open(M12 / "diag12.json"))["매매"]


def months_of(ds):
    return sorted({d[:6] for d in ds})


def load(c):
    base = {r["날"]: float(r["NAV"]) for r in csv.DictReader(open(HERE / f"base_{c}.csv"))}
    attr = list(csv.DictReader(open(HERE / f"attr_{c}.csv")))
    tr = json.load(open(HERE / f"trade_{c}.json"))
    led = json.load(open(M.WORK / f"led_{c}.json"))
    # 걸러낸 장부 줄 → 원 장부 줄(같은 줄 내용 차례대로)
    pool = defaultdict(list)
    for i, r in enumerate(raw):
        pool[json.dumps(r)].append(i)
    to_raw = [pool[json.dumps(r)].pop(0) for r in led]
    acc = M.mstats(M.account(HERE / f"base_{c}.csv"))["달"]
    return base, attr, tr, to_raw, acc


def decompose(c):
    base, attr, tr, to_raw, acc = load(c)
    ds = sorted(base)
    mend = {}
    for d in ds:
        mend[d[:6]] = d
    ms = [m for m in months_of(ds) if "201703" <= m <= "202608"]
    allm = months_of(ds)
    lane_m = defaultdict(lambda: defaultdict(float))
    for r in attr:
        for k in LANES:
            lane_m[r["날"][:6]][k] += float(r[k])
    out = {}
    for m in ms:
        pm = allm[allm.index(m) - 1]
        n0, n1 = base[mend[pm]], base[mend[m]]
        v0, v1 = tr["값"].get(mend[pm], {}), tr["값"].get(mend[m], {})
        keys = set(v0) | set(v1) | {k.split("|")[0] for k in tr["흐름"] if k.endswith("|" + m)}
        per = {}
        for k in keys:
            per[k] = v1.get(k, 0.0) - v0.get(k, 0.0) + tr["흐름"].get(f"{k}|{m}", 0.0)
        s1d = sum(per.values())
        assert abs(s1d - lane_m[m]["1d"]) < 1e-6 * n0 + 1, (c, m, s1d, lane_m[m]["1d"])
        assert abs(sum(lane_m[m].values()) - (n1 - n0)) < 1e-6 * n0 + 1, (c, m)
        rows = []
        for k, v in per.items():
            ri = to_raw[int(k)]
            cc, b, e, p, s = raw[ri]
            rows.append(dict(raw=ri, pnl=v / n0 * 100, new=b[:6] == m, closed=e[:6] == m, win=p > 0, door=diag[ri]["door"], reg=diag[ri]["reg"], code=cc))
        out[m] = dict(acc=acc[m] * 100, base=(n1 / n0 - 1) * 100, lanes={k: lane_m[m][k] / n0 * 100 for k in LANES}, trades=rows,
                      n_hold_end=len(v1), d1_end_share=sum(v1.values()) / n1 * 100)
    return out


def group(rows, key):
    g = defaultdict(float)
    for r in rows:
        g[key(r)] += r["pnl"]
    return dict(g)


def summ(D, months):
    n = len(months)
    if not n:
        return {}
    avg = lambda f: round(sum(f(D[m]) for m in months) / n, 3)
    t = lambda m: D[m]["trades"]
    return {"달 수": n, "계좌 달 %": avg(lambda x: x["acc"]), "바탕 달 %": avg(lambda x: x["base"]),
            **{f"갈래 {k} %p": avg(lambda x, k=k: x["lanes"][k]) for k in LANES},
            "1일봉: 이번 달 새로 산 매매 %p": avg(lambda x: sum(r["pnl"] for r in x["trades"] if r["new"])),
            "1일봉: 전달부터 들고 온 매매 %p": avg(lambda x: sum(r["pnl"] for r in x["trades"] if not r["new"])),
            "1일봉: 그달 안 판 매매 %p": avg(lambda x: sum(r["pnl"] for r in x["trades"] if r["closed"])),
            "1일봉: 달 끝에 들고 있는 매매 %p": avg(lambda x: sum(r["pnl"] for r in x["trades"] if not r["closed"])),
            "1일봉: 나중에 이익으로 끝난 매매 %p(진단)": avg(lambda x: sum(r["pnl"] for r in x["trades"] if r["win"])),
            "1일봉: 나중에 손실로 끝난 매매 %p(진단)": avg(lambda x: sum(r["pnl"] for r in x["trades"] if not r["win"])),
            "1일봉: 규칙 문 %p": avg(lambda x: sum(r["pnl"] for r in x["trades"] if r["door"] == "규칙")),
            "1일봉: 정배열 문 %p": avg(lambda x: sum(r["pnl"] for r in x["trades"] if r["door"] == "정배열")),
            "1일봉 매매 수(그달 손익 있음)": avg(lambda x: len(x["trades"])),
            "그달 새로 산 1일봉 수": avg(lambda x: sum(r["new"] for r in x["trades"])),
            "달 끝 1일봉 보유 수": avg(lambda x: x["n_hold_end"]),
            "달 끝 1일봉 몫 %": avg(lambda x: x["d1_end_share"]),
            "1일봉 몫 손익이 계좌 달 손익보다 나쁜 달 비율(이 묶음)": round(sum(D[m]["lanes"]["1d"] < 0 for m in months) / n * 100, 1)}


def main():
    G = decompose("REPRO_G")
    S = decompose("F_SIDEDOWN_G")
    loss = [m for m in G if G[m]["acc"] < 0]
    prof = [m for m in G if G[m]["acc"] > 0]
    lost = [m for m in G if G[m]["acc"] > 0 and S[m]["acc"] < 0]
    rec = [m for m in G if G[m]["acc"] < 0 and S[m]["acc"] > 0]
    assert len(loss) == 40 and len(lost) == 6 and len(rec) == 2, (len(loss), len(lost), len(rec))
    rep = {"손실 달(REPRO_G 40)": summ(G, loss), "이익 달(REPRO_G 74)": summ(G, prof)}
    # 손실 달 1일봉 몫: 새로 산 매매가 1일봉 손실의 얼마를 내나 · 1일봉 갈래가 음수인 손실 달 수
    rep["손실 달 중 1일봉 갈래가 음수"] = sum(G[m]["lanes"]["1d"] < 0 for m in loss)
    rep["손실 달 중 1일봉을 0으로 두면 이익이 되는 달(덧붙임 효과 무시 · 바탕 기준)"] = sum(G[m]["base"] < 0 and G[m]["base"] - G[m]["lanes"]["1d"] > 0 for m in loss)
    # 대조 사례: 6달 · 2달 — 갈래별 차이(가운데 − 기준) · 1일봉 차이를 '뺀 매매' · '남은 매매'로
    def diff(ms):
        res = {}
        for m in ms:
            kept = {r["raw"]: r["pnl"] for r in S[m]["trades"]}
            gone = sum(r["pnl"] for r in G[m]["trades"] if r["raw"] not in kept)
            same = sum(kept.values()) - sum(r["pnl"] for r in G[m]["trades"] if r["raw"] in kept)
            res[m] = {"계좌 기준 → 가운데 %": [round(G[m]["acc"], 2), round(S[m]["acc"], 2)],
                      "바탕 기준 → 가운데 %": [round(G[m]["base"], 2), round(S[m]["base"], 2)],
                      **{f"Δ{k} %p": round(S[m]["lanes"][k] - G[m]["lanes"][k], 2) for k in LANES},
                      "Δ1일봉 중 뺀 매매가 기준에서 낸 손익(−) %p": round(-gone, 2), "Δ1일봉 중 남은 매매 크기 차 %p": round(same, 2)}
        return res
    rep["이익→손실 6달"] = diff(lost)
    rep["손실→이익 2달"] = diff(rec)
    rep["손실 달 목록"] = {m: {"계좌 %": round(G[m]["acc"], 2), "바탕 %": round(G[m]["base"], 2), **{k: round(G[m]["lanes"][k], 2) for k in LANES},
                            "1일봉 새로 산 %p": round(sum(r["pnl"] for r in G[m]["trades"] if r["new"]), 2),
                            "1일봉 들고 온 %p": round(sum(r["pnl"] for r in G[m]["trades"] if not r["new"]), 2)} for m in loss}
    json.dump(rep, open(HERE / "diag13.json", "w"), ensure_ascii=False, indent=1)
    for k, v in rep.items():
        if k != "손실 달 목록":
            print(k, json.dumps(v, ensure_ascii=False))


if __name__ == "__main__":
    main()
