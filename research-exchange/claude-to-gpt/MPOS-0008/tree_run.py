"""고정 나무 실행기(GPT #421 지적 3 · 잠금 경계): 고정 나무(9743cb802)의 nrl.py · ntools.py가 sys.path 앞에 넣는 바깥 작업 복사본
(/home/user/stock-dash)을 고정 나무로 바꿔 넣고, 끝날 때 실제로 불러온 모듈 파일 · sha256을 영수증으로 남김. 고정 나무 밖 연구 코드를 불러오면 실패.
python3 tree_run.py <영수증 json> <스크립트> [인자...]   (cwd = 고정 나무)"""
import atexit
import hashlib
import json
import os
import runpy
import sys

TREE = os.path.realpath("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/m54tree")
OUTSIDE = os.path.realpath("/home/user/stock-dash")
HERE = os.path.dirname(os.path.realpath(__file__))


class GuardedPath(list):
    def _fix(self, p):
        rp = os.path.realpath(str(p))
        if rp == OUTSIDE or rp.startswith(OUTSIDE + os.sep):
            return TREE + rp[len(OUTSIDE):]
        return p

    def insert(self, i, p):
        super().insert(i, self._fix(p))

    def append(self, p):
        super().append(self._fix(p))


def audit(receipt):
    used, bad = {}, []
    for name, m in sorted(sys.modules.items()):
        f = getattr(m, "__file__", None)
        if not f:
            continue
        rf = os.path.realpath(f)
        if rf.startswith(TREE + os.sep) or rf.startswith(HERE + os.sep):
            used[name] = [rf.replace(TREE, "TREE").replace(HERE, "HERE"), hashlib.sha256(open(rf, "rb").read()).hexdigest()]
        elif rf.startswith(OUTSIDE + os.sep) or "/scratchpad/" in rf:
            bad.append(rf)
    json.dump({"모듈": used, "바깥": bad, "sys.path 앞": [p.replace(TREE, "TREE") for p in list(sys.path)[:6]]},
              open(receipt, "w"), ensure_ascii=False, indent=1)
    if bad:
        sys.stderr.write(f"고정 나무 밖 코드 불러옴 → 실패: {bad}\n")
        os._exit(3)


if __name__ == "__main__":
    receipt, script = sys.argv[1], sys.argv[2]
    sys.argv = [script] + sys.argv[3:]
    sys.path[:] = [p for p in sys.path if not os.path.realpath(p or ".").startswith(OUTSIDE)]
    sys.path = GuardedPath(sys.path)
    sys.path.insert(0, os.path.dirname(os.path.realpath(script)))
    atexit.register(audit, receipt)
    runpy.run_path(script, run_name="__main__")
