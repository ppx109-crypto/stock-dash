"""1일봉 원판 장부에 갈래(규칙 · 정배열) 붙이기(진단 · 결정 안 바꿈): ex21 BASE와 같은 lab.run 호출 → 매매마다 nrl.tier(산 날 후보 줄).
cwd = 고정 나무 · tree_run. 출력: EX_OUT json [(코드, 산 날, 판 날, 손익, 자리, 갈래, 들고)]"""
import json, os, sys
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), "research"))
import lab  # noqa: E402
import nrl  # noqa: E402
import rule  # noqa: E402
out = []
for side, pool, since in (("앞", nrl.early, rule.SINCE), ("뒤", nrl.inside, rule.MID)):
    g = lab.run(pool, nrl.prices, nrl.BASE_HOLD, nrl.BASE_EXIT, slots=nrl.SLOTS, rank=rule.order, since=since, apart=nrl.kin, realistic=True, cap=130,
                detail=True, size=nrl.BASE_SIZE)
    for t in g["매매목록"]:
        out.append((t["code"], t["산 날"], t["판 날"], t["손익"], t["자리"] if t.get("자리") is not None else 1, nrl.tier(t["행"]), t["들고"]))
json.dump(out, open(os.environ["EX_OUT"], "w"), ensure_ascii=False)
print(len(out))
