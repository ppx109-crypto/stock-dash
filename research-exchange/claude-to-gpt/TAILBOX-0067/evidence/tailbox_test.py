"""TAILBOX-0067 시험 — 기준 재현 · 박스 판정 · 흔들림 맞춤 · 격자 · 잣대 · 이웃 · 잠금."""
import json, os, sys, tempfile
from pathlib import Path
os.environ["REG_BOX"] = "TAILBOX-0067"
sys.path.insert(0, "/home/user/stock-dash/research")
import tailbox as T
import regime_dev as D
ok = 0
def check(name, cond):
    global ok
    assert cond, name
    ok += 1
    print("통과", name)
D.DATA, D.FEAT = None, None
b = T.both(dict(T.FINAL))
check("1 기준 = MIX-0054 최종(계좌 전체 연 34.113% · 손실 40 · −14.043%) · 덧붙임만 2010-03 ~ 2016 연 −1.98%(AUDIT-MIX54-0066 ⑧과 같음)",
      b["full"]["annual_pct"] == 34.113 and b["full"]["loss_months"] == 40 and b["full"]["worst_full_month_pct"] == -14.043 and round(b["dev"]["annual_pct"], 2) == -1.98)
er = T.er_table(60); px = D.data()[1]["069500"]; ds = sorted(px); d0 = ds[300]; k = ds.index(d0)
path = sum(abs(px[ds[i]] - px[ds[i-1]]) for i in range(k - 59, k + 1))
check("2 ER(60) = |C_p − C_{p−60}| ÷ 60일 하루 변화 절댓값 합(그날까지 값만)", abs(er[d0] - abs(px[d0] - px[ds[k-60]]) / path) < 1e-12)
feat = D.FEAT[1]
s0 = T._ORIG_STATES(feat, T.FINAL); s1 = T.states_box(feat, dict(T.FINAL, box={"n": 60, "thr": 0.15}))
chg = [d for d in s1 if s1[d] != s0[d]]
check("3 박스: 원래 상승 · 횡보이고 ER < 0.15인 날만 '박스'로 바뀜 · 하락 · 그 밖은 그대로",
      chg and all(s1[d] == "박스" and s0[d] in ("상승", "횡보") and er[d] < 0.15 for d in chg)
      and all(s1[d] == s0[d] for d in s1 if d not in chg) and T.states_box(feat, T.FINAL) == s0)
check("4 '박스' 목표 = 덧붙임 0 · 1일봉 몫 그대로(1.0)", T.targets_box("박스", T.FINAL) == (1.0, T.FINAL["inv"], 0.0))
n0 = T.standalone(dict(T.FINAL)); n1 = T.standalone(dict(T.FINAL, lev_vt=10.0))
check("5 덧붙임만: lev_vt가 아주 크면(10) 지금 규칙과 NAV가 하루도 다르지 않음", n0 == n1)
g = T.grid()
check("6 격자 19 = 기준 + 가 12(L {0.4 · 0.5 · 0.6} × vt {0.15 · 0.20 · 0.25 · 0.30}) + 나 6(ER n {60 · 120} × thr {0.10 · 0.15 · 0.20})",
      len(g) == 19 and sum(1 for n, _ in g if n.startswith("가_")) == 12 and sum(1 for n, _ in g if n.startswith("나_")) == 6)
mk = lambda fa, fd, fm, w, da, dd, dm: {"full": {"annual_raw": fa, "worst_day_raw": fd, "worst_full_month_raw": fm, "within": w},
                                        "dev": {"annual_raw": da, "worst_day_raw": dd, "worst_full_month_raw": dm}}
bb = mk(0.34, -0.13, -0.14, True, -0.02, -0.08, -0.10)
check("7 가 잣대: 연 −0.5%p 안 · 하루 +2%p · 2010 ~ 2016 하루 · 달 · 연 안 나빠짐 → 채택 · 하루 +1.9%p는 탈락(이웃은 +1%p면 통과) · 2010 ~ 2016 달이 나빠지면 탈락",
      T.ok_tail(mk(0.336, -0.11, -0.13, True, -0.024, -0.08, -0.09), bb) and not T.ok_tail(mk(0.336, -0.111, -0.13, True, -0.02, -0.08, -0.10), bb)
      and T.ok_tail(mk(0.336, -0.12, -0.13, True, -0.05, -0.2, -0.3), bb, half=True) and not T.ok_tail(mk(0.336, -0.10, -0.13, True, -0.02, -0.08, -0.101), bb))
check("8 나 잣대: 2010 ~ 2016 연 +2%p · 계좌 전체 잣대 안 · 연 −1%p 안 · 달 −1%p 안 → 채택 · 2010 ~ 2016 +1.9%p는 탈락(이웃 +1%p면 통과) · 연 −1.1%p는 탈락",
      T.ok_box(mk(0.331, -0.13, -0.149, True, 0.0001, 0, 0), bb) and not T.ok_box(mk(0.34, -0.13, -0.14, True, -0.0011, 0, 0), bb)
      and T.ok_box(mk(0.34, -0.13, -0.14, True, -0.0099, 0, 0), bb, half=True) and not T.ok_box(mk(0.329, -0.13, -0.14, True, 0.05, 0, 0), bb))
check("9 이웃: 가 (0.5 · 0.20) = L 둘 + vt 둘 + 규칙 6 = 10 · 나 (60 · 0.15) = thr 둘 + n 하나 + 규칙 6 = 9",
      len(T.nb_tail(dict(T.FINAL, up_lev=0.5, lev_vt=0.20))) == 10 and len(T.nb_box(dict(T.FINAL, box={"n": 60, "thr": 0.15}))) == 9)
Tm = Path(tempfile.mkdtemp())
good = T.lock_body(); (Tm / "ok.json").write_text(json.dumps(good))
check("10 입력 잠금 13칸이 같으면 통과", T.verify_inputs(Tm / "ok.json") == good and len(good) == 13)
(Tm / "bad.json").write_text(json.dumps(dict(good, **{"etf-data/122630.json": "0" * 64})))
old = (T.LOCK, T.EVALS); T.LOCK, T.EVALS = Tm / "bad.json", Tm / "e.jsonl"
try:
    T.run(); stopped = False
except SystemExit as e:
    stopped = "122630" in str(e)
T.LOCK, T.EVALS = old
check("11 잠금이 다르면 첫 STARTED 전에 멈춤", stopped and not (Tm / "e.jsonl").exists())
print(f"모두 {ok}개 통과")
