"""ENS-0068 합성 · 재현 시험."""
import json
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import ens as E  # noqa: E402
D, T = E.D, E.T
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


b = E.both(dict(E.FINAL))
chk("1 기준 재현(계좌 전체 34.113% · 덧붙임만 −1.982%)", b["full"]["annual_pct"] == 34.113 and b["dev"]["annual_pct"] == -1.982 and b["full"]["worst_full_month_pct"] == -14.043)
for mode in ("frac", "vote"):
    c = dict(E.FINAL, ens=E.ens(mode, ns=[24], ps=[3]))
    fa, fb = T.full(c), T.full(dict(E.FINAL))
    sa, sb = T.standalone(c), T.standalone(dict(E.FINAL))
    chk(f"2 구성원 하나({mode})면 지금 판과 NAV 같음", set(fa) == set(fb) and max(abs(fa[d] - fb[d]) for d in fa) < 1e-12
        and max(abs(sa[d] - sb[d]) for d in sa) < 1e-12)
cfg = dict(E.FINAL)
t = E.targets_ens
chk("3 순 노출: 모두 상승 → 122630 0.4", t("E:15/0/0", cfg) == (1.0, "122630", 0.4))
chk("3 순 노출: 모두 횡보 → 인버스 0.4 · 모두 하락 → 0", t("E:0/15/0", cfg) == (1.0, "114800", 0.4) and t("E:0/0/15", cfg)[2] == 0.0)
x = t("E:5/5/5", cfg); y = t("E:2/10/3", cfg)
chk("3 순 노출: 5/5/5 → 122630 0.0667 · 2/10/3 → 인버스 0.16", x[1] == "122630" and abs(x[2] - (0.8 / 3 - 0.4 / 3) / 2) < 1e-12 and y[1] == "114800" and abs(y[2] - 0.16) < 1e-12)
chk("4 다수결 같을 때 조심 쪽", E.vote((7, 7, 1)) == "횡보" and E.vote((5, 5, 5)) == "하락" and E.vote((8, 6, 1)) == "상승" and E.vote((6, 3, 6)) == "하락")
g = E.grid()
chk("5 격자 7칸", len(g) == 7 and [n for n, _ in g][1:] == ["frac_np_L0.4", "frac_n_L0.4", "vote_np_L0.4", "frac_np_L0.5", "frac_n_L0.5", "vote_np_L0.5"])
nb = E.neighbors(g[1][1])
chk("6 이웃 넷(n × 0.85 · × 1.15 · persist ∓ 1)", [x["ens"]["n"] for x in nb[:2]] == [[14, 17, 20, 24, 27], [20, 23, 28, 32, 37]]
    and [x["ens"]["p"] for x in nb[2:]] == [[1, 2, 3], [3, 4, 5]] and E.neighbors(g[2][1])[2]["ens"]["p"] == [2])
B = {"full": {"within": True, "annual_raw": 0.34, "worst_full_month_raw": -0.14}, "dev": {"annual_raw": -0.02, "worst_full_month_raw": -0.10}}
mk = lambda a, m, da, dm, w=True: {"full": {"within": w, "annual_raw": a, "worst_full_month_raw": m}, "dev": {"annual_raw": da, "worst_full_month_raw": dm}}
chk("7 잣대 경계(연 −0.5%p · 달 +1%p · 덧붙임만 안 나빠짐)", E.ok(mk(0.335, -0.13, -0.02, -0.10), B) and not E.ok(mk(0.3349, -0.13, -0.02, -0.10), B)
    and not E.ok(mk(0.34, -0.1301, -0.02, -0.10), B) and not E.ok(mk(0.34, -0.13, -0.0201, -0.10), B) and not E.ok(mk(0.40, -0.12, 0.0, 0.0, False), B))
chk("8 이웃 잣대(연 −1%p · 달 기준 · 덧붙임만 −0.5%p)", E.ok(mk(0.33, -0.14, -0.025, -0.2), B, nb=True) and not E.ok(mk(0.3299, -0.14, -0.02, -0.1), B, nb=True)
    and not E.ok(mk(0.34, -0.1401, -0.02, -0.1), B, nb=True) and not E.ok(mk(0.34, -0.14, -0.0251, -0.1), B, nb=True))
chk("9 잠금 통과", bool(E.verify_inputs()))
bad = json.loads(E.LOCK.read_text()); bad["research/ens.py"] = "0" * 64
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
    json.dump(bad, fh)
try:
    E.verify_inputs(fh.name); chk("10 잠금 다르면 멈춤", False)
except SystemExit:
    chk("10 잠금 다르면 멈춤", True)
print(f"모두 통과 {ok}개")
