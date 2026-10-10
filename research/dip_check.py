"""evals.jsonl에서 판 결과를 꺼내 accept()로 견줌(셈 없음). python3 research/dip_check.py 후보판 채택판 [removal]"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash/research")
LOG = Path("/home/user/stock-dash/research-exchange/claude-to-gpt/DIP-DEEP-0042/evals.jsonl")


def res(tag):
    got = [json.loads(x) for x in LOG.read_text(encoding="utf-8").splitlines() if x.strip()]
    done = [g for g in got if g.get("status") == "DONE" and g["tag"] == tag]
    return done[-1]["res"]


def accept(cand, inc, removal=False):
    # dip_dev.accept와 같은 식(스냅샷을 읽지 않으려고 옮겨 둠)
    why = {}
    for h in ("D1", "D2"):
        c, i = cand.get(h), inc.get(h)
        if not c or not i:
            why[h] = "결과 없음"
            continue
        w = max(c["폭"], i["폭"])
        d = c["연수익"] - i["연수익"]
        slack = w if removal else 0
        why[h] = [c["매매"] >= 60, (d >= -w) if removal else (d > w),
                  c["행운뺌"] >= i["행운뺌"] - slack and c["큰2건뺌"] >= i["큰2건뺌"] - slack]
    return all(isinstance(v, list) and all(v) for v in why.values()), why


if __name__ == "__main__":
    a, b = sys.argv[1], sys.argv[2]
    print(a, "대", b, accept(res(a), res(b), removal=len(sys.argv) > 3))
