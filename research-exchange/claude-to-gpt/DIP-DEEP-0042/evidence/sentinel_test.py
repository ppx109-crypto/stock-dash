"""DIP-DEEP-0042 센티널 시험 — 2022-12-29 뒤 자료를 크게 바꿔 넣어도 개발 도구의 D 산출물이 한 칸도 안 바뀌는지.
- 두 번 돌림: 보통(SENT=0) · 센티널(SENT=1: nrl의 CUT 뒤 일봉 × 3, 표 줄 가짜 추가, 수급 누적 + 1e12, 시장 폭 0).
- 뜻 없는 가짜 후보(코드 끝자리 짝수 · 날짜 끝자리 3 · 5일 뒤 팖)로 엔진을 돌리고, 결과와 부품 값 전체를 sha256으로만 적음.
  성적 숫자는 출력하지 않음(가설과 무관 · 평가 판 수에 넣지 않음 · 고르기에 쓰지 않음).
python3 evidence/sentinel_test.py   (안에서 두 번 새 프로세스로 돌림)"""
import hashlib, json, os, subprocess, sys
if os.getenv("SENT_CHILD"):
    sys.path.insert(0, "/home/user/stock-dash"); sys.path.insert(0, "/home/user/stock-dash/research")
    import nrl
    CUT = "20221229"
    if os.getenv("SENT_CHILD") == "1":
        for b in nrl.prices.values():
            b["rows"] = [(d, c * 3 if d > CUT else c) for d, c in b["rows"]]
        fake = [dict(r, date="20230105") for r in nrl.inside[:500]]
        nrl.inside.extend(fake)
        for code, (days, acc, ok, closes) in nrl.FLOW.items():
            import bisect
            k = bisect.bisect_right(days, CUT)
            for c in acc:
                for j in range(k + 1, len(acc[c])):
                    acc[c][j] += 1e12
        for d in list(nrl.BR):
            if d > CUT:
                nrl.BR[d] = 0.0
        nrl.BR["20230105"] = 0.0
    import dip_dev as D
    feats = [(r["code"], r["date"], D.ret(r, 5), D.ma_gap(r, 20), D.flow_sum(r, 5, "외국인"), D.flow_sum(r, 5, "투신"),
              D.flow_sum(r, 5, "개인"), D.ix_ret(r["date"], 60), D.BR.get(r["date"])) for r in D.rows]
    dummy = lambda r: int(r["code"][-1]) % 2 == 0 and r["date"][-1] == "3"
    res = D.run_way(dummy, D.fixed_exit(1e9, 1e9, 5))
    out = {"rows": len(D.rows), "max_date": max(r["date"] for r in D.rows), "res_present": {k: v is not None for k, v in res.items()},
           "feat_sha": hashlib.sha256(json.dumps(feats, ensure_ascii=False).encode()).hexdigest(),
           "res_sha": hashlib.sha256(json.dumps(res, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
           "prices_sha": hashlib.sha256(json.dumps(sorted((c, b["rows"]) for c, b in D.prices.items())).encode()).hexdigest()}
    print(json.dumps(out))
    sys.exit(0)
got = {}
for mode in ("0", "1"):
    p = subprocess.run([sys.executable, __file__], env={**os.environ, "SENT_CHILD": mode}, capture_output=True, text=True)
    if p.returncode:
        print(p.stderr[-2000:]); sys.exit(1)
    got[mode] = json.loads(p.stdout.strip().splitlines()[-1])
same = got["0"] == got["1"]
print(json.dumps({"보통": got["0"], "센티널": got["1"], "완전_같음": same}, ensure_ascii=False, indent=1))
sys.exit(0 if same else 1)
