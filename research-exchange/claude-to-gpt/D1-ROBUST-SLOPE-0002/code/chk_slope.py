# 자료 맞춤 점검(엔진 시험 아님): 일봉 줄(lanes)로 다시 센 180일 EMA 5일 기울기가 표의 '추세 기울기'와 같은지
import sys, random
sys.path.insert(0, "/home/user/stock-dash")
import lab, nrl
ema = {}
def slope(code, day, step):
    if code not in ema:
        ema[code] = lab.ema_series(nrl.lanes[code]["closes"], 180)
    d = nrl.lanes[code]["날"]; i = d.index(day); e = ema[code]
    if i < step or e[i] is None or not e[i - step]: return None
    return (e[i] / e[i - step] - 1) * 100
random.seed(0)
rows = [r for r in nrl.inside if r.get("추세 기울기") is not None]
smp = random.sample(rows, 3000)
diffs = []; miss = 0
for r in smp:
    if r["code"] not in nrl.lanes or r["date"] not in nrl.lanes[r["code"]]["날"]: miss += 1; continue
    s = slope(r["code"], r["date"], 5)
    if s is None: miss += 1; continue
    diffs.append(abs(s - r["추세 기울기"]))
diffs.sort()
n = len(diffs)
print("표본", n, "못 셈", miss, "가운데 차", round(diffs[n//2], 5), "99% 차", round(diffs[int(n*.99)], 4), "최대 차", round(diffs[-1], 4),
      "0.01 넘는 몫", round(sum(x > 0.01 for x in diffs) / n, 4))
