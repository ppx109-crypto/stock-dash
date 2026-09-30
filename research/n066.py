"""일봉 새 66회차 — 한투 재무비율(분기 · 한 번도 안 쓴 자료)을 순서 · 크기 · 거르기로.

발표일이 없어 분기 끝 + 60일(12월 결산 + 90일) 뒤부터 씀(늦게 잡아 미래 참조를 막음). 재무비율 분기는 2019~라 앞 반은 2019~2020만 덮음.
실행: NRL_CACHE=... python3 research/n066.py
"""
import sys

sys.path.insert(0, "/home/user/stock-dash/research")
import ntools as T
import nrl
import rule

print("== 일봉 새 66회차: 한투 재무비율 ==", flush=True)
KEYS = ("ROE", "영업이익증가율", "매출증가율", "부채비율")
for k in KEYS:
    print(f"값 있는 몫 {k}", T.cover(lambda r, k=k: T.ratio_now(r, k)), "%", flush=True)
base = T.once("지금 규칙(기준)")
ROE = (lambda r: T.ratio_now(r, "ROE"), False)
OPG = (lambda r: T.ratio_now(r, "영업이익증가율"), False)
SAG = (lambda r: T.ratio_now(r, "매출증가율"), False)
DEBT = (lambda r: T.ratio_now(r, "부채비율"), True)
FLOW, RET = (T.flow_strength, True), (T.ret, False)
for tag, parts in (("ROE 높은 것", [ROE]), ("영업이익증가율", [OPG]), ("매출증가율", [SAG]), ("부채 적은 것", [DEBT]),
                   ("ROE + 영업이익증가율", [ROE, OPG]), ("수급 약 + 수익 큼 + ROE", [FLOW, RET, ROE])):
    got = T.once("순서: " + tag, rank=T.rank_by(parts))
    T.diff_check(base, got)
for cut in (0.0, 5.0):
    hold = lambda r, cut=cut: nrl.BASE_HOLD(r) and not ((T.ratio_now(r, "ROE") is not None) and T.ratio_now(r, "ROE") < cut)
    got = T.once(f"거르기: ROE {cut}% 아래면 안 삼", holds=hold)
    T.diff_check(base, got, "막은")
size = lambda r: 4 if rule.holds(r) else (4 if (nrl.steady(r) >= 3 or (T.ratio_now(r, "ROE") or -99) >= 15) else 2)
got = T.once("크기: 정배열도 ROE 15%↑면 4칸", size=size)
T.diff_check(base, got)
print("끝", flush=True)
