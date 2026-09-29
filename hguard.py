"""1시간봉 연구의 미래 참조 검사(여덟 겹). 하나라도 어긋나면 FAIL과 어긋난 자리를 말함.

python hguard.py            → docs/1H-GUARD.md에 결과를 적음(회차에서 새 규칙을 올리기 전에 돌림)

1. 시험지 잠금   — 2026-09-30 뒤 봉 · 일봉 · 수급 · 공시 · 순위를 아예 읽지 않음(hlab.bar_limit · day_limit).
2. 체결 감사     — 모의 계좌 안에서 체결마다: 시가 체결은 그 종목의 **바로 앞 봉**이 닫힌 뒤 정한 것인지, 장중 손절 · 익절 값은
                   그 봉의 저가~고가 안인지, 자리 바꾸기 판단 봉이 체결 봉보다 앞인지(hlab._audit — 어긋나면 모의가 멈춤).
3. 잘라내기      — 시각 T 뒤 자료(1시간봉 · 일봉 · 수급 · 공시 · 시총 순위 · 추세 문)를 모두 잘라 낸 세계에서 다시 돌려,
                   T까지의 신호와 T까지 끝난 매매가 전체 세계와 **한 건도 다르지 않은지**.
4. 더럽히기      — T 뒤 자료를 엉뚱한 값(제멋대로 걷는 주가 · 뒤섞은 순위 · 가짜 수급 · 가짜 공시)으로 바꾼 세계에서 같은 비교.
                   '조금이라도 뒷날을 쓴 것'까지 잡힘.
   4b 봉마다 더럽히기 — 종목 60개 × 봉 약 24곳(재료가 켜진 봉 절반)마다 그 봉 **뒤만** 엉뚱하게 바꿔, 그 봉까지의 사는 신호 ·
                   그 봉의 파는 판단 · 묵음(자리 바꾸기) 판단이 그대로인지. 한 봉만 엿보는 규칙도 잡으려고 수백 곳을 봄.
5. 검사 눈 확인  — 일부러 다음 봉 종가를 보는 규칙(엿보기)은 3 · 4에서 **반드시 걸려야** 함. 안 걸리면 검사가 눈먼 것 → FAIL.
6. 날짜 짚기     — 봉마다 붙은 일봉 재료의 날 · 수급 마지막 날이 그 봉의 날보다 앞인지(전 거래일 것만 쓰는지).
7. 문턱은 과거로 — '조용함' 문턱은 달마다 그 달 앞 자료로만(hlab.calm_by_month, tests/test_hguard.py가 뒷줄을 더해도 앞 달 값이
                   그대로인지 봄). 순위 · 분위 같은 문턱을 새로 만들면 이 방식으로만.
8. 단위 시험     — tests/test_hguard.py(인공 자료): 잠금 · 잘라내기 · 더럽히기가 load에서 제대로 되는지, 감사가 어긋난 체결을 잡는지,
                   자른 자료로 돌린 모의가 앞부분 매매를 그대로 내는지, 엿보기 규칙은 달라지는지.
"""
import os
import pickle
import subprocess
import sys
import tempfile
from pathlib import Path

CUTS = ("2024061314", "2025031411", "2025121210")


def world(env_extra, tag):
    path = Path(tempfile.gettempdir()) / f"hguard_{tag}.pkl"
    env = {**os.environ, **env_extra}
    env.pop("HLAB_OPEN_HOLDOUT", None)
    r = subprocess.run([sys.executable, "research/hguard_world.py", str(path)], env=env, capture_output=True, text=True)
    if r.returncode != 0:
        return None, (r.stderr or r.stdout)[-1500:]
    return pickle.loads(path.read_bytes()), None


def compare(full, other, T):
    """T까지의 신호 · T까지 끝난 매매가 같은가 → {규칙: 어긋난 수 · 보기}."""
    out = {}
    for name, fr in full["rules"].items():
        orr = other["rules"][name]
        s1 = {(c, t) for c, ts in fr["sigs"].items() for t in ts if t <= T}
        s2 = {(c, t) for c, ts in orr["sigs"].items() for t in ts if t <= T}
        t1 = {x for x in fr["trades"] if not str(x[2]).startswith("끝") and x[2] <= T}
        t2 = {x for x in orr["trades"] if not str(x[2]).startswith("끝") and x[2] <= T}
        diff_s, diff_t = s1 ^ s2, t1 ^ t2
        out[name] = (len(diff_s), len(diff_t), len(t1), sorted(diff_t)[:3] or sorted(diff_s)[:3])
    return out


def main():
    lines = ["# 1시간봉 미래 참조 검사 결과", "", "hguard.py가 적음. 여덟 겹 설명은 hguard.py 머리말.", ""]
    ok = True
    full, err = world({}, "full")
    if err:
        print(err)
        return 1
    # 1 시험지 잠금 · 6 날짜 짚기
    lock = full["max_bar"] < "2026093000" and full["max_rank_day"] < "20260930"
    ok &= lock
    lines.append(f"- 1 시험지 잠금: {'통과' if lock else 'FAIL'} (가장 늦은 봉 {full['max_bar']} · 가장 늦은 순위 날 {full['max_rank_day']})")
    lines.append("- 2 체결 감사: 통과(모든 규칙의 모의가 감사에 걸리지 않고 끝남)")
    d_ok = full["dates_bad"] == 0
    ok &= d_ok
    lines += ["", "| 4b 봉마다 더럽히기 | 규칙 | 어긋남 / 짚은 곳 | 판정 |", "|---|---|---|---|"]
    for name, (bad_n, n) in full["bar_poison"].items():
        good = bad_n > 0 if name.startswith("엿보기") else bad_n == 0
        ok &= good
        verdict = ("통과(걸림 = 검사 눈 살아 있음)" if good else "FAIL(검사가 눈멂)") if name.startswith("엿보기") else ("통과" if good else "FAIL")
        lines.append(f"| | {name} | {bad_n} / {n} | {verdict} |")
    lines.append("")
    lines.append(f"- 6 날짜 짚기: {'통과' if d_ok else 'FAIL'} (어긋난 봉 {full['dates_bad']} {full['dates'][:3]})")
    caught = {}
    lines += ["", "| 검사 | T | 규칙 | 어긋난 신호 | 어긋난 매매 | T까지 끝난 매매 | 판정 |", "|---|---|---|---|---|---|---|"]
    for kind, var in (("3 잘라내기", "HLAB_CUT"), ("4 더럽히기", "HLAB_POISON")):
        for T in CUTS:
            other, err = world({var: T}, f"{var}_{T}")
            if err:
                ok = False
                lines.append(f"| {kind} | {T} | (실행 실패) | | | | FAIL: {err.splitlines()[-1] if err else ''} |")
                continue
            for name, (ds, dt, n, ex) in compare(full, other, T).items():
                if name.startswith("엿보기"):
                    caught[name] = caught.get(name, 0) + (ds + dt > 0)
                    good = True
                    verdict = "걸림" if ds + dt else "(이 T에선 안 드러남)"
                else:
                    good = (ds + dt) == 0
                    verdict = "통과" if good else f"FAIL {ex}"
                ok &= good
                lines.append(f"| {kind} | {T} | {name} | {ds} | {dt} | {n} | {verdict} |")
    for name, hits in caught.items():
        ok &= hits > 0
        lines.append(f"- 3 · 4 검사 눈({name}): 자르기 · 더럽히기 여섯 곳 가운데 {hits}곳에서 걸림 → {'통과' if hits else 'FAIL(검사가 눈멂)'}")
    lines += ["", f"**종합: {'모두 통과' if ok else 'FAIL — 위 표에서 어긋난 곳을 고칠 때까지 결과를 믿지 않음'}**"]
    Path("docs/1H-GUARD.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
