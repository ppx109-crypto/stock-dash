"""KMF-0015 합성 시험."""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf15 as M  # noqa: E402
import kmf as K  # noqa: E402
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


def mkday(d, path):
    """5분봉 76개(이름 544 ~ 919) · path(봉 번호 → 종가) · 시가 = 앞 봉 종가."""
    rows, prev = [], 100.0
    for j in range(76):
        cl = path(j); rows.append((d, 544 + 5 * j, prev, max(prev, cl) + 0.1, min(prev, cl) - 0.1, cl, 1)); prev = cl
    return rows


inv = {r["date"]: r["개인"] for r in json.loads(M.FLOW.read_text())["rows"]}
days = sorted(d for d in inv if d >= "20260105")[:40]
bias = M.flow_bias(days)
dpos = next(d for d in days if bias.get(d) == 1)
dneg = next(d for d in days if bias.get(d) == -1)
up = lambda j: 100 + 0.5 * j                                                     # 꾸준히 오름
cfg = M.grid()[0]
w = M.signals(mkday(dpos, up), cfg)
# 09:05 창: 앞 30분 = 봉 549(1번) ~ 574(6번) · 들기 판단 봉 574(6번) · 정리 판단 봉 604(12번)
chk("1 오름 쪽 날 · 오르는 앞 30분 → 6번 봉에서 삼", w[6] == 1)
chk("2 60분째 봉에서 정리 또는 다음 창으로 이어 삼(0 또는 1)", w[12] in (0, 1))
w = M.signals(mkday(dneg, up), cfg)
chk("3 내림 쪽 날에는 오르는 창에서 안 삼(수급 거름)", all(x != 1 for x in w[:60]))
w0 = M.signals(mkday(dneg, up), M.grid()[2])
chk("4 거름 끈 칸(flow0)은 내림 쪽 날에도 삼", w0[6] == 1)
dn = lambda j: 100 - 0.5 * j
w = M.signals(mkday(dneg, dn), cfg)
k845 = (845 + 29 - 544) // 5                                                    # 14:05 되돌림 창 들기 판단 봉
chk("5 14:05 되돌림 창: 내리는 앞 30분이면 삼(반대) → 내림 쪽 날이라 거름에 막힘", w[k845] in (None, 0))
w = M.signals(mkday(dpos, dn), cfg)
chk("6 오름 쪽 날 · 14:05 창 내리는 앞 30분 → 되돌림으로 삼", w[k845] == 1)
import tempfile, os
raw = json.loads(M.FLOW.read_text())
for r in raw["rows"]:
    if r["date"] >= dpos:
        r["개인"] = -r["개인"] * 1000                                              # 그날과 뒤 값을 엉터리로
tmp = Path(tempfile.mkdtemp()) / "inv.json"; tmp.write_text(json.dumps(raw, ensure_ascii=False))
old = M.FLOW; M.FLOW = tmp; M._BIAS.clear()
b_ = M.flow_bias([dpos])
M.FLOW = old; M._BIAS.clear()
chk("7 수급은 그날 앞 거래일 값만(그날 · 뒤 값을 엉터리로 바꿔도 그대로)", b_[dpos] == bias[dpos])
chk("8 하루 멈춤 −25p · 칸 4개 · 잣대 1.94 · 시험 2 잠금 없으면 멈춤", K.DAY_STOP == -25.0 and len(M.grid()) == 4 and M.TEST2_MIN_PER_DAY == 1.94 and not M.TEST2_OK.exists())
chk("9 잠금 통과(수급 파일 포함)", "market-data/investor_KSP.json" in M.verify_inputs())
print(f"모두 통과 {ok}개")
