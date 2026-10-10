"""DIP-DEEP-0042 round 3 합성 시험 — 평가 기록(STARTED · FAILED · DONE) · 받아들이는 식(낙폭 없음) · 토막 끝 정산 · 끝 날 안 삼.
엔진 성과는 셈하지 않음(run_way를 가짜로 바꿔 끼움). python3 evidence/dev_test.py"""
import json, os, sys, tempfile
from pathlib import Path
tmp = Path(tempfile.mkdtemp()) / "evals.jsonl"
os.environ["DIP_EVAL_LOG"] = str(tmp)
sys.path.insert(0, "/home/user/stock-dash/research")
import dip_dev as D
fails = []
def ok(c, m):
    print(("통과 " if c else "실패 ") + m)
    if not c: fails.append(m)
# 1) 평가 기록: 가짜 run_way
D.run_way = lambda *a, **k: {"D1": {"x": 1}, "D2": {"x": 2}}
D.evaluate("가짜1", None, None)
def boom(*a, **k): raise RuntimeError("일부러 낸 오류")
D.run_way = boom
try:
    D.evaluate("가짜2", None, None)
except RuntimeError:
    pass
recs = [json.loads(x) for x in tmp.read_text().splitlines()]
ok([r["status"] for r in recs] == ["STARTED", "DONE", "STARTED", "FAILED"], "STARTED → DONE · STARTED → FAILED 순서로 기록")
ok(recs[2]["n"] == recs[3]["n"] == 2 and D._started() == 2, "실패한 판도 같은 번호로 남고 상한 셈(STARTED)에 들어감")
with tmp.open("a") as fh: fh.write(json.dumps({"n": 3, "status": "STARTED", "tag": "중단"}) + "\n")
ok(D._started() == 3, "끝 표시 없이 중단된 판(STARTED만)도 셈")
D.EVAL_CAP = 3
try:
    D.evaluate("넘침", None, None); ok(False, "상한 넘으면 멈춰야 함")
except SystemExit as e:
    ok("상한" in str(e), "상한(여기선 3) 다 쓰면 셈 없이 멈춤")
# 2) 받아들이는 식(낙폭 없음)
inc = {"D1": {"매매": 100, "연수익": 10.0, "폭": 2.0, "행운뺌": 5.0, "큰2건뺌": 4.0, "최대낙폭": -10, "골 폭": 1},
       "D2": {"매매": 100, "연수익": 10.0, "폭": 2.0, "행운뺌": 5.0, "큰2건뺌": 4.0, "최대낙폭": -10, "골 폭": 1}}
c = json.loads(json.dumps(inc)); c["D1"]["연수익"] = c["D2"]["연수익"] = 12.5; c["D1"]["최대낙폭"] = c["D2"]["최대낙폭"] = -40
ok(D.accept(c, inc)[0], "연수익 차 2.5 > 폭 2 · 행운뺌 같음이면 받아들임(낙폭 −40이어도 · 낙폭은 보고만)")
c["D2"]["연수익"] = 12.0
ok(not D.accept(c, inc)[0], "D2 차 2.0은 폭 2보다 크지 않아 거절")
c["D2"]["연수익"] = 12.5; c["D1"]["행운뺌"] = 4.99
ok(not D.accept(c, inc)[0], "행운뺌이 줄면 거절")
r = json.loads(json.dumps(inc)); r["D1"]["연수익"] = r["D2"]["연수익"] = 8.0; r["D1"]["행운뺌"] = 3.0
ok(D.accept(r, inc, removal=True)[0], "덜어냄: 연수익 −2(= −폭) · 행운뺌 −2까지는 받아들임")
r["D1"]["연수익"] = 7.99
ok(not D.accept(r, inc, removal=True)[0], "덜어냄: −2.01이면 거절")
c2 = json.loads(json.dumps(inc)); c2["D1"]["매매"] = 59; c2["D1"]["연수익"] = c2["D2"]["연수익"] = 20
ok(not D.accept(c2, inc)[0], "매매 59건이면 거절")
# 3) 토막 끝 정산 · 끝 날 안 삼
lane = {"closes": [100, 101, 102, 103]}
never = lambda *a: False
go = D.settle(never)
ok(go(lane, 0, 100, 2, 102) is False and go(lane, 0, 100, 3, 103) is True, "줄의 마지막 칸(토막 끝)에서만 정산해 팖")
h = D.no_last_day(lambda r: True, "20191230")
ok(h({"date": "20191227"}) and not h({"date": "20191230"}), "토막 끝 날에는 새로 사지 않음")
p, lanes, _ = D.seg("D1")
ok(max(d for b in p.values() for d, _ in b["rows"]) <= D.D1[1], "D1 토막 일봉은 2019-12-30까지로 잘림")
ok(all(not v[0] or v[0][-1] <= D.CUT for v in D.FLOW.values()) and D.IXD[-1] <= D.CUT, "수급 · 069500도 CUT까지")
print(f"합계: 실패 {len(fails)}"); sys.exit(1 if fails else 0)
