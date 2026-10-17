"""정직 캐시 실행(HONEST_CACHE.md 판 2 · 손익 없음). honest_cache.py 원문을 exec(tree_run은 나무 밖 import를 막음).
EX_MODE=FULL : 고정 나무 가격판 전체로 정직 캐시 → EX_OUT.pkl + EX_OUT(요약 json).
EX_MODE=CUT  : EX_CUT까지 가격으로 다시 만들고 EX_FULL(.pkl)의 c까지와 대조 — 행 · 칸 · 칸 이름 · 타입 · 달 문턱 · 순위 · BR · shape · 문 · 거절 이유.
EX_MODE=OLD  : EX_FULL 정직 캐시 대 지금 옛 캐시(nrl) — inside 행 · 문(옛: 전체 문턱 G · 캐시 shape/BR) 건수 차이 + 엔진 진입(종목 · 산 날) 건수만.
cwd = 고정 나무 · tree_run. 손익 · 수익률 출력 없음."""
import hashlib
import json
import os
import pickle
import sys

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "research"))
HC = os.environ["EX_HC"]
ns = {"__name__": "honest_cache", "__file__": HC}
exec(compile(open(HC, encoding="utf-8").read(), HC, "exec"), ns)
import numpy as np  # noqa: E402
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402
import study  # noqa: E402

MODE, OUT = os.environ["EX_MODE"], os.environ["EX_OUT"]
TMP = os.environ.get("EX_TMP", OUT + ".tmp")
P = study.load_prices()


def rows_sha(inside):
    h = hashlib.sha256()
    for k in sorted(inside):
        h.update(json.dumps(inside[k], sort_keys=True, ensure_ascii=False, default=str).encode())
    return h.hexdigest()


def price_manifest():
    return {c: hashlib.sha256(json.dumps(P[c]["rows"]).encode()).hexdigest() for c in sorted(P)}


if MODE == "FULL":
    H = ns["build_honest"](P, "99999999", TMP)
    keep = {k: H[k] for k in ("inside", "T", "BR", "first_day", "shape")}
    pickle.dump(keep, open(OUT + ".pkl", "wb"), protocol=pickle.HIGHEST_PROTOCOL)
    man = price_manifest()
    out = {"모드": MODE, "실측": H["실측"], "inside 행 지문": rows_sha(H["inside"]),
           "가격 지문 뜻": "원파일 바이트가 아니라 study.load_prices로 읽은 rows의 JSON 직렬화 SHA256", "달 문턱 수": len(H["T"]),
           "달 문턱 없음(k < 1000) 달": [m for m, v in H["T"].items() if v is None][:5],
           "가격 rows 직렬화 지문 묶음": hashlib.sha256(json.dumps(man, sort_keys=True).encode()).hexdigest(), "가격 종목 수": len(man)}
    json.dump(man, open(OUT + ".prices.json", "w"), ensure_ascii=False, indent=0)
elif MODE == "CUT":
    c = os.environ["EX_CUT"]
    full = pickle.load(open(os.environ["EX_FULL"], "rb"))
    H = ns["build_honest"](P, c, TMP)
    d_rows = ns["rows_diff_strict"](H["inside"], full["inside"], upto=c)
    # 양쪽 키 집합을 먼저(GPT #457 4차 ②): 달 문턱은 c가 든 달까지 · BR은 c까지 날 · shape는 c까지 inside에 나온 종목 · 길이는 자른 가격 길이
    T_d = ns["keyed_diff"](H["T"], full["T"], upto=c[:6])
    BR_d = ns["keyed_diff"](H["BR"], full["BR"], upto=c)
    codes_c = {k[0] for k in full["inside"] if k[1] <= c}
    sh_d = ns["shape_diff"](H["shape"], {k: v for k, v in full["shape"].items() if k in codes_c},
                            {code: len([1 for d, _ in P[code]["rows"] if d <= c]) for code in codes_c | set(H["shape"])})
    tl_c, tl_f = ns["trend_leg_with"](H["T"]), ns["trend_leg_with"](full["T"])
    g_diff = {}
    for k in sorted(set(H["inside"]) & {x for x in full["inside"] if x[1] <= c}):
        gc = ns["gates"](H["inside"][k], tl_c, H["shape"], H["BR"])
        gf = ns["gates"](full["inside"][k], tl_f, full["shape"], full["BR"])
        for g in gc:
            if gc[g] != gf[g]:
                g_diff.setdefault(g, []).append(k)
    ok = d_rows["같음"] and T_d["같음"] and BR_d["같음"] and sh_d["같음"] and not g_diff
    out = {"모드": MODE, "자르는 날": c, "실측": H["실측"], "행 · 칸(c까지 inside)": d_rows, "달 문턱(양쪽 키)": T_d,
           "BR(양쪽 키)": BR_d, "shape(양쪽 종목 · 길이)": sh_d, "문 다름": {g: len(v) for g, v in g_diff.items()},
           "문 다름 예": {g: v[:5] for g, v in g_diff.items()},
           "판정": "동일 가격판 후보 재생 · 내부 시간 절단 PASS" if ok else "동일 가격판 후보 재생 · 내부 시간 절단 FAIL"}
elif MODE == "OLD":
    full = pickle.load(open(os.environ["EX_FULL"], "rb"))
    since = rule.SINCE
    Hn = {k: v for k, v in full["inside"].items() if k[1] >= since}
    On = {(r["code"], r["date"]): r for r in nrl.inside if r["date"] >= since}
    tl_h = ns["trend_leg_with"](full["T"])
    gd, both = {}, set(Hn) & set(On)
    reason = {}
    for k in sorted(both):
        gh = ns["gates"](Hn[k], tl_h, full["shape"], full["BR"])
        go = ns["gates"](On[k], rule.trend_leg, nrl.shape, nrl.BR)
        for g in gh:
            if gh[g] != go[g]:
                gd[g] = gd.get(g, 0) + 1
    # 엔진 진입(종목 · 산 날) 건수만 — 정직 캐시 · 같은 가격판 · 정직 shape/BR/달 문턱
    rule.trend_leg = tl_h
    nrl.shape, nrl.BR = full["shape"], full["BR"]
    kin = rule.apart(P)
    inside_l = sorted(Hn.values(), key=lambda r: (r["date"], r["code"]))
    assert all("i" in r for r in inside_l)
    early = [r for r in inside_l if r["date"] < rule.MID]
    ents = set()
    for side, pool, s in (("앞", early, rule.SINCE), ("뒤", inside_l, rule.MID)):
        g = lab.run(pool, P, nrl.BASE_HOLD, nrl.BASE_EXIT, slots=nrl.SLOTS, rank=rule.order, since=s, apart=kin, realistic=True, cap=130,
                    detail=True, size=nrl.BASE_SIZE)
        ents |= {(t["code"], t["산 날"]) for t in g["매매목록"]}
    base = json.load(open(os.environ["EX_LEDGER"]))
    assert hashlib.sha256(json.dumps(base).encode()).hexdigest() == "0ec97a14ba3d9b81168906eb332c6753d576ff57601e526c935345aafac75c99"
    eb = {(x[0], x[1]) for x in base}
    old_last = max(k[1] for k in On)
    from collections import Counter
    onlyH, onlyO = sorted(set(Hn) - set(On)), sorted(set(On) - set(Hn))
    entsC, ebC = {e for e in ents if e[1] <= old_last}, {e for e in eb if e[1] <= old_last}
    out = {"모드": MODE, "옛 표 마지막 날": old_last,
           "inside 행(SINCE ~) 정직 · 옛 · 정직만 · 옛만": [len(Hn), len(On), len(onlyH), len(onlyO)],
           "정직만 행: 공통 구간 · 꼬리(옛 표 마지막 날 뒤)": [sum(1 for k in onlyH if k[1] <= old_last), sum(1 for k in onlyH if k[1] > old_last)],
           "정직만 행 공통 구간 목록(종목 · 날 · 앞 30)": [k for k in onlyH if k[1] <= old_last][:30],
           "정직만 행 공통 구간 종목별 수": dict(Counter(k[0] for k in onlyH if k[1] <= old_last).most_common(20)),
           "옛만 행 목록": onlyO,
           "장부에 기록된 매매의 서로 다른 진입 키(종목 · 산 날) 공통 구간 정직 · 원판 · 정직만 · 원판만 · 같음": [len(entsC), len(ebC), len(entsC - ebC), len(ebC - entsC), len(entsC & ebC)],
           "같은 키 꼬리(옛 표 마지막 날 뒤) 정직 · 원판": [len(ents - entsC), len(eb - ebC)],
           "정직만 · 원판만 키(공통 구간)": [sorted(entsC - ebC), sorted(ebC - entsC)],
           "범위": "lab.run 매매목록(청산 · 정산 때 적힘 · settle_end=False라 열린 보유는 빠질 수 있음)의 서로 다른 (종목, 산 날) · 엔진 안에서는 손익을 계산하지만 성과 요약은 출력하지도 선택 기준으로 쓰지도 않음",
           "같은 행에서 문 다름(정직: 달 문턱 · 정직 shape/BR · 옛: 전체 문턱 G · 캐시 shape/BR)": gd,
           "칸 대조(같은 행)": ns["rows_diff_strict"](Hn, On),
           "(전체 기간) 진입 키 정직 · 원판 · 정직만 · 원판만 · 같음": [len(ents), len(eb), len(ents - eb), len(eb - ents), len(ents & eb)]}
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str)[:4000])
