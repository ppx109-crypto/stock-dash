"""MPOS-0009 ⓐ 진단(고르기 · 판정 없음 · GPT #426): P0 계좌 '기여'(독립 봇 수익 아님 · MPOS-0001 귀속 비율 배분)를
달마다 복리 연결(일별 기여 c_b,d → 그달 기여 = Σ_d c_b,d × 그날 전까지 그달 누적(1+R))하고 잔차를 보고.
① 114달 · 앞(~2021-12) · 뒤(2022-01~) 상관 ② P0 손실 달의 동반 손실(그달 기여 < 0 인 봇 수) · 하방 기여 ③ 실제 음수 비율 · 연속 길이 · 해마다
④ 6달 묶음 이어뽑기(2000번 · 씨앗 20261016 · 보기 전에 고정)로 달 μ/σ · 손실 비율 90% 구간."""
import json, sys, math, random, statistics as S, collections
d = json.load(open(sys.argv[1]))["day"]
B = ("add", "1d", "basket", "engine", "inverse")
mon = collections.defaultdict(lambda: {"R": 0.0, **{b: 0.0 for b in B}, "날": 0})
for k in sorted(d):
    v = d[k]; m = mon[k[:6]]; g = 1 + m["R"]
    for b in B: m[b] += v[b] * g
    m["R"] = g * (1 + v["r"]) - 1; m["날"] += 1
M = [m for m in sorted(mon) if "201703" <= m <= "202608"]
out = {"달": len(M), "복리 연결 잔차(R − Σ기여) 최대 절대 %p": max(abs(mon[m]["R"] - sum(mon[m][b] for b in B)) for m in M) * 100}
def corr(x, y):
    mx, my = S.mean(x), S.mean(y); sx = math.sqrt(sum((a - mx) ** 2 for a in x)); sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx and sy else None
for nm, ms in (("114달", M), ("앞", [m for m in M if m <= "202112"]), ("뒤", [m for m in M if m >= "202201"])):
    out[f"기여 상관 · {nm}"] = {f"{a}~{b}": round(corr([mon[m][a] for m in ms], [mon[m][b] for m in ms]), 3) for i, a in enumerate(B) for b in B[i + 1:]}
    out[f"기여 달 평균 · σ · 비 · {nm}"] = {b: [round(S.mean(mon[m][b] for m in ms) * 100, 3), round(S.stdev(mon[m][b] for m in ms) * 100, 3), round(S.mean(mon[m][b] for m in ms) / S.stdev(mon[m][b] for m in ms), 3)] for b in B}
loss = [m for m in M if mon[m]["R"] < 0]
out["손실 달 동반 손실(기여 < 0인 봇 수) 분포"] = dict(collections.Counter(sum(mon[m][b] < 0 for b in B) for m in loss))
out["손실 달 하방 기여 합 %p"] = {b: round(sum(min(0, mon[m][b]) for m in loss) * 100, 2) for b in B}
neg = [mon[m]["R"] < 0 for m in M]; runs, c = [], 0
for x in neg:
    c = c + 1 if x else 0
    if x: runs.append(c)
out["실제 음수 비율 · 앞 · 뒤"] = [sum(neg) / len(M), sum(mon[m]["R"] < 0 for m in M if m <= "202112") / 58, sum(mon[m]["R"] < 0 for m in M if m >= "202201") / 56]
out["가장 긴 연속 손실 달"] = max(runs) if runs else 0
out["해마다 손실 달"] = dict(collections.Counter(m[:4] for m in loss))
R = [mon[m]["R"] for m in M]; rnd = random.Random(20261016); mu_s, lr = [], []
for _ in range(2000):
    idx = []
    while len(idx) < len(R):
        s = rnd.randrange(len(R) - 6 + 1); idx += range(s, s + 6)
    x = [R[i] for i in idx[:len(R)]]; mu_s.append(S.mean(x) / S.stdev(x)); lr.append(sum(v < 0 for v in x) / len(x))
q = lambda v, p: sorted(v)[int(p * (len(v) - 1))]
out["6달 묶음 이어뽑기 90%"] = {"달 μ/σ": [q(mu_s, .05), q(mu_s, .95)], "손실 비율": [q(lr, .05), q(lr, .95)], "묶음": 6, "횟수": 2000, "씨앗": 20261016}
x = R; m_, s_ = S.mean(x), S.stdev(x)
out["왜도 · 첨도(초과) · 1차 자기상관"] = [sum(((v - m_) / s_) ** 3 for v in x) / len(x), sum(((v - m_) / s_) ** 4 for v in x) / len(x) - 3, corr(x[:-1], x[1:])]
print(json.dumps(out, ensure_ascii=False, indent=1))
