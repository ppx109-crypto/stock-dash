"""별도 클로드 검사 담당(RLK-0004)의 장중 자르기 시험: 40일 × 9개 시각에서 그 뒤 1분봉을 지우고 처음부터 다시 셈 → 그 시각 앞 신호 · 알 수 있는 정리 분 · 지연 0 · 1 · 2 거래가 같아야 함. 쓰는 법: python3 research/kmf_rlk4_audit_intraday_cut.py <저장소 뿌리>"""
import sys, importlib, collections, random
ROOT = sys.argv[1]; sys.path.insert(0, ROOT + "/research")
import kmf_nb as K, kmf_rlk4 as R
FULL_BY = {d: dict(v) for d, v in K.BY.items()}; FULL_DAYS = list(K.DAYS)
fns = ("t2", "s3", "r0", "s5", "s6")
full = {f: {d: getattr(R, f)(d) for d in R.EVAL} for f in fns}
fullpnl = {f: {d: [] for d in R.EVAL} for f in fns}
for f in fns:
    for d in R.EVAL:
        for dl in (0, 1, 2):
            lg = []; K.execute(d, full[f][d], delay=dl, log=lg); fullpnl[f][d].append(lg)
random.seed(1); days = random.sample(R.EVAL, 40)
bad = collections.Counter(); n = 0
for X in days:
    for M in (570, 615, 660, 705, 750, 795, 840, 885, 901):
        BY = collections.defaultdict(dict)
        for d in FULL_DAYS:
            if d < X: BY[d] = FULL_BY[d]
            elif d == X: BY[d] = {m: r for m, r in FULL_BY[d].items() if m < M}
        K.BY = BY; K.DAYS = sorted(d for d in BY if BY[d])
        K.B15 = K.bars(15); K.E10 = K.ind(K.B15, 10); K.E20 = K.ind(K.B15, 20)
        K.BYD = collections.defaultdict(list)
        for j, b in enumerate(K.B15): K.BYD[b[0]].append(j)
        R2 = importlib.reload(R)
        for f in fns:
            a = [s[:4] for s in full[f][X] if s[0] <= M]; b = [s[:4] for s in getattr(R2, f)(X) if s[0] <= M]
            # m_exit: only compare when known by M
            ae = [s[4] for s in full[f][X] if s[0] <= M and s[4] <= M]; be = [s[4] for s in getattr(R2, f)(X) if s[0] <= M and s[4] <= M]
            n += 1
            if a != b or ae != be: bad[f] += 1; print("다름", f, X, M, a, b)
            # trades fully closed before M (exit minute < M) must match
            for dl in (0, 1, 2):
                lg = []; K.execute(X, getattr(R2, f)(X), delay=dl, log=lg)
                fa = [t for t in fullpnl[f][X][dl] if t["정리분"] < M - 1]; fb = [t for t in lg if t["정리분"] < M - 1]
                if fa != fb[:len(fa)] or len(fb) != len(fa): bad[f + "_tr"] += 1; print("거래다름", f, X, M, dl, len(fa), len(fb))
print("비교", n, "다름", dict(bad))
