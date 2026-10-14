"""COMP-0001 창 ① 보완 봇(공개 규칙) — 매일 09:00 ~ 09:45 · 진입은 15분봉 끝 09:15(555) · 09:30(570)만 · 09:45(585) 시가에 모두 정리.
대상 추세봇: 클로드 제작 최선 추세봇 P2 v1.3(비공개 · 사용자 2026-10-14 "너가 제작한 최선의 추세봇이 맞아") · P2는 09:50(590) 전 보유 0(같은 자료).
한 계약 결합: 창 ①이 끝난 뒤 그날 P2 하루 한도 = 15 − max(0, −창 ① 손익)(사용자 "−15p로 계산해") · 결합 계산은 비공개 엔진(결과 숫자만 공개).
신호 자료: 그날 닫힌 15분봉 · 전날까지 끝난 날봉(ATR = 날 폭 EMA14 · 종가 EMA10/20) · 09:00 시가(갭). 지연 0 · 비용 0.04 · CAP 12 · 1계약.
판(6 · 결과 전 고정): GPT #343 H1 = T2 눌림 뒤 재개(첫 유효 신호 1번) 손절 {1.0, 1.5} ATR ·
  클로드(탐색 agentW1 뒤 · 사후 선택 표시) = 갭 되돌림 k {0.3, 0.5} · 15분 EMA10 띠 되돌림 k {1.0, 1.5} + 평평(|EMA20 4봉 기울기|/ATR ≤ 0.5).
평가: 2026-01-08 ~ 10-12(P2 자료 끝과 같음) · 빈 29분 9일은 원판에 두고 스트레스판(kmf_r0q.execute2)을 따로.
python3 research/kmf_comp_w1.py → research/kmf_comp_w1_daily.json(원정밀도 · 결합 입력) · _out.json(표시 · 날별 마지막 정리 분 · 09:45 넘은 정리)"""
import sys, os, json, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import kmf_nb as K
import kmf_r0q as Q
import kmf_hdd_pre as P
EXIT = 585
J15 = {(K.B15[j][0], K.B15[j][1]): j for j in range(len(K.B15))}
DIDX = {d: i for i, d in enumerate(K.DAYS)}

# 날봉 ATR(날 폭 EMA14) · 날 종가 EMA10 · EMA20 — 그날 앞 날까지만
DAILY = {}
e10 = e20 = a = None
for d in K.DAYS:
    DAILY[d] = (e10, e20, a)                              # d 시작 때 알려진 값(전날까지)
    x = K.BY[d]; c = K.last_close(d); rng = max(r[3] for r in x.values()) - min(r[4] for r in x.values())
    e10 = c if e10 is None else e10 + (c - e10) * 2 / 11; e20 = c if e20 is None else e20 + (c - e20) * 2 / 21
    a = rng if a is None else a + (rng - a) * 2 / 15

def prev_day(d):
    i = DIDX[d]; return K.DAYS[i - 1] if i > 0 else None

def bar(d, m):
    j = J15.get((d, m));
    if j is None: return None
    b = K.B15[j]; e1, at = K.E10[j]; e2 = K.E20[j][0]
    sl = (e2 - K.E20[j - 4][0]) if j >= 4 else 0.0
    return dict(o=b[2], h=b[3], l=b[4], c=b[5], e10=e1, e20=e2, atr=at, sl=sl, j=j)

def gap_units(d):
    p = prev_day(d); da = DAILY[d][2]
    if p is None or not da: return None
    o = K.BY[d].get(540)
    if o is None: return None                             # 09:00 첫 분이 없으면 갭 모름
    return (o[2] - K.last_close(p)) / da

# ---------- 신호 ----------
def v_gap_fade(d, k, s=1.0):
    """갭 되돌림: |갭| ≥ k×날ATR · 09:15 15분 종가가 아직 갭 쪽으로 EMA10 바깥(위 갭이면 종가 > EMA10) → 반대로 · 목표 = 전날 종가."""
    g = gap_units(d); b = bar(d, 555)
    if g is None or b is None or abs(g) < k: return []
    side = -1 if g > 0 else 1
    if not ((b["c"] > b["e10"]) if g > 0 else (b["c"] < b["e10"])): return []
    return [(555, side, K.last_close(prev_day(d)), s * b["atr"], EXIT)]

def v_gap_follow(d, k, s=1.0):
    """갭 따라감: |갭| ≥ k×날ATR · 09:15 종가가 갭 방향으로 시가보다 더 가고 EMA10 같은 쪽 → 따라감 · 목표 없음."""
    g = gap_units(d); b = bar(d, 555); o = K.BY[d].get(540)
    if g is None or b is None or abs(g) < k: return []
    up = g > 0
    if not ((b["c"] > o[2] and b["c"] > b["e10"]) if up else (b["c"] < o[2] and b["c"] < b["e10"])): return []
    return [(555, 1 if up else -1, None, s * b["atr"], EXIT)]

def v_band_rev(d, k, s=1.0, flat=None):
    """15분 EMA10 띠 되돌림(R0를 창 안으로): 09:15 · 09:30 종가가 EMA10 ± k×ATR 바깥 → 반대 · 목표 EMA10.
    flat 주면 |EMA20 4봉 기울기|/ATR ≤ flat 일 때만."""
    out = []
    for m in (555, 570):
        b = bar(d, m)
        if b is None or b["atr"] <= 0: continue
        if flat is not None and abs(b["sl"]) / b["atr"] > flat: continue
        if abs(b["c"] - b["e10"]) >= k * b["atr"]: out.append((m, -1 if b["c"] > b["e10"] else 1, b["e10"], s * b["atr"], EXIT))
    return out

def v_t2(d, s):
    """GPT H1: K.sig_t(T2) 신호 중 봉 끝 555 · 570만 · 첫 유효 신호 1번 · 정리 분 = min(원래, 585)."""
    for (m0, side, tg, sd, mx) in K.sig_t(d, "T2", s=s):
        if m0 in (555, 570): return [(m0, side, tg, sd, min(mx, EXIT))]
    return []

VARIANTS = {"H1 T2 손절 1.0": lambda d: v_t2(d, 1.0), "H1 T2 손절 1.5": lambda d: v_t2(d, 1.5),
            "갭 되돌림 k0.3": lambda d: v_gap_fade(d, 0.3), "갭 되돌림 k0.5": lambda d: v_gap_fade(d, 0.5),
            "띠 되돌림 k1.0 평평": lambda d: v_band_rev(d, 1.0, flat=0.5), "띠 되돌림 k1.5 평평": lambda d: v_band_rev(d, 1.5, flat=0.5)}
DAYS = [d for d in K.DAYS if "20260108" <= d <= "20261012"]

def main():
    data_sha = {str(q.relative_to(HERE.parent)): hashlib.sha256(q.read_bytes()).hexdigest() for q in (K.MINI, K.FUT, K.F1M)}
    if not K.CUT: assert data_sha == P.DATA_EXPECT
    daily, exits = {}, {}
    for name, f in VARIANTS.items():
        for mode in ("원판", "스트레스판"):
            p, ex = {}, {}
            for d in DAYS:
                lg = []; p[d] = Q.execute2(d, f(d), log=lg, stress=(mode == "스트레스판")); ex[d] = max((t["정리분"] for t in lg), default=None)
            daily[f"{name} {mode}"] = p; exits[f"{name} {mode}"] = ex
    meta = {"days": len(DAYS), "first": DAYS[0], "last": DAYS[-1], "data_sha256": data_sha, "KMF_CUT": K.CUT,
            "code_sha256": {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in ("kmf_comp_w1.py", "kmf_r0q.py", "kmf_nb.py", "kmf_rlk4.py")}}
    sfx = os.getenv("KMF_OUT_SUFFIX", "")
    # 계산용 날별 값은 반올림 없이(원정밀도 · GPT #343 A) · 표시용만 반올림
    (HERE / f"kmf_comp_w1_daily{sfx}.json").write_text(json.dumps(daily, ensure_ascii=False))
    late = {k: {d: m for d, m in ex.items() if m is not None and m > EXIT} for k, ex in exits.items()}
    (HERE / f"kmf_comp_w1_out{sfx}.json").write_text(json.dumps({"meta": meta, "단독 합(표시)": {k: round(sum(p.values()), 2) for k, p in daily.items()},
        "마지막 정리 분(날별)": exits, "09:45 넘어 정리된 날": late, "가장 늦은 정리 분": {k: max((m for m in ex.values() if m is not None), default=None) for k, ex in exits.items()}}, ensure_ascii=False, indent=1))
    print({k: round(sum(p.values()), 2) for k, p in daily.items() if k.endswith("원판")})

if __name__ == "__main__":
    main()
