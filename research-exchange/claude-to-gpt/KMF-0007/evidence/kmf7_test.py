"""KMF-0007 시험(손익 셈 없음)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import kmf7 as K7  # noqa: E402
ok = 0


def chk(name, cond):
    global ok
    if not cond:
        print("실패:", name); sys.exit(1)
    ok += 1; print("통과:", name)


c = K7.cfg()
chk("1 칸은 KMF-0005 N60_day_e1 그대로(60분 범위 · −12p만 · 하루 1번 · RNA 거름 없음)",
    c == {"bot": "ORB15", "or": 60, "stop": "day", "max_entries": 1, "rna": False, "tag": "N60_day_e1"})
k5 = json.loads((ROOT / "research-exchange/claude-to-gpt/KMF-0005/evidence/dev_rows.json").read_text())
chk("2 KMF-0005 결과에 같은 칸 · 개발 +202.76p(이미 공개된 값)", k5["N60_day_e1"]["cfg"] == c and k5["N60_day_e1"]["dev"]["total_p"] == 202.76)
chk("3 잠금 통과", bool(K7.verify_inputs()))
print(f"모두 통과 {ok}개")
