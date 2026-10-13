"""HDD-0001 round 3 — GPT #338 결함 2개 보완 재실행(같은 12판 · 같은 승격식 · 새 가설 없음).
잠근 kmf_nb.py 원문(해시 확인)에서 두 곳만 바꾼 사본을 kmf_nb 이름으로 올린 뒤 kmf_hdd_pre의 신호 · 판정 함수를 그대로 씁니다.
 결함 1(계약 사후 선택): kiwoom-data 선물 파일 구간(09-01 ~ 10-12)의 계약을 '그날 거래량 1위' 대신 장 전에 아는 달력 근월물
   (만기일 = 둘째 목요일 당일부터 다음 월물 · collect_fut_1min.front_code와 같은 규칙)로 고름. 그날 그 코드가 없으면 그날 뺌.
 결함 2(불완전 15분봉): 09:00 ~ 15:14 안에 분이 빠진 15분봉이 하나라도 있는 날은 그날 줄 전체를 뺌(fail-closed · EMA · ATR · 조용함 이력에도 안 넣음).
   뺀 날 목록 · 봉별 분 수는 출력에 남김.
python3 research/kmf_hdd_fc.py → research/kmf_hdd_fc_out.json · _daily.json"""
import sys, types, json, hashlib, collections
from datetime import date, timedelta
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
NB_SHA = "b34f3549fe9a93b951e104148605404737f0bab30faf2d6960296d59957b55de"
PRE_SHA = "b7c56a2387e6869cad0513f9465b54d331140ce17d1fe807189a57d9dec2e5d3"
OLD_MAIN = "        main = sorted(vol.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]\n"
NEW_MAIN = "        main = FRONT(d)\n        if main not in vol: continue\n"
OLD_ROWS = "ROWS = load(); BY = collections.defaultdict(dict); DUP = 0\n"
NEW_ROWS = "ROWS = load(); ROWS = [r for r in ROWS if r[0] not in EXCL_FN(ROWS)]; BY = collections.defaultdict(dict); DUP = 0\n"
MONTH_CH = "123456789ABC"

def front(d):
    day = date(int(d[:4]), int(d[4:6]), int(d[6:])); y, m = day.year, day.month
    for _ in range(15):
        first = date(y, m, 1); thu2 = first + timedelta(days=(3 - first.weekday()) % 7 + 7)
        if thu2 > day: return f"A05{y % 10}{MONTH_CH[m - 1]}000"
        m += 1
        if m == 13: y, m = y + 1, 1

SHORT = {}
def excl(rows):
    if SHORT.get("_done"): return SHORT["days"]
    g = collections.defaultdict(collections.Counter)
    for r in rows:
        if 540 <= r[1] <= 914: g[r[0]][(r[1] - 540) // 15] += 1
    bad = {}
    for d, c in g.items():
        miss = {540 + (k + 1) * 15: 15 - c.get(k, 0) for k in range(25) if c.get(k, 0) < 15}
        if miss: bad[d] = miss
    SHORT.update(_done=True, days=set(bad), detail=bad); return SHORT["days"]

def load_engine():
    src = (HERE / "kmf_nb.py").read_text(encoding="utf-8")
    assert hashlib.sha256(src.encode()).hexdigest() == NB_SHA and src.count(OLD_MAIN) == 1 and src.count(OLD_ROWS) == 1
    mod = types.ModuleType("kmf_nb"); mod.__file__ = str(HERE / "kmf_nb.py"); mod.FRONT = front; mod.EXCL_FN = excl
    sys.modules["kmf_nb"] = mod; exec(compile(src.replace(OLD_MAIN, NEW_MAIN).replace(OLD_ROWS, NEW_ROWS), mod.__file__, "exec"), mod.__dict__)
    assert hashlib.sha256((HERE / "kmf_hdd_pre.py").read_bytes()).hexdigest() == PRE_SHA
    import kmf_hdd_pre as P
    return mod, P

def main():
    K, P = load_engine(); from kmf_hdd_base import DAYS, stat, Z
    H = {d: K.execute(d, P.sig_h(d)) for d in DAYS}
    rows = {"H(대조)": {**stat(H)}}; daily = {"H(대조)": {d: round(v, 4) for d, v in H.items()}}; res = {}
    for f, cfgs in P.FAM.items():
        for i, c in enumerate(cfgs):
            p = {d: K.execute(d, P.sig_h(d, f, c)) for d in DAYS}; s = stat(p)
            s["−15 넘은 날"] = sum(1 for v in p.values() if v < -15.0); s["한 날 효과"] = P.one_day_share(p, H)
            s["기본 통과"] = (s["합"] >= 476.0 and s["MDD"] >= -36.1 and s["−15 넘은 날"] == 0 and s["앞반"] > 0 and s["뒤반"] > 0
                          and s["한 날 효과"] is not None and s["한 날 효과"] < 0.5)
            res[(f, i)] = s; rows[P.label(f, c)] = s; daily[P.label(f, c)] = {d: round(v, 4) for d, v in p.items()}
    for (f, i), s in res.items():
        s["통과"] = s["기본 통과"] and sum(1 for j in P.neighbors(f, i) if res[(f, j)]["기본 통과"]) >= 1
        s["엄한 읽기 통과(이웃만 2개 이상)"] = s["기본 통과"] and sum(1 for j in P.neighbors(f, i) if res[(f, j)]["기본 통과"]) >= 2
    passed = [(f, i) for (f, i), s in res.items() if s["통과"]]; pick = None
    if passed:
        fb = min({f for f, _ in passed}, key=lambda f: -max(res[(f, i)]["MDD"] for g, i in passed if g == f))
        i = max((i for g, i in passed if g == fb), key=lambda i: res[(fb, i)]["합"]); pick = P.label(fb, P.FAM[fb][i])
    data_sha = {str(q.relative_to(HERE.parent)): hashlib.sha256(q.read_bytes()).hexdigest() for q in (K.MINI, K.FUT, K.F1M)}
    assert data_sha == P.DATA_EXPECT
    meta = {"days": len(DAYS), "first": DAYS[0], "last": DAYS[-1], "engine_days": len(K.DAYS), "rows_read": len(K.ROWS), "dup_minutes": K.DUP,
            "뺀 날(불완전 15분봉 · 봉 끝 분: 빠진 분 수)": {d: SHORT["detail"][d] for d in sorted(SHORT["detail"])},
            "data_sha256": data_sha, "code_sha256": {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in ("kmf_hdd_fc.py", "kmf_hdd_pre.py", "kmf_hdd_base.py", "kmf_nb.py", "kmf_rlk4.py", "kmf_rl4.py")}}
    (HERE / "kmf_hdd_fc_out.json").write_text(json.dumps({"meta": meta, "rows": rows, "통과": [P.label(f, P.FAM[f][i]) for f, i in passed], "새 자료 후보(사용자 승인 뒤)": pick}, ensure_ascii=False, indent=1))
    (HERE / "kmf_hdd_fc_daily.json").write_text(json.dumps(daily, ensure_ascii=False))
    for k, s in rows.items(): print(k, {x: s.get(x) for x in ("합", "MDD", "최악", "앞반", "뒤반", "한 날 효과", "기본 통과", "통과")})
    print("뺀 날", sorted(SHORT["detail"]), "| 평가 날", len(DAYS), DAYS[0], DAYS[-1], "| 통과", [P.label(f, P.FAM[f][i]) for f, i in passed], "후보", pick)

if __name__ == "__main__":
    main()
