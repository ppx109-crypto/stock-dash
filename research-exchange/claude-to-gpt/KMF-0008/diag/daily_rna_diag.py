"""KMF-0008 준비 · 판정 밖 진단: 24년 KODEX 200 일봉(etf-ohlc/069500.json · 수정 값)에서 일봉 RNA가 하루 안(시가→종가) · 밤(종가→시가) · 하루(종가→종가) 움직임을 맞히는가.
개발 2003-07 ~ 2014만 씀(2015부터 안 읽음). RNA는 어제 종가까지 값(5 · 20 · 60 · 120선 · 기울기 5일 · 이격밴드 60일)."""
import json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf as K
src = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "etf-ohlc/069500.json")
d = [x for x in json.load(open(src))["adjusted"] if x[0] <= "20141231"]
dt = [x[0] for x in d]; o = np.array([x[1] for x in d]); c = np.array([x[4] for x in d])
f = K.rna(c, (5, 20, 60, 120), slope_k=5, band=60)
st, zz, gp = defaultdict(list), defaultdict(list), defaultdict(list)
big = defaultdict(lambda: [[], [], []])
for i in range(1, len(d)):
    if dt[i] < "20030701":
        continue
    oo, s, z = f["order"][i - 1], f["slope"][i - 1], f["z120"][i - 1]
    if np.isnan(oo) or np.isnan(s):
        continue
    oc = (c[i] / o[i] - 1) * 100
    st[("위" if s > 0 else "아래") + str(int(oo))].append(oc)
    if not np.isnan(z):
        zz["z>1.5" if z > 1.5 else "z<-1.5" if z < -1.5 else "중간"].append(oc)
    gap = (o[i] / c[i - 1] - 1) * 100
    gp["갭 +0.5%↑" if gap > 0.5 else "갭 −0.5%↓" if gap < -0.5 else "갭 작음"].append(oc)
    k = "위3" if (s > 0 and oo == 3) else "아래0" if (s < 0 and oo == 0) else "나머지"
    big[k][0].append(gap); big[k][1].append(oc); big[k][2].append((c[i] / c[i - 1] - 1) * 100)
sm = lambda v: {"days": len(v), "mean_pct": round(float(np.mean(v)), 3), "up_share": round(float(np.mean(np.array(v) > 0)), 3)}
out = {"rna_state_open_to_close": {k: sm(v) for k, v in sorted(st.items())},
       "z120_open_to_close": {k: sm(v) for k, v in sorted(zz.items())},
       "gap_open_to_close": {k: sm(v) for k, v in sorted(gp.items())},
       "night_day_full_by_state": {k: {"night_mean_pct": round(float(np.mean(v[0])), 3), "day_mean_pct": round(float(np.mean(v[1])), 3),
                                       "close_to_close_mean_pct": round(float(np.mean(v[2])), 3), "days": len(v[0])} for k, v in big.items()}}
print(json.dumps(out, ensure_ascii=False, indent=1))
