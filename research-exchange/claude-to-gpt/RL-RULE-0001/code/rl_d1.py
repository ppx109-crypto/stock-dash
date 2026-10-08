"""RL-RULE-0001 · 1일봉 D0 환경 위 온라인 문맥 밴딧 강화학습(클로드 PREREG 2e85514a).
python3 -E -P rl_d1.py <b2> <nrl-cache.pkl> <출력>
PR #45 daily_exec.py 앞부분(신호 · 장부 · 순차 실행)을 그대로 불러 쓰고, run_d1 원문에 에이전트 갈고리 두 곳만 끼움:
① 매도 체결 뒤 새로 닫힌 포지션의 비용 뒤 수익률을 보상으로 학습, ② 매수 후보마다 사기/건너뛰기 행동."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_src = (HERE / "daily_exec.py").read_text(encoding="utf-8").split("RUNS, CUTS = {}, {}")[0]
G = {"__name__": "rl_base", "__file__": str(HERE / "daily_exec.py")}
exec(compile(_src, "daily_exec(앞부분 · PR #41/#45 그대로)", "exec"), G)
sys.path.insert(0, str(HERE))
import common as CM  # noqa: E402
import numpy as np  # noqa: E402

KN, nrl = G["KN"], G["nrl"]
OUT = Path(sys.argv[3])
DAYS_ALL, PICKS, SIZE, BR = list(G["DAYS"]), G["PICKS"], G["SIZE"], nrl.BR
EPS, N_MIN, BR_EDGE = 0.10, 10, 70
PERIODS = (("2017-02~2020-12(배우는 초기)", "20170201", "20201231"), ("2021~2022", "20210101", "20221231"),
           ("2023-01~2026-09", "20230101", "20260930"), ("전체 2017-02~2026-09", "00000000", "99999999"))


class Agent:
    """표 정책 문맥 밴딧. 상태 8칸 × 행동(사기/건너뛰기). 건너뛰기 가치 0 고정, 사기 가치 = 자기 매매 보상 평균."""

    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        self.n, self.sum, self.pid_state, self.seen = {}, {}, {}, 0
        self.count = {"buy_learning": 0, "buy_greedy": 0, "buy_explore": 0, "skip": 0, "rewards": 0}
        self.hist, self.last_month = [], None
        self.log = []

    @staticmethod
    def state(row, d):
        if nrl.tier(row) == "규칙":
            br = "추세"
        else:
            br = {4: "정배열연속", 3: "신선", 2: "약한"}.get(int(SIZE(row)), f"기타{int(SIZE(row))}")
        return br + ("|폭70+" if BR.get(d, 0) >= BR_EDGE else "|폭70-")

    def act(self, s, pid, d):
        u = self.rng.random()                       # 후보마다 늘 1번(흐름 고정)
        n = self.n.get(s, 0)
        if n < N_MIN:
            kind = "buy_learning"
        elif self.sum[s] / n > 0:
            kind = "buy_greedy"
        elif u < EPS:
            kind = "buy_explore"
        else:
            kind = "skip"
        self.count[kind] += 1
        self.log.append((d, pid, s, kind))
        if kind != "skip":
            self.pid_state[pid] = s
            return True
        return False

    def learn(self, closed, d):
        for row in closed[self.seen:]:
            s = self.pid_state.pop(row["pid"], None)
            if s is None:
                continue
            if not str(row["last_exit"])[:8] <= d:
                raise AssertionError("미래 참조: 보상 날짜 > 학습 날짜")
            r = row["pnl_net"] / row["invest0"]
            self.n[s] = self.n.get(s, 0) + 1
            self.sum[s] = self.sum.get(s, 0.0) + r
            self.count["rewards"] += 1
        self.seen = len(closed)
        if d[:6] != self.last_month:
            self.last_month = d[:6]
            self.hist.append((d, self.table()))

    def table(self):
        return {s: {"n": self.n[s], "mean_ret": self.sum[s] / self.n[s],
                    "action": "사기(배우는 중)" if self.n[s] < N_MIN else ("사기" if self.sum[s] > 0 else "건너뛰기(ε 탐색)")}
                for s in sorted(self.n)}


rs = _src[_src.index("def run_d1("):_src.index("\ndef snapshot(")]


def rep(s, a, b):
    assert s.count(a) == 1, a
    return s.replace(a, b)


rs = rep(rs, "def run_d1(mode, mult, LN=None, CLm=None, PK=None, snap_day=None):",
         "def run_rl(mode, mult, LN=None, CLm=None, PK=None, snap_day=None, AG=None):")
rs = rep(rs, '    acc = KN.Account(KN.Costs(CC, market_of, mult, "stock"))', '    acc = KN.Account(KN.Costs(CC, market_of, mult, "stock"), CM.CASH)')
rs = rep(rs, "            pend_sell = keep\n", "            pend_sell = keep\n            if AG is not None:\n                AG.learn(acc.closed, d)\n")
rs = rep(rs, "            want = min(max(int(SIZE(row)), 1), SLOTS - used)\n",
         "            want = min(max(int(SIZE(row)), 1), SLOTS - used)\n"
         "            if AG is not None and not AG.act(AG.state(row, d), f\"{c}:{d}\", d):\n"
         "                continue\n")
exec(compile(rs, "run_rl(run_d1 원문 + 에이전트 갈고리)", "exec"), G)
G["CM"] = CM


def run(mult, seed=None, LN=None, CLm=None, PK=None):
    ag = Agent(seed) if seed is not None else None
    r = G["run_rl"]("next", mult, LN=LN, CLm=CLm, PK=PK, AG=ag)
    r["cal"] = [d for d, _, _ in r["nav"]]
    r["agent"] = ag
    return r


def by_code(r):
    by = {}
    for p in r["closed"] + r["open"]:
        by[p["code"]] = by.get(p["code"], 0.0) + p["pnl_net"]
    return by


def median(xs):
    s = sorted(xs)
    return (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2


def raw(r):
    nav = r["nav"]
    seg = [CM.CASH] + [x[1] for x in nav]
    rets = [seg[i] / seg[i - 1] - 1 for i in range(1, len(seg))]
    yrs = KN._years(nav[0][0], nav[-1][0])
    peak, mdd = seg[0], 0.0
    for v in seg:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    wd = min(range(len(rets)), key=lambda i: rets[i])
    return {"CAGR": ((seg[-1] / seg[0]) ** (1 / yrs) - 1) * 100, "MDD": mdd * 100, "worst_day": rets[wd] * 100, "worst_day_at": nav[wd][0],
            "day_breach": sum(1 for x in rets if x < -0.15 - 1e-12), "end_nav": seg[-1],
            "fills": sum(1 for f in r["fills"] if f["status"] in ("FILLED", "REDUCED"))}


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)),
                            encoding="utf-8")


OUT.mkdir(parents=True, exist_ok=True)
RES, RUNS = {"runs": {}}, {}
for name, m, seed in [("B", 1.0, None), ("B", 2.0, None)] + [("RL", m, s) for s in (0, 1, 2, 3) for m in (1.0, 2.0)]:
    key = f"{name}_x{m:g}" + (f"_s{seed}" if seed is not None else "")
    r = RUNS[key] = run(m, seed)
    rp = CM.stats(r, PERIODS)
    w = raw(r)
    ent = {"raw": w, "report": CM.strip(rp), "monthly": rp[PERIODS[3][0]]["monthly"], "notes": r["notes"],
           "gap": [r["tot"].get("max_gap_cash"), r["tot"].get("max_gap_nav")]}
    if r["agent"]:
        ag = r["agent"]
        ent["agent"] = {"count": ag.count, "final_table": ag.table(), "pending_unrewarded": len(ag.pid_state)}
        dump(f"policy_history_{key}.json", {"monthly_tables": ag.hist, "decisions": ag.log})
    RES["runs"][key] = ent
    with open(OUT / f"nav_{key}.csv", "w", encoding="utf-8") as f:
        f.write("date,nav_won,invested_won\n")
        f.writelines(f"{d},{n:.2f},{i:.2f}\n" for d, n, i in r["nav"])
    print(key, round(w["end_nav"]), round(w["CAGR"], 2), round(w["MDD"], 2), round(w["worst_day"], 2), w["worst_day_at"], w["day_breach"],
          "체결", w["fills"], "구간", {p[0][:9]: rp[p[0]]["CAGR"] for p in PERIODS}, "에이전트", r["agent"].count if r["agent"] else "-", flush=True)
    if key == "B_x2":                                       # 기준 맞춤(PR #45 · #51)
        b1 = RUNS["B_x1"]
        tr_end = [n for d, n, _ in b1["nav"] if d <= "20201231"][-1]
        chk = {"train_end_x1": (11653611, round(tr_end)), "full_end_x1": (80945976, round(b1["nav"][-1][1])),
               "full_end_x2": (51761721, round(r["nav"][-1][1]))}
        RES["baseline_check"] = {k: {"ref": a, "claude": b, "same": a == b} for k, (a, b) in chk.items()}
        print("기준 맞춤", RES["baseline_check"], flush=True)
        if not all(v["same"] for v in RES["baseline_check"].values()):
            dump("rl_results.json", RES)
            print("BLOCKED · 기준 불일치", flush=True)
            raise SystemExit(3)

# ── 자르기 시험 2판(RL seed 0 · 비용 1배) ──
RES["cut_test"] = {}
for x in ("20201231", "20230630"):
    LN2 = {c: dict(v, closes=[(y * 1.37 if dd > x else y) for dd, y in zip(v["날"], v["closes"])]) for c, v in G["LANE"].items()}
    CL2 = {c: G["bump_after"](v, x) for c, v in G["CL"].items()}
    PK2 = {d: v for d, v in PICKS.items() if d <= x}
    rc = run(1.0, 0, LN=LN2, CLm=CL2, PK=PK2)
    full = RUNS["RL_x1_s0"]
    same = G["same_prefix"](dict(full, snap=None), dict(rc, snap=None), x)
    pa = [t for t in full["agent"].hist if t[0] <= x]
    pb = [t for t in rc["agent"].hist if t[0] <= x]
    la = [z for z in full["agent"].log if z[0] <= x]
    lb = [z for z in rc["agent"].log if z[0] <= x]
    RES["cut_test"][x] = {"fills_equal": same["fills_equal"], "nav_equal": same["nav_equal"], "n_days": same["n_days"],
                          "policy_tables_equal": pa == pb, "decisions_equal": la == lb, "n_decisions": len(la)}
    print("자르기", x, RES["cut_test"][x], flush=True)

# ── 판정(PREREG 그대로) ──
S = (0, 1, 2, 3)
E = lambda s: RES["runs"][f"RL_x2_s{s}"]["raw"]
b2 = RES["runs"]["B_x2"]["raw"]
rate = [E(s)["end_nav"] / b2["end_nav"] - 1 for s in S]
conc = []
for s in S:
    A, Bb = by_code(RUNS["B_x2"]), by_code(RUNS[f"RL_x2_s{s}"])
    diff = {c: Bb.get(c, 0.0) - A.get(c, 0.0) for c in set(A) | set(Bb)}
    pos = sum(v for v in diff.values() if v > 0)
    top = max(diff.items(), key=lambda x: x[1])
    conc.append({"seed": s, "net": E(s)["end_nav"] - b2["end_nav"], "positive_sum": pos, "top_code": top[0], "top_won": top[1],
                 "top_share": top[1] / pos if pos > 0 else None, "top5_abs": sorted(diff.items(), key=lambda x: -abs(x[1]))[:5]})
tops = [c["top_code"] for c in conc if c["top_share"] is not None and c["top_share"] >= 0.70]
same_code = max((tops.count(c) for c in set(tops)), default=0)
crit = {"1_wins_ge3": sum(1 for x in rate if x > 0) >= 3, "2_median_rate_ge5pct": median(rate) >= 0.05,
        "3_no_day_breach": all(RES["runs"][f"RL_x{m}_s{s}"]["raw"]["day_breach"] == 0 for s in S for m in ("1", "2")),
        "4_cagr2_median_pos": median([E(s)["CAGR"] for s in S]) > 0, "5_not_concentrated": same_code < 3,
        "6_cut_test": all(v["fills_equal"] and v["nav_equal"] and v["policy_tables_equal"] and v["decisions_equal"] for v in RES["cut_test"].values())}
RES["judgement"] = {"rate_vs_B_x2": rate, "median_rate": median(rate), "concentration": conc, "criteria": crit,
                    "verdict": "개선 후보" if all(crit.values()) else "개선 없음"}
print("판정", crit, RES["judgement"]["verdict"], flush=True)
dump("rl_results.json", RES)
print("끝", flush=True)
