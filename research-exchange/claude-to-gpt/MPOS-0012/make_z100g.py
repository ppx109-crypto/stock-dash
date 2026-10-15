"""z100g.py 만들기(GPT #435 고칠 것 1): 고정 나무 z100.py(9743cb802)를 그대로 읽어 **같은 날 1일봉 매수 배정 한 곳만** 바꿈.
원판: 장부 줄 순서대로 min(want, cash × 0.98)를 차례로 배정 → 현금이 모자라면 앞줄(= 판 날이 빠른 줄)이 먼저 받음(미래 의존).
바꾼 판: 그날 1일봉 매수를 묶어 want 합으로 한 번 make_room → 쓸 수 있는 돈(현금 × 0.98 · 현금 ÷ 증거금 · 계좌 흔들림 상한 여유)을
want 비율대로 똑같이 나눔(× 0.995 여유) → 줄 순서 · 판 날 · 손익 · 부분 청산 나눔과 무관. 그 밖의 코드는 한 글자도 안 바꿈(ROOT만 고정 나무로)."""
import hashlib
import sys
from pathlib import Path

TREE = Path("/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/m54tree")
SRC = TREE / "research/z100.py"
SRC_SHA = "47b85d2aee5743db81aa82166581156480801f5ab492df1a74c367f0ce28840d"
OLD_ROOT = 'ROOT = Path(__file__).resolve().parents[1]\n'
NEW_ROOT = 'ROOT = Path("%s")   # z100g: 고정 나무\n' % TREE
OLD = '''        for tag, k, c, s in buys.get(d, []):
            if tag != "1d":
                continue
            want = total() * SHARE * s / 10
            if D1_VOL > 0:
                held1 = sum(p["val"] for p in pos.values() if p["bot"] == "1d")
                want = max(0.0, min(want, allowed * total() * SHARE - held1))
                if want <= 0:
                    continue
            make_room(want, d)
            got = buy((tag, k), "1d", c, d, min(want, cash * 0.98))
            if got:
                pos[(tag, k)]["entry"] = pos[(tag, k)]["val"]
            if got < want * 0.99:
                missed["1d"] += (want - got) / total()
                missed_n["1d"] += 1
'''
NEW = '''        assert D1_VOL == 0, "z100g: 1일봉 흔들림 상한은 지원 안 함"
        grp = [(tag, k, c, total() * SHARE * s / 10) for tag, k, c, s in buys.get(d, []) if tag == "1d"]   # z100g: 그날 1일봉 매수 묶음
        need = sum(w for _, _, c, w in grp if price(c, d))
        if need > 0:
            make_room(need, d)
            room = min(cash * 0.98, cash / MARGIN)
            if ACC_VOL > 0:
                room = min(room, max(0.0, acc_allowed * total() - sum(p["val"] for p in pos.values())))
            ratio = min(1.0, room * 0.995 / need)
            for tag, k, c, want in grp:
                got = buy((tag, k), "1d", c, d, want * ratio)
                if got:
                    pos[(tag, k)]["entry"] = pos[(tag, k)]["val"]
                if got < want * 0.99:
                    missed["1d"] += (want - got) / total()
                    missed_n["1d"] += 1
'''


def make(out):
    s = SRC.read_text(encoding="utf-8")
    assert hashlib.sha256(s.encode()).hexdigest() == SRC_SHA
    assert s.count(OLD) == 1 and s.count(OLD_ROOT) == 1
    Path(out).write_text(s.replace(OLD, NEW).replace(OLD_ROOT, NEW_ROOT), encoding="utf-8")


if __name__ == "__main__":
    make(sys.argv[1])
