"""D1-VOL2-VALIDATE-0005 — 후보(지금 규칙 + 흔들림 상한 × 2 · 덜어내기 없음) 고정 판의 확인 V1(원 자료) · V2(시총 고친 자료) · V4(자르기).
NRL_CACHE로 자료 묶음을 고름(원: /tmp/nrl-cache.pkl · 고친: CAPS_ADJ=1 + scratchpad/nrl-cache-adj.pkl). Z_TAG=raw|adj.
python3 research/z083.py"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import z080  # noqa: E402
import z081  # noqa: E402

OUT = Path(os.environ.get("Z_OUT", "/home/user/stock-dash/research-exchange/claude-to-gpt/D1-VOL2-VALIDATE-0005/evidence"))
TAG = os.environ.get("Z_TAG", "raw")
CAND = {"vol": z080.VOL_DAY * 2}          # 후보: 흔들림 상한 × 2(하루 2.1822%) · 덜어내기 없음
CUTS = {"앞": ("20190630",), "뒤": ("20231231", "20250630")}


def main():
    out = {"task": "D1-VOL2-VALIDATE-0005", "tag": TAG, "cache": os.environ.get("NRL_CACHE", "/tmp/nrl-cache.pkl"), "candidate": {"vol_day": CAND["vol"]}}
    for which in ("앞", "뒤"):
        gs = z081.ledgers(which, z081.holds_b0)
        base = z081.evaluate(gs, {})
        cand = z081.evaluate(gs, CAND)
        cuts = [z080.cut_check(gs[0], T, **CAND) for T in CUTS[which]]
        keep = ("cagr", "cagr_spread", "worst_day", "worst_month", "mdd", "regime", "down_side", "down_side_spread", "months")
        out[which] = {"지금 규칙": {k: base[k] for k in keep}, "후보": {k: cand[k] for k in keep}, "cut_check": cuts,
                      "engine_median": sorted(g["engine"] for g in gs)[len(gs) // 2]}
        for n, r in (("지금 규칙", base), ("후보", cand)):
            print(f"[{TAG} · {which}] {n}: 연복리 {r['cagr']}(폭 {r['cagr_spread']}) · 하루 {r['worst_day']} · 달 {r['worst_month']} · 고점 대비 {r['mdd']} · "
                  f"장별 {r['regime']} · 횡보+하락 {r['down_side']}", flush=True)
        print(f"[{TAG} · {which}] 엔진 연수익(가운데) {out[which]['engine_median']} · 자르기 {cuts}", flush=True)
    c = {w: out[w]["후보"] for w in ("앞", "뒤")}
    out["limits_ok"] = all(c[w]["worst_day"][1] > -15 and c[w]["worst_month"][1] > -15 for w in c)
    out["positive"] = all(c[w]["cagr"] > 0 for w in c)
    out["cuts_ok"] = all(x["ok"] for w in ("앞", "뒤") for x in out[w]["cut_check"])
    out["pass"] = out["limits_ok"] and out["positive"] and out["cuts_ok"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"validate_{TAG}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"[{TAG}] 판정: 한도 {out['limits_ok']} · 연복리 > 0 {out['positive']} · 자르기 {out['cuts_ok']} → {'PASS' if out['pass'] else 'FAIL'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
