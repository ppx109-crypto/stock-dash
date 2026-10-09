"""MAXRET-0026 판정 — z092_eval.stats 그대로로 여섯 판 앞 · 뒤 반 숫자를 세고, 사전등록대로 앞 반(하루 · 달 > −7.5%)에서 고르고 뒤 반(> −15% · m1보다 연복리 높음)에서 시험.
python3 research/z099_eval.py <판 CSV 폴더> <자르기 CSV 또는 ->"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash/research")
from z092_eval import BACK, FRONT, load, stats  # noqa: E402

ORDER = ["m1", "m2", "m2.5", "m3", "m4", "off"]
MULT = {"m1": 1, "m2": 2, "m2.5": 2.5, "m3": 3, "m4": 4, "off": float("inf")}


def main():
    folder, cut = Path(sys.argv[1]), sys.argv[2]
    navs = {k: load(folder / f"{k}.csv") for k in ORDER}
    out = {k: {"front": stats(v, *FRONT), "back": stats(v, *BACK)} for k, v in navs.items()}
    out["check_m1_back_23.44"] = out["m1"]["back"]["cagr"] == 23.44
    out["check_m2_back_33.83"] = out["m2"]["back"]["cagr"] == 33.83
    ok = [k for k in ORDER if out[k]["front"]["worst_day"] > -7.5 and out[k]["front"]["worst_month"] > -7.5]
    pick = max(ok, key=lambda k: (out[k]["front"]["cagr"], -MULT[k])) if ok else None
    out["front_ok"], out["pick"] = ok, pick
    if pick:
        b = out[pick]["back"]
        out["pass_limits"] = b["worst_day"] > -15 and b["worst_month"] > -15
        out["pass_beats_m1"] = b["cagr"] > out["m1"]["back"]["cagr"]
    if cut != "-":
        full = dict(navs[pick])
        rows = [(r["날"], float(r["NAV"])) for r in csv.DictReader(open(cut, encoding="utf-8"))]
        out["cut_days"] = len(rows)
        out["cut_ok"] = len(rows) > 0 and all(abs(v / full[d] - 1) < 1e-9 for d, v in rows)
    checks = out["check_m1_back_23.44"] and out["check_m2_back_33.83"] and out.get("cut_ok", False)
    out["verdict"] = "판정 보류" if not (checks and pick) else ("PASS" if out["pass_limits"] and out["pass_beats_m1"] else "FAIL")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
