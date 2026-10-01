"""15분봉 연구의 미래 참조 검사(hguard.py와 같은 방식). 하나라도 어긋나면 FAIL과 어긋난 자리를 말함.

python m15guard.py  → docs/15M-GUARD.md에 결과를 적음(15분봉 회차에서 새 규칙을 올리기 전에 돌림).

1. 시험지 잠금  — 최종 시험 달(2026-09) 15분봉을 읽지 않음(m15lab.load · M15_OPEN_OOS) · 2026-09-30 뒤도(hlab.bar_limit).
2. 체결 감사    — 모의 안에서 체결마다 바로 앞 봉이 닫힌 뒤 정한 것인지 · 장중 체결 값이 봉 안인지(hlab._audit — 어긋나면 모의가 멈춰 세계가 실패).
3. 잘라내기     — 시각 T 뒤 15분봉 · 일봉 · 수급 · 공시 · 순위를 모두 잘라 낸 세계에서, T까지의 신호 · T까지 끝난 매매가 한 건도 다르지 않은지.
4. 더럽히기     — T 뒤 자료를 엉뚱한 값으로 바꾼 세계에서 같은 비교.
   4b 봉마다    — 종목 60개 × 봉 약 24곳마다 그 봉 뒤만 엉뚱하게 바꿔, 그 봉의 사는 신호 · 파는 판단이 그대로인지(한 봉 엿보기를 잡음).
5. 검사 눈 확인 — 일부러 미래를 보는 규칙 셋(다음 봉 보고 사기 · 120봉 뒤 보고 사기 · 다음 봉 보고 팔기)은 3 · 4 가운데 어디서든 반드시 걸려야 함.
6. 날짜 짚기    — 봉에 붙은 일봉 재료의 날 · 수급 마지막 날이 그 봉의 날보다 앞인지.
(단위 시험 tests/test_m15lab.py: 읽기 · 잠금 · 잘라내기 · 더럽히기 · 다음 봉 시가 체결)
"""
import os
import pickle
import subprocess
import sys
import tempfile
from pathlib import Path

CUTS = ("2025121010", "2026031311", "2026061514")
EYES = ("엿보기: 다음 봉 보고 사기", "엿보기: 120봉 뒤 보고 사기", "엿보기: 다음 봉 보고 팔기")


def world(env_extra, tag):
    path = Path(tempfile.gettempdir()) / f"m15guard_{tag}.pkl"
    env = {**os.environ, **env_extra}
    env.pop("HLAB_OPEN_HOLDOUT", None)
    env.pop("M15_OPEN_OOS", None)
    r = subprocess.run([sys.executable, "research/m15guard_world.py", str(path)], env=env, capture_output=True, text=True)
    if r.returncode != 0:
        return None, (r.stderr or r.stdout)[-1500:]
    return pickle.loads(path.read_bytes()), None


def compare(full, other, T):
    out = {}
    stamp = T + "00"          # 10자리 시각 T → 15분봉에선 T시 00분 '앞'까지가 같아야 함
    for name, fr in full["rules"].items():
        orr = other["rules"][name]
        s1 = {(c, t) for c, ts in fr["sigs"].items() for t in ts if t < stamp}
        s2 = {(c, t) for c, ts in orr["sigs"].items() for t in ts if t < stamp}
        t1 = {x for x in fr["trades"] if not str(x[2]).startswith("끝") and x[2] < stamp}
        t2 = {x for x in orr["trades"] if not str(x[2]).startswith("끝") and x[2] < stamp}
        out[name] = (len(s1 ^ s2), len(t1 ^ t2), len(t1))
    return out


def main():
    lines = ["# 15분봉 미래 참조 검사 결과", "", "m15guard.py가 적음. 겹 설명은 m15guard.py 머리말.", ""]
    fails = []
    full, err = world({}, "full")
    if err:
        print(err)
        return 1
    lines.append(f"- 1 시험지 잠금: 마지막 봉 {full['last']} (최종 시험 달 2026-09 앞) → {'통과' if full['last'] < '202609010000' else '**어긋남**'}")
    if full["last"] >= "202609010000":
        fails.append("잠금")
    lines.append("- 2 체결 감사: 전체 세계 모의가 감사에 걸리지 않고 끝남 → 통과")
    lines.append(f"- 6 날짜 짚기: 재료가 붙은 봉 {full['dates_seen']:,}개 가운데 그 봉의 날보다 늦은 재료 {full['dates_bad']} → "
                 + ("통과" if full["dates_bad"] == 0 else "**어긋남**"))
    if full["dates_bad"]:
        fails.append("날짜")
    caught = {e: 0 for e in EYES}
    lines += ["", "| 겹 | 자른 · 더럽힌 시각 | 규칙 | 다른 신호 | 다른 매매 | 견준 매매 | 결과 |", "|---|---|---|---|---|---|---|"]
    for how, key in (("3 잘라내기", "HLAB_CUT"), ("4 더럽히기", "HLAB_POISON")):
        for T in CUTS:
            other, err = world({key: T}, f"{key}_{T}")
            if err:
                fails.append(f"{how} {T} 세계 실패")
                lines.append(f"| {how} | {T} | (세계 실패) | | | | **어긋남** |")
                continue
            for name, (ds, dt, n) in compare(full, other, T).items():
                eye = name in EYES
                if eye:
                    caught[name] += ds + dt
                    res = "검사 눈" if ds + dt else "-"
                else:
                    res = "통과" if ds + dt == 0 else "**어긋남**"
                    if ds + dt:
                        fails.append(f"{how} {T} {name}")
                lines.append(f"| {how} | {T} | {name} | {ds} | {dt} | {n} | {res} |")
    lines.append("")
    for name, (seen, diff) in (full.get("bar_poison") or {}).items():
        eye = name in EYES
        if eye:
            caught[name] += diff
        res = ("검사 눈" if diff else "-") if eye else ("통과" if diff == 0 else "**어긋남**")
        if not eye and diff:
            fails.append(f"4b 봉마다 {name}")
        lines.append(f"- 4b 봉마다 더럽히기 '{name}': 본 봉 {seen} · 달라진 판단 {diff} → {res}")
    if not full.get("bar_poison"):
        fails.append("4b 봉마다 더럽히기를 못 돌림")
    lines.append("")
    for e, n in caught.items():
        ok = n > 0
        lines.append(f"- 5 검사 눈 '{e}': 걸린 수 {n} → {'통과' if ok else '**어긋남(검사가 눈멂)**'}")
        if not ok:
            fails.append(f"검사 눈 {e}")
    lines += ["", "**종합: " + ("모두 통과**" if not fails else f"어긋남 {len(fails)}곳** — " + " · ".join(fails))]
    # 시험용 자료(M15_HOME)로 돌린 결과는 문서에 남기지 않음(진짜 15분봉 결과만 docs/15M-GUARD.md에)
    if not os.environ.get("M15_HOME"):
        Path("docs/15M-GUARD.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
