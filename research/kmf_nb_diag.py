"""RLK-0003 진단(새 설정 없음 · RLK-0002 round 2 고정 판 · 지연 0 거래 장부만 씀).
1) T2 s1.5 · 조용하지 않은 날(q0.6): 상위 5일 / 나머지 날 · 비용 전 / 뒤 · 진입 때 완결 15분 RNA 상태(EMA10−EMA20 ÷ ATR 칸 · EMA20 4봉 기울기 ÷ ATR 칸) · 사유별 · 달별 거래 수
2) 같은 판 거래 전이: 한 날 두 번째 거래 · 손절 뒤 재진입
3) R0 · 자체 조용 q0.6: 앞 / 뒤 반 거래 수 · 평균 · 사유별(목표 · 손절 · 15:15) · 진입 때 이격 크기 칸
python3 research/kmf_nb_diag.py → research/kmf_nb_diag.json"""
import json, sys, collections, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "research"))
import kmf_nb as K
TR = json.loads((ROOT / "research/kmf_nb_trades.json").read_text())
J = {(K.B15[j][0], K.B15[j][1]): j for j in range(len(K.B15))}
def state(t):
    j = J[(t["d"], t["신호분"])]; e10, a = K.E10[j]; e20 = K.E20[j][0]; sl = e20 - K.E20[j - 4][0]
    gap = abs(e10 - e20) / a if a else 0; slo = abs(sl) / a if a else 0; dis = abs(K.B15[j][5] - e10) / a if a else 0
    return {"배열 칸": "≤0.5" if gap <= 0.5 else ("0.5~1.5" if gap <= 1.5 else ">1.5"), "기울기 칸": "≤0.5" if slo <= 0.5 else ("0.5~1.5" if slo <= 1.5 else ">1.5"),
            "이격 칸": "≤1.5" if dis <= 1.5 else ("1.5~2.5" if dis <= 2.5 else ">2.5"), "ATR": round(a, 2)}
def grp(ts, key):
    g = collections.defaultdict(list)
    for t in ts: g[key(t)].append(t["손익"])
    return {k: {"건": len(v), "합": round(sum(v), 1), "비용 전 합": round(sum(v) + 0.08 * len(v), 1), "평균": round(st.mean(v), 2), "이긴": sum(1 for x in v if x > 0)} for k, v in sorted(g.items())}
out = {}
T2 = TR["T2_s1.5 · 조용하지 않은 날(q0.6)"]
day = collections.defaultdict(float)
for t in T2: day[t["d"]] += t["손익"]
top5 = set(sorted(day, key=day.get, reverse=True)[:5])
for t in T2: t.update(state(t))
out["T2"] = {"상위5일": sorted(top5), "상위5일/나머지": grp(T2, lambda t: "상위5일" if t["d"] in top5 else "나머지"),
             "나머지 · 반": grp([t for t in T2 if t["d"] not in top5], lambda t: "앞(~05-29)" if t["d"] < "20260601" else "뒤(06-01~)"),
             "나머지 · 사유": grp([t for t in T2 if t["d"] not in top5], lambda t: t["사유"]),
             "나머지 · 배열 칸": grp([t for t in T2 if t["d"] not in top5], lambda t: t["배열 칸"]),
             "나머지 · 기울기 칸": grp([t for t in T2 if t["d"] not in top5], lambda t: t["기울기 칸"]),
             "달별": grp(T2, lambda t: t["d"][4:6]),
             "그날 몇 번째": grp(T2, lambda t: sum(1 for u in T2 if u["d"] == t["d"] and u["진입분"] < t["진입분"]) + 1),
             "손절 뒤 재진입": grp([t for t in T2 if any(u["d"] == t["d"] and u["정리분"] <= t["진입분"] and u["사유"] == "손절" for u in T2)], lambda t: "손절 뒤")}
R = TR["R0 · 자체 조용 q0.6"]
for t in R: t.update(state(t))
out["R0_q0.6"] = {"반": grp(R, lambda t: "앞(~05-29)" if t["d"] < "20260601" else "뒤(06-01~)"),
                  "반 · 사유": grp(R, lambda t: ("앞" if t["d"] < "20260601" else "뒤") + " · " + t["사유"]),
                  "반 · 이격 칸": grp(R, lambda t: ("앞" if t["d"] < "20260601" else "뒤") + " · " + t["이격 칸"]),
                  "반 · ATR 평균": {h: round(st.mean(t["ATR"] for t in R if (t["d"] < "20260601") == (h == "앞")), 2) for h in ("앞", "뒤")}}
(ROOT / "research/kmf_nb_diag.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=0)[:6000])
