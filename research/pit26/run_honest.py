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
    out = {"모드": MODE, "실측": H["실측"], "inside 행 지문": rows_sha(H["inside"]), "달 문턱 수": len(H["T"]),
           "달 문턱 없음(k < 1000) 달": [m for m, v in H["T"].items() if v is None][:5],
           "가격 파일 지문 묶음": hashlib.sha256(json.dumps(man, sort_keys=True).encode()).hexdigest(), "가격 종목 수": len(man)}
    json.dump(man, open(OUT + ".prices.json", "w"), ensure_ascii=False, indent=0)
elif MODE == "CUT":
    c = os.environ["EX_CUT"]
    full = pickle.load(open(os.environ["EX_FULL"], "rb"))
    H = ns["build_honest"](P, c, TMP)
    d_rows = ns["rows_diff_strict"](H["inside"], full["inside"], upto=c)
    T_diff = [m for m in H["T"] if m <= c[:6] and H["T"][m] != full["T"].get(m)]
    BR_diff = [d for d in H["BR"] if d <= c and H["BR"][d] != full["BR"].get(d)]
    sh_diff = 0
    for code, one in H["shape"].items():
        if code not in full["shape"]:
            sh_diff += 1
            continue
        n = len(one["정배열"])
        for key in ("정배열", "간격", "50>200"):
            a, b = np.asarray(one[key][:n], dtype=float), np.asarray(full["shape"][code][key][:n], dtype=float)
            if not np.array_equal(np.nan_to_num(a, nan=-7.7), np.nan_to_num(b, nan=-7.7)):
                sh_diff += 1
                break
    tl_c, tl_f = ns["trend_leg_with"](H["T"]), ns["trend_leg_with"](full["T"])
    g_diff = {}
    for k in sorted(set(H["inside"]) & {x for x in full["inside"] if x[1] <= c}):
        gc = ns["gates"](H["inside"][k], tl_c, H["shape"], H["BR"])
        gf = ns["gates"](full["inside"][k], tl_f, full["shape"], full["BR"])
        for g in gc:
            if gc[g] != gf[g]:
                g_diff.setdefault(g, []).append(k)
    ok = d_rows["같음"] and not T_diff and not BR_diff and sh_diff == 0 and not g_diff
    out = {"모드": MODE, "자르는 날": c, "실측": H["실측"], "행 · 칸(c까지 inside)": d_rows, "달 문턱 다른 달": T_diff,
           "BR 다른 날": len(BR_diff), "shape 다른 종목": sh_diff, "문 다름": {g: len(v) for g, v in g_diff.items()},
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
    out = {"모드": MODE, "inside 행(SINCE ~) 정직 · 옛 · 정직만 · 옛만": [len(Hn), len(On), len(set(Hn) - set(On)), len(set(On) - set(Hn))],
           "같은 행에서 문 다름(정직: 달 문턱 · 정직 shape/BR · 옛: 전체 문턱 G · 캐시 shape/BR)": gd,
           "칸 대조(같은 행)": ns["rows_diff_strict"](Hn, On),
           "엔진 진입 정직 · 원판 · 정직만 · 원판만 · 같음": [len(ents), len(eb), len(ents - eb), len(eb - ents), len(ents & eb)]}
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str)[:4000])
