"""KMF-0008 시험 1(09-01 ~ 10-12 · 비독립) 한 번 — 확인 통과 칸(evidence/pick.json)만 · GPT 동의 파일(final_ok.json) 있을 때 · 10-13부터 안 읽음 · 두 번째는 멈춤.
결과는 늘 WAITING_DATA(시험 2) 또는 NO_EDGE(시험 1). python3 research/kmf8_test1.py"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kmf as K  # noqa: E402
import kmf8 as K8  # noqa: E402

OK = K8.BOX / "final_ok.json"
OUT = K8.BOX / "evidence/test1.json"


def main():
    if OUT.exists():
        sys.exit("시험 1은 이미 한 번 돌렸음(멈춤)")
    if not OK.exists():
        sys.exit("지피티 동의 파일이 없음(멈춤)")
    pick = json.loads((K8.BOX / "evidence/pick.json").read_text())
    ok = json.loads(OK.read_text())
    if not pick or not pick.get("val_pass") or ok.get("pick") != pick["name"]:
        sys.exit("확인 통과 칸이 아니거나 동의 파일과 다름(멈춤)")
    b = K8.prep(K._rows_before(K.TEST2_FROM))
    days, trades = K.simulate(b, K8.signals(b, pick["cfg"]))
    t = K.stats(days, trades, *K.TEST)
    pass1 = t.get("days", 0) > 0 and t["total_p"] > 0 and t["worst_day_p"] >= K.DAY_STOP - 0.5
    OUT.write_text(json.dumps({"ok": ok, "name": pick["name"], "cfg": pick["cfg"], "test1": t, "pass1": pass1,
                               "val_check": K.stats(days, trades, *K.VAL)["total_p"]}, ensure_ascii=False, indent=1))
    print(json.dumps({"verdict": "WAITING_DATA(시험 2)" if pass1 else "NO_EDGE(시험 1)", "test1_total_p": t.get("total_p"), "pass1": pass1}, ensure_ascii=False))


if __name__ == "__main__":
    main()
