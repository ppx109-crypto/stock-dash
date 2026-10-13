"""RLK-0007 — 새 날(2026-10-14 ~) 앞으로 걷기 실행기(round 3 초안 · 사용자 승인 · 잠금 전).
잠근 코드(kmf_nb · kmf_rlk4 · kmf_rl4)는 한 글자도 안 바꿉니다. kmf_nb.py 원문을 읽어 해시를 맞춘 뒤
'futures-1m 읽기 조건' 한 줄만 바꾼 사본을 kmf_nb 이름으로 올립니다(바꾼 줄은 assert로 정확히 1곳):
  개발(10-13 하루) 줄 + 미리 정한 규칙으로 고른 새 날(FWD_DAYS) 줄만 읽음. 결손 · 빠진 날 줄은 EMA · ATR · 조용함 이력에도 넣지 않음(없던 날).
이어 배우기: 따로 저장하는 checkpoint는 없습니다. 날마다 처음(03-06)부터 날짜순으로 다시 재생하므로 148일 학습 이력이 그대로 이어집니다.
  --selfcheck: FWD_DAYS가 비면 148일 RL-4 N z0.5 결정 장부 · 날별 손익 · H가 잠근 결과(kmf_rl4_*.json)와 한 칸도 안 다른지 확인.
이것은 '20일이 찬 뒤 한 번 하는 날짜순 재생'이며 매일 실제로 내린 shadow 결정이 아닙니다(결과에 그렇게 표시).
모드: --quality(손익 없이 새 날 자료 품질만) · --selfcheck · --final(20일이 찼을 때 한 번)."""
import csv, json, sys, types, hashlib, random, collections, subprocess, statistics as st
from datetime import date, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; RS = ROOT / "research"; sys.path.insert(0, str(RS))
LOCK = {"kmf_nb.py": "b34f3549fe9a93b951e104148605404737f0bab30faf2d6960296d59957b55de",
        "kmf_rlk4.py": "8caed7c65867511572b4a12e53780d97940fbe901ec7c0a9be506455532765a6",
        "kmf_rl4.py": "c3406edc58fc81d40bec78d904b4ce947c7765efb33939fa7ae2c01fc9bf76d9"}
REF = {"kmf_rl4_decisions.json": "a4ec21228dc387ac2123307dc21423dd5f5fb6340910e3267d7f1dc3cb710e60",
       "kmf_rl4_daily.json": "e707acb38154a731362e6592a716fb0f1bca063d2443240f73ac2f6617974f20"}
F1M = ROOT / "futures-1m/mini_kospi200_futures_1min.csv"; CAL = ROOT / "etf-data/069500.json"
FWD_START, NEED, JUDGE_DELAY, FAMILY = "20261014", 20, 0, ("H", "RL-4 N z0.5", "쉼")   # 지연 0 = 신호 봉 끝 바로 그 분 시가(사용자 2026-10-14 "실전 체결 지연은 길어야 5초" → 1 · 2분 지연은 셈 · 보고 안 함)
SLIPS = (0.05, 0.1, 0.25)                  # 민감도만: 거래 한 번(왕복)마다 이만큼 불리하게 = 5초 안 체결의 값 차이(판정에 안 씀)
OLD = '            if not (DEV_FROM_F1M <= d < DEV_END) or (CUT and d >= CUT): continue\n'
NEW = '            if not ((DEV_FROM_F1M <= d < DEV_END) or d in FWD_DAYS) or (CUT and d >= CUT): continue\n'
DEV_DATA = ("kiwoom-data/mini_1min_2026_01_08.csv", "kiwoom-data/kospi200_futures_1min.csv")   # 148일 초기 학습에 읽히는 개발 입력(F1M 10-13 하루는 F1M 해시로)
FIRST, LAST = 540, 934                     # 엔진(kmf_nb.load)과 같은 정규장 분(09:00 ~ 15:34) · 품질 검사도 이 안에서만(GPT #335 결함 2)
DEV_HASH = {"kiwoom-data/mini_1min_2026_01_08.csv": "2acfec06a264da7d8d306d911da4c426dccd0d84e8c42b5d005e8c304a9eafe7",
            "kiwoom-data/kospi200_futures_1min.csv": "84831af6b017d6b52ee06cf8c9d5c3116a7452ae9c14deb938299875649a26de"}
F1M_DEV_SLICE = "6073899291895e9909a0ff39f1da891245226994de35ca0a2fb1796a24b61b7d"   # futures-1m 파일 중 10-14 앞 줄(머리줄 뺌 · 822줄)만의 해시

def f1m_dev_slice():
    lines = [l for l in F1M.read_bytes().split(b"\n")[1:] if l and l[:10].replace(b"-", b"") < FWD_START.encode()]
    return hashlib.sha256(b"\n".join(lines)).hexdigest()
MONTH_CH = "123456789ABC"                  # main collect_fut_1min.py(sha256 0fd513a8…e447)의 front_code 규칙을 그대로 옮김(GPT #335 결함 3)
COLLECTOR_SHA = "0fd513a81aad8fb37ffafbdab380efc47372631a728c7a9084a59d8d0f15e447"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def expected_code(d):
    """그날 장 전에 아는 미니 근월물 코드(만기일 = 둘째 목요일 당일부터 다음 월물)."""
    day = date(int(d[:4]), int(d[4:6]), int(d[6:])); y, m = day.year, day.month
    for _ in range(15):
        first = date(y, m, 1); second_thu = first + timedelta(days=(3 - first.weekday()) % 7 + 7)
        if second_thu > day: return f"A05{y % 10}{MONTH_CH[m - 1]}000"
        m += 1
        if m == 13: y, m = y + 1, 1

detail = {}

def fwd_minutes():
    """새 날(FWD_START ~) 줄의 날 · 분 · 계약 코드만(값은 읽지 않음 · 손익 계산 없음)."""
    out = collections.defaultdict(lambda: {"m": [], "code": set()})
    with open(F1M, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            d = r["datetime"][:10].replace("-", "")
            m = int(r["datetime"][11:13]) * 60 + int(r["datetime"][14:16])
            if d < FWD_START or not (FIRST <= m <= LAST): continue
            out[d]["m"].append(m); out[d]["code"].add(r["code"])
    return out

def day_ok(d, ms, codes):
    """미리 정한 포함 규칙(결과 보기 전 고정).
    하루: kmf13.complete_days와 같음(중복 0 · 고유 분 ≥ 360 · 첫 분 ≤ 09:05 · 끝 분 ≥ 15:29 · 이웃 분 빈 곳 ≤ 5분).
    봉: 09:00 ~ 15:15 신호용 15분봉 25개 모두 빠진 분 ≤ 5(아니면 그날 전체 뺌 · 봉만 빼지 않음).
    계약: 그날 코드 1개(수집기가 장 전에 아는 달력 규칙 '만기일 당일부터 다음 월물'로 고름 · 당일 거래량으로 고르지 않음)."""
    u = sorted(set(ms)); why = []
    if len(ms) != len(u): why.append(f"중복 {len(ms) - len(u)}")
    if len(u) < 360: why.append(f"고유 분 {len(u)}")
    if not u or u[0] > 545: why.append("첫 분 늦음")
    if not u or u[-1] < 929: why.append("끝 분 이름(15:29 앞)")
    gap = max((b - a for a, b in zip(u, u[1:])), default=999)
    if gap > 5: why.append(f"빈 곳 {gap}분")
    s = set(u); worst = max(15 - sum(1 for m in range(540 + 15 * k, 555 + 15 * k) if m in s) for k in range(25))
    if worst > 5: why.append(f"15분봉 빠진 분 최대 {worst}")
    bars = [15 - sum(1 for m in range(540 + 15 * k, 555 + 15 * k) if m in s) for k in range(25)]
    exp = expected_code(d)
    if len(codes) != 1: why.append(f"계약 코드 {len(codes)}개")
    elif exp not in codes: why.append(f"계약 코드 {sorted(codes)[0]} ≠ 달력 근월물 {exp}")
    return not why, why, {"rows": len(ms), "unique_min": len(u), "max_gap": gap, "bar_missing_max": worst, "bar_missing": bars, "codes": sorted(codes), "expected_code": exp}

def calendar_days():
    """거래일 달력(KODEX 200 일봉 날짜) · 새 날 줄이 아예 없는 거래일을 '수집 실패'로 가려내는 데만 씀."""
    return sorted(d for d, _ in json.loads(CAL.read_text())["closes"] if d >= FWD_START)

def pick_days():
    global detail
    fm = fwd_minutes(); cal = calendar_days(); seen = sorted(set(cal) | set(fm)); good, bad = [], {}; detail = {}
    for d in seen:
        if d not in fm: bad[d] = {"사유": ["거래일인데 줄 없음(수집 실패)"]}; continue
        ok, why, info = day_ok(d, fm[d]["m"], fm[d]["code"])
        if d not in cal: why = why + ["달력에 없는 날(휴장 · 달력 늦음)"]; ok = False
        (good.append(d) if ok else bad.__setitem__(d, {"사유": why, **info})); detail[d] = {"포함": ok, "사유": why, **info}
    return good, bad, cal

def load_engine(fwd_days):
    """잠근 kmf_nb 원문 해시 확인 → 읽기 조건 한 줄만 바꾼 사본을 kmf_nb로 올림 → kmf_rlk4 · kmf_rl4 원본 import."""
    for f, h in LOCK.items(): assert sha(RS / f) == h, f"{f} 해시 다름"
    src = (RS / "kmf_nb.py").read_text(encoding="utf-8"); assert src.count(OLD) == 1
    mod = types.ModuleType("kmf_nb"); mod.__file__ = str(RS / "kmf_nb.py"); mod.FWD_DAYS = frozenset(fwd_days)
    sys.modules["kmf_nb"] = mod; exec(compile(src.replace(OLD, NEW), mod.__file__, "exec"), mod.__dict__)
    import kmf_rlk4, kmf_rl4
    return mod, kmf_rl4

def selfcheck():
    for f, h in DEV_HASH.items(): assert sha(ROOT / f) == h, f"{f} 개발 입력 해시 다름"
    assert f1m_dev_slice() == F1M_DEV_SLICE, "futures-1m 개발 구간(10-13 앞) 해시 다름"
    K, R = load_engine([])
    for f, h in REF.items(): assert sha(RS / f) == h, f"{f} 해시 다름"
    rdec = json.loads((RS / "kmf_rl4_decisions.json").read_text()); rday = json.loads((RS / "kmf_rl4_daily.json").read_text()); bad = 0
    for dl in (0, 1, 2):
        P = R.arm_pnl(dl); p, pick, dec = R.run(P, "N", 0.5)
        bad += sum(1 for d in R.EVAL if json.loads(json.dumps(dec[d], ensure_ascii=False)) != rdec["RL-4 상태N z0.5"][str(dl)][d])
        bad += sum(1 for d in R.EVAL if abs(round(p[d], 4) - rday["RL-4 상태N z0.5"][str(dl)][d]) > 1e-9)
        bad += sum(1 for i, d in enumerate(R.EVAL) if i >= R.WARM and abs(round(P["H"][d], 4) - rday["대조 늘 H(손 합침)"][str(dl)][d]) > 1e-9)
    res = {"eval_days": len(R.EVAL), "다른 칸": bad, "kmf_nb 사본 = 원본 DAYS": K.DAYS[-1] == "20261013"}
    print("자체 확인", res); return bad

def mtm_low(K, d, log):
    """그날 장중 평가 최저(실현 + 보유 중 평가 · 비용 뒤) — 보고만."""
    real = low = 0.0
    for t in log:
        if t["d"] != d: continue
        side, ent = t["방향"], t["진입가"]
        for m in range(t["진입분"], min(t["정리분"], 934) + 1):
            r = K.BY[d].get(m)
            if r: low = min(low, real + side * ((r[4] if side > 0 else r[3]) - ent) - 2 * K.COST)
        real += t["손익"]; low = min(low, real)
    return round(low, 4)

def block_ci(diff, B=2000, L=5, seed=0):
    rng = random.Random(seed); n = len(diff); sums = []
    for _ in range(B):
        x = []
        while len(x) < n: s = rng.randrange(0, n - L + 1); x += diff[s:s + L]
        sums.append(sum(x[:n]))
    sums.sort(); return [round(sums[int(0.025 * B)], 4), round(sums[int(0.975 * B) - 1], 4)]

def final():
    good, bad, cal = pick_days()
    if len(good) < NEED: print("WAITING_DATA", len(good)); return 2
    sc = subprocess.run([sys.executable, __file__, "--selfcheck"], capture_output=True, text=True)   # 별도 프로세스(GPT #335 결함 1 · 모듈 캐시 섞임 막기)
    if sc.returncode != 0: print("BLOCKED 148일 자체 확인 실패", sc.stdout[-500:], sc.stderr[-500:]); return 3
    fwd = good[:NEED]; K, R = load_engine(fwd); assert set(fwd) <= set(R.EVAL)
    out = {"표시": "20일이 찬 뒤 한 번 한 날짜순 재생(매일 실제 shadow 결정 아님)", "새 날": fwd, "뺀 날": bad,
           "code_sha256": {f: sha(RS / f) for f in (*LOCK, "kmf_fwd.py")}, "data_sha256": {**{f: sha(ROOT / f) for f in DEV_DATA}, "futures-1m 개발 구간(10-14 앞)": f1m_dev_slice(), str(F1M.relative_to(ROOT)): sha(F1M), str(CAL.relative_to(ROOT)): sha(CAL)},
           "148일 자체 확인(별도 프로세스)": sc.stdout.strip()[-300:], "참고 결과 해시": {f: sha(RS / f) for f in REF}, "수집기 front_code 규칙 sha256": COLLECTOR_SHA,
           "날별 품질(포함 · 뺀 날 · 봉별 빠진 분 · 계약)": {d: detail[d] for d in sorted(detail) if d <= fwd[-1]},
           "CAP(엔진 안 하루 멈춤)": K.CAP, "판정 잣대": "지연 0(5초 안 체결 · 사용자 2026-10-14) · 비용 뒤 장 끝 그날 손익 ≥ −15p(자르지 않고 그대로 기록)", "지연별": {}}
    for dl in (JUDGE_DELAY,):
        P = R.arm_pnl(dl); p, pick, dec = R.run(P, "N", 0.5)
        logs = {"S3": [], "R0": []}
        for d in fwd:
            K.execute(d, R.R4.s3(d), delay=dl, log=logs["S3"]); K.execute(d, R.R4.r0(d), delay=dl, log=logs["R0"])
        arm_of = {"H": {d: ("R0" if R.Z[d] else "S3") for d in fwd}, "RL-4 N z0.5": {d: pick[d] for d in fwd}, "쉼": {d: "쉼" for d in fwd}}
        res = {}
        for fam in FAMILY:
            ser = {d: (0.0 if arm_of[fam][d] == "쉼" else P[arm_of[fam][d]][d]) for d in fwd}
            base = lambda d: ("R0" if R.Z[d] else "S3") if arm_of[fam][d] == "H" else arm_of[fam][d]   # RL-4가 H 팔을 고르면 그날 H가 쓰는 팔
            tr = [t for d in fwd if base(d) != "쉼" for t in logs[base(d)] if t["d"] == d]
            eq = pk = mdd = 0.0
            for d in fwd: eq += ser[d]; pk = max(pk, eq); mdd = min(mdd, eq - pk)
            res[fam] = {"합": round(sum(ser.values()), 4), "날별": {d: round(v, 4) for d, v in ser.items()}, "장 끝 최악": round(min(ser.values()), 4),
                        "−15p 위반 날": [d for d in fwd if ser[d] < -15.0], "날 끝 MDD": round(mdd, 4),
                        "장중 평가 최저": min((mtm_low(K, d, [t for t in tr if t["d"] == d]) for d in fwd), default=0.0),
                        "거래 수": len(tr), "보유 분 합": sum(t["정리분"] - t["진입분"] for t in tr), "비용 합": round(len(tr) * 2 * K.COST, 4),
                        "미끄럼 민감도(근사 · 판정 안 씀)": {str(s): round(sum(ser.values()) - s * len(tr), 4) for s in SLIPS},
                        "고른 팔 날 수": dict(collections.Counter(arm_of[fam][d] for d in fwd))}
            res[fam]["PASS"] = res[fam]["합"] > 0 and not res[fam]["−15p 위반 날"]
        diff = [res["RL-4 N z0.5"]["날별"][d] - res["H"]["날별"][d] for d in fwd]; ci = block_ci(diff)
        res["RL − H"] = {"합": round(sum(diff), 4), "날별": dict(zip(fwd, [round(x, 4) for x in diff])), "5일 덩어리 재표집 95%": ci, "RL이 낫다고 말함": sum(diff) > 0 and ci[0] > 0}
        res["결정 장부(RL-4 N z0.5 · 새 날)"] = {d: dec[d] for d in fwd}; out["지연별"][str(dl)] = res
    out["판정(지연 0)"] = {f: out["지연별"][str(JUDGE_DELAY)][f]["PASS"] for f in ("H", "RL-4 N z0.5")}
    (RS / "kmf_fwd_out.json").write_text(json.dumps(out, ensure_ascii=False, indent=1)); print(json.dumps(out["판정(지연 0)"], ensure_ascii=False)); return 0

def quality():
    good, bad, cal = pick_days()
    q = {"새 날 포함(앞에서부터)": good, "뺀 날 · 사유": bad, "거래일(달력)": cal, "모인 날": len(good), "필요": NEED}
    (RS / "kmf_fwd_quality.json").write_text(json.dumps(q, ensure_ascii=False, indent=1)); print(json.dumps({k: q[k] for k in ("모인 날", "필요")}, ensure_ascii=False), "뺀 날", list(bad)); return 0

if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--selfcheck"]: sys.exit(1 if selfcheck() else 0)
    sys.exit(final() if a == ["--final"] else quality())
