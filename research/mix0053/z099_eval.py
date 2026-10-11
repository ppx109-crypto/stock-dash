"""MAXRET-0026 판정 — z092_eval.stats 그대로로 여섯 판 앞 · 뒤 반 숫자를 세고, 사전등록대로 앞 반(하루 · 달 > −7.5%)에서 고르고 뒤 반(> −15% · m1보다 연복리 높음)에서 시험.
python3 research/z099_eval.py <판 CSV 폴더> <자르기 CSV>
round 2(GPT #157 6090910926): 기준 맞춤은 일별 NAV 전체(날짜 집합 · 행 수 · 상대 차 1e-9) · 자르기는 full의 T까지 앞부분과 일대일(순서 · 고유 · 행 수 · 마지막 날 · 상대 차)."""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash/research")
from z092_eval import BACK, FRONT, load, stats  # noqa: E402

ORDER = ["m1", "m2", "m2.5", "m3", "m4", "off"]
T = "20231231"
R = "/home/user/stock-dash/research-exchange/claude-to-gpt/"
REF = {"m1": R + "ACC-IMPROVE-0016/evidence/nav/F.csv",                      # blob 1a5e7c94
       "m2": R + "ACC-IMPROVE-0014/evidence/nav/cap0_park0_m2.0.csv"}       # blob 877d66fc


def same_path(a, b):
    """두 일별 NAV 줄이 날짜 순서 · 고유 · 행 수 · 값(상대 차 1e-9)까지 같은지. 돌려줌: (같음, 첫 다른 날 또는 까닭)."""
    da, db = [d for d, _ in a], [d for d, _ in b]
    if da != sorted(set(da)) or db != sorted(set(db)):
        return False, "날짜가 정렬 · 고유가 아님"
    if len(a) != len(b):
        return False, f"행 수 {len(a)} ≠ {len(b)}"
    for (d1, v1), (d2, v2) in zip(a, b):
        if d1 != d2:
            return False, f"날짜 {d1} ≠ {d2}"
        if abs(v1 / v2 - 1) >= 1e-9:
            return False, d1
    return True, None
MULT = {"m1": 1, "m2": 2, "m2.5": 2.5, "m3": 3, "m4": 4, "off": float("inf")}


def main():
    folder, cut = Path(sys.argv[1]), sys.argv[2]
    navs = {k: load(folder / f"{k}.csv") for k in ORDER}
    out = {k: {"front": stats(v, *FRONT), "back": stats(v, *BACK)} for k, v in navs.items()}
    for k, ref in REF.items():
        ok_, why = same_path(navs[k], load(ref))
        out[f"check_{k}_same_as_ref"], out[f"check_{k}_first_diff"] = ok_, why
    ok = [k for k in ORDER if out[k]["front"]["worst_day"] > -7.5 and out[k]["front"]["worst_month"] > -7.5]
    pick = max(ok, key=lambda k: (out[k]["front"]["cagr"], -MULT[k])) if ok else None
    out["front_ok"], out["pick"] = ok, pick
    if pick:
        b = out[pick]["back"]
        out["pass_limits"] = b["worst_day"] > -15 and b["worst_month"] > -15
        out["pass_beats_m1"] = b["cagr"] > out["m1"]["back"]["cagr"]
    if pick:
        full = [(d, v) for d, v in navs[pick] if d <= T]
        part = load(cut)
        ok_, why = same_path(part, full)
        out["cut_rows"], out["cut_last"], out["full_prefix_last"] = len(part), part[-1][0] if part else None, full[-1][0]
        out["cut_ok"], out["cut_first_diff"] = ok_ and bool(part) and part[-1][0] == full[-1][0], why
    checks = out["check_m1_same_as_ref"] and out["check_m2_same_as_ref"] and out.get("cut_ok", False)
    out["verdict"] = "판정 보류" if not (checks and pick) else ("PASS" if out["pass_limits"] and out["pass_beats_m1"] else "FAIL")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
