"""MPOS-0023 준비 진단(G1 · 성과 안 봄 · 판단 순간 값 · 겹침 · 빠짐만): 원판 경로(문은 하나도 안 막음)에서 엔진이 기존 닮은 종목 문을
통과시킨 정배열 후보마다, 그 순간 실제 보유(open_slots · 자리 수 = 배정 칸)와 후보(요청 칸 = nrl.BASE_SIZE)로
1일봉 몫 안 '한계 위험 증가' = σ(보유 + 후보) − σ(보유)(하루 수익 σ · 전 거래일까지 60개 · 시작 · 끝 날 같은 구간만 · 칸 / 10 비중)를 셈.
함께: 평균 상관(MPOS-0022 K 문과 같은 정의) · 쌍별 최대 상관(같은 창 · 기존 문은 든 종목 산 날 창이라 다름). 장부는 원판과 같아야 함.
cwd = 고정 나무 · tree_run. 출력: EX_OUT json."""
import hashlib, json, os, sys, types
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402
_SRC = open(os.environ["EX_PARTS"], "rb").read()
P = types.SimpleNamespace(); exec(compile(_SRC, os.environ["EX_PARTS"], "exec"), P.__dict__)
DAYS = {c: [d for d, _ in b["rows"]] for c, b in nrl.prices.items()}
CLOSE = {c: [x for _, x in b["rows"]] for c, b in nrl.prices.items()}
REC = []
def win(code, d):
    r, last = P.window(DAYS[code], CLOSE[code], d, 60)
    assert last is None or last < d
    return r
def cov(a, b):
    ks = sorted(set(a) & set(b))
    if len(ks) < 40:
        return None
    x = [a[k] for k in ks]; y = [b[k] for k in ks]
    mx, my = sum(x) / len(x), sum(y) / len(y)
    return sum((p - mx) * (q - my) for p, q in zip(x, y)) / (len(ks) - 1)
def apart(row, held):
    if not nrl.kin(row, held):
        return False
    if nrl.tier(row) != "정배열" or not held:
        return True
    slots = sys._getframe(1).f_locals["open_slots"]
    d = row["date"]
    items = [(sp["row"]["code"], sp["자리"] / 10) for sp in slots.values()]
    cand = (row["code"], nrl.BASE_SIZE(row) / 10)
    W = {c: win(c, d) for c, _ in items + [cand]}
    if any(v is None for v in W.values()):
        REC.append([d, row["code"], None, None, None, "자료 모자람"]); return True
    def var(port):
        s = 0.0
        for c1, w1 in port:
            for c2, w2 in port:
                v = cov(W[c1], W[c2])
                if v is None:
                    return None
                s += w1 * w2 * v
        return s
    v0, v1 = var(items), var(items + [cand])
    cs = [P.corr(W[cand[0]], W[c]) for c, _ in items]
    cs = [x for x in cs if x is not None]
    if v0 is None or v1 is None or not cs:
        REC.append([d, row["code"], None, None, None, "겹친 구간 모자람"]); return True
    REC.append([d, row["code"], (max(v1, 0) ** 0.5 - max(v0, 0) ** 0.5) * 100, sum(cs) / len(cs), max(cs), ""])
    return True
rows = []
for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
    g = lab.run(pool, nrl.prices, nrl.BASE_HOLD, nrl.BASE_EXIT, slots=nrl.SLOTS, rank=rule.order, since=since, apart=apart, realistic=True, cap=130,
                detail=True, size=nrl.BASE_SIZE)
    rows += [(t["code"], t["산 날"], t["판 날"], t["손익"], t["자리"] if t.get("자리") is not None else 1) for t in g["매매목록"]]
json.dump(rows, open(os.environ["EX_OUT"] + ".led.json", "w"))
json.dump({"부품 지문": hashlib.sha256(_SRC).hexdigest(), "판단 순간": REC}, open(os.environ["EX_OUT"], "w"), ensure_ascii=False)
print(len(rows), len(REC))
