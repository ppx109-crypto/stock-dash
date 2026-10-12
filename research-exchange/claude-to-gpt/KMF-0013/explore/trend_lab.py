"""KMF-0013 탐색(사용자 2026-10-13: "추세장봇먼저 RNA로 · 앞뒤 잘라서 말고 한번에 다 보고 개발 · 국면 여러 번 봐도 좋음").
전체 자료 2026-01-02 ~ 10-12(10-13부터 시험 2 자료는 안 읽음) · 하루 −25p · 1계약 · 편도 0.04p · 판단 = 봉 종가 · 체결 = 다음 봉 시가.
RNA 추세 봇(N분봉 · 그 봉까지 값만):
  선 5 · 20 · 60 · 120봉 EMA(날 넘어 이어 셈) · 큰 흐름 = 120선 기울기(k봉) · 역추세 금지
  들기: mode 'align' 정배열(5>20>60>120)+기울기 / 'pull' 정배열 중 앞 봉 종가 ≤ 20선 · 이 봉 > 20선(눌림 뒤 다시 섬) / 'box' 정배열 중 지난 B봉 고가 뚫는 종가
  정리: 종가가 exit선(20 · 60) 반대로 마감 · 또는 트레일(들고 난 뒤 최고 종가 − tr × ATR20) · 그날 마지막 봉
  하루 들기 max_n번까지 · 새로 들기 15:00 판단까지"""
import sys, json, itertools
from collections import defaultdict
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K, kmf4 as K4
K.DAY_STOP = -25.0
END = "20261013"


def ema(a, s):
    out = np.empty(len(a)); k = 2 / (s + 1); out[0] = a[0]
    for i in range(1, len(a)):
        out[i] = out[i - 1] + k * (a[i] - out[i - 1])
    out[:s] = np.nan
    return out


BASE_MIN = (25, 100, 300, 600)            # 선 길이(분) = 5분봉 5 · 20 · 60 · 120봉


def spans_for(tf, scale=1.0):
    return tuple(max(2, int(round(m * scale / tf))) for m in BASE_MIN)


def feats(b, spans=(5, 20, 60, 120)):
    c = np.array([r[5] for r in b]); h = np.array([r[3] for r in b]); l = np.array([r[4] for r in b])
    E = dict(zip((5, 20, 60, 120), (ema(c, s) for s in spans)))
    E[240] = ema(c, spans[3] * 2)                                   # 정리선 후보(가장 긴 선의 2배)     # 열쇠는 이름(짧은 선 → 긴 선) · 실제 길이는 spans
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum(np.maximum(h - l, np.abs(h - pc)), np.abs(l - pc))
    atr = np.full(len(c), np.nan)
    for i in range(20, len(c)):
        atr[i] = tr[i - 20:i].mean()                     # 앞 20봉(그 봉 제외)
    return c, h, l, E, atr


def signals(b, cfg, F=None):
    c, h, l, E, atr = F or feats(b)
    n = len(b); want = [None] * n
    k = cfg["sk"]; pos = 0; peak = None; cnt = 0; day = None
    orf, erf, t_from = cfg.get("orf", 0), cfg.get("erf", 0.0), cfg.get("t_from", 0)
    for i in range(n):
        d, m = b[i][0], b[i][1]
        if d != day:
            day, pos, cnt, peak = d, 0, 0, None
            d0, o0, ohi, olo, mv = i, b[i][2], None, None, 0.0     # 그날 시가 · 아침 범위 · 움직임 합(그 봉까지)
            st = m - (cfg["tf"] - 1)
        if m < st + orf:
            ohi = b[i][3] if ohi is None else max(ohi, b[i][3]); olo = b[i][4] if olo is None else min(olo, b[i][4])
        if i > d0:
            mv += abs(c[i] - c[i - 1])
        er_now = abs(c[i] - o0) / mv if mv > 0 else 0.0
        if i < k + 1 or np.isnan(E[120][i - k]) or np.isnan(atr[i]):
            continue
        slope = E[120][i] - E[120][i - k]
        up = E[5][i] > E[20][i] > E[60][i] > E[120][i] and slope > 0
        dn = E[5][i] < E[20][i] < E[60][i] < E[120][i] and slope < 0
        ex = E[cfg["exit"]][i]
        if pos:
            peak = max(peak, c[i]) if pos > 0 else min(peak, c[i])
            out = (pos > 0 and c[i] < ex) or (pos < 0 and c[i] > ex)
            if cfg["tr"]:
                out = out or (pos > 0 and c[i] < peak - cfg["tr"] * atr[i]) or (pos < 0 and c[i] > peak + cfg["tr"] * atr[i])
            if out:
                want[i], pos = 0, 0
            continue
        if m > K.ENTRY_TO or cnt >= cfg["max_n"] or m < t_from or (orf and m < st + orf) or er_now < erf:
            continue
        for side, ok in ((1, up), (-1, dn)):
            if not ok:
                continue
            if cfg["mode"] == "pull":
                trig = side * (c[i - 1] - E[20][i - 1]) <= 0 < side * (c[i] - E[20][i])
            elif cfg["mode"] == "box":
                w = h[i - cfg["B"]:i] if side > 0 else l[i - cfg["B"]:i]
                trig = c[i] > w.max() if side > 0 else c[i] < w.min()
            else:
                trig = True
            if trig and orf and ohi is not None:
                trig = c[i] > ohi if side > 0 else c[i] < olo
            if trig:
                want[i], pos, peak, cnt = side, side, c[i], cnt + 1
                break
    return want


def report(days, trades):
    vals = days; mo = defaultdict(float)
    for d, v in vals.items():
        mo[d[:6]] += v
    eq = pk = mdd = 0.0
    for d in sorted(vals):
        eq += vals[d]; pk = max(pk, eq); mdd = min(mdd, eq - pk)
    return {"total": round(sum(vals.values()), 1), "per_day": round(sum(vals.values()) / len(vals), 2), "trades": len(trades),
            "pos_m": sum(1 for v in mo.values() if v > 0), "worst_m": round(min(mo.values()), 1), "worst_d": round(min(vals.values()), 1),
            "mdd": round(mdd, 1), "months": {k: round(v, 1) for k, v in sorted(mo.items())}}


if __name__ == "__main__":
    rows = K._rows_before(END)
    res = {}
    for tf in (5, 15, 30):
        b = K4.day_start_aligned(rows, tf)
        F = feats(b)
        for mode, ex, trl, sk, mx in itertools.product(("align", "pull", "box"), (20, 60), (0, 3), (3, 6), (1, 3)):
            cfg = {"tf": tf, "mode": mode, "exit": ex, "tr": trl, "sk": sk, "max_n": mx, "B": 8}
            days, tr = K.simulate(b, signals(b, cfg, F))
            res[f"T{tf}_{mode}_x{ex}_t{trl}_s{sk}_n{mx}"] = report(days, tr)
    json.dump(res, open(Path(__file__).with_suffix(".round1.json"), "w"), ensure_ascii=False, indent=0)
    top = sorted(res.items(), key=lambda kv: (-kv[1]["pos_m"], -kv[1]["total"]))[:25]
    for k, v in top:
        print(k, {x: v[x] for x in ("total", "per_day", "trades", "pos_m", "worst_m", "worst_d", "mdd")})
