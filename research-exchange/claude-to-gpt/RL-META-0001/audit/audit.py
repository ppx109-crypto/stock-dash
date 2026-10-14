# RL-META-0001 독립 감사 — 공개 출력(rl_meta_out.json · RESULT.md)만 읽음
import json, os, re, sys
B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = json.load(open(os.path.join(B, "rl_meta_out.json"), encoding="utf-8"))
RES = open(os.path.join(B, "RESULT.md"), encoding="utf-8").read()
OUT = []; NP = NF = 0
def rep(ok, name, extra=""):
    global NP, NF
    if ok is None: OUT.append(f"NEEDS_DATA {name} {extra}"); return
    if ok: NP += 1
    else: NF += 1
    OUT.append(f"{'PASS' if ok else 'FAIL'} {name} {extra}".rstrip())
EPS = 1e-6
ARM = J["팔 날별"]; DAYS = list(ARM)
# 1
rep(len(DAYS) == 183 and DAYS[0] == "20260108" and DAYS[-1] == "20261012" and DAYS == sorted(DAYS),
    "1 날 수·범위", f"n={len(DAYS)} {DAYS[0]}..{DAYS[-1]}")
SEL = [d for d in DAYS if d <= "20260630"]; CHK = [d for d in DAYS if d > "20260630"]
rep(len(SEL) + len(CHK) == 183, "1 고르기/참고 나눔", f"SEL={len(SEL)} CHK={len(CHK)}")
rep(all(len(v) == 4 for v in ARM.values()), "1 팔 4개")
BR = J["판별 날별"]; PK = J["판별 고른 팔"]; BOARDS = list(BR)
# 2
for b in BOARDS:
    ok = list(BR[b]) == DAYS and list(PK[b]) == DAYS and all(abs(BR[b][d] - ARM[d][PK[b][d]]) <= EPS for d in DAYS)
    rep(ok, f"2 날별=팔[고른 팔] {b}")
# 3
for b, a in (("대조 A1 v12a", 1), ("대조 A2 P2", 2), ("대조 A3 나누기", 3)):
    rep(all(PK[b][d] == a for d in DAYS), f"3 고정 {b}=A{a}")
LEARN = [b for b in BOARDS if not b.startswith("대조")]
for b in LEARN:
    rep(all(PK[b][d] == 2 for d in DAYS[:20]), f"3 처음 20일 A2 {b}")
# 4
def argmax(v): m = max(v); return v.index(m)
def run_D(g):
    cum = [0.0]*4; pk = {}
    for i, d in enumerate(DAYS):
        pk[d] = 2 if i < 20 else argmax(cum)
        cum = [g*c + r for c, r in zip(cum, ARM[d])]
    return pk
def run_W(n):
    pk = {}
    for i, d in enumerate(DAYS):
        if i < 20: pk[d] = 2; continue
        s = [sum(ARM[x][k] for x in DAYS[max(0, i-n):i]) for k in range(4)]
        pk[d] = argmax(s)
    return pk
for b in LEARN:
    m = re.match(r"([DWR]) [γλn]([\d.]+)", b)
    t, p = m.group(1), float(m.group(2))
    if t == "R":
        rep(None, f"4 재현 {b}", "(맥락 입력 비공개 · 건너뜀)"); continue
    pk = run_D(p) if t == "D" else run_W(int(p))
    diff = [d for d in DAYS if pk[d] != PK[b][d]]
    rep(not diff, f"4 재현 {b}", f"다름 {len(diff)}일 {diff[:5]}")
# 5
def stats(vals_by_day):
    ds = list(vals_by_day); v = [vals_by_day[d] for d in ds]
    tot = sum(v); cum = pk = 0.0; mdd = 0.0
    for x in v:
        cum += x; pk = max(pk, cum); mdd = min(mdd, cum - pk)
    mon = {}
    for d, x in zip(ds, v): mon.setdefault(d[:6], []).append(x)
    ms = [sum(xs) for xs in mon.values() if len(xs) >= 5]
    top5 = sum(sorted(v, reverse=True)[:5])
    return {"합": tot, "MDD": mdd, "최악": min(v), "월 양수율": (sum(s > 0 for s in ms)/len(ms)) if ms else None,
            "월 양수": f"{sum(s > 0 for s in ms)}/{len(ms)}", "위5 몫": (top5/tot) if tot > 0 else None,
            "비": tot/max(1.0, abs(mdd)), "거래 날": sum(1 for x in v if x != 0)}
def same(a, b):
    if a is None or b is None: return a is None and b is None
    if isinstance(a, str): return a == b
    return abs(a - b) <= EPS
SEG = {"고르기 1~6월": SEL, "참고 7~10월": CHK, "9~10월": [d for d in DAYS if d >= "20260901"],
       "09-21 이후": [d for d in DAYS if d >= "20260921"], "전체": DAYS}
REC = {b: {s: stats({d: BR[b][d] for d in ds}) for s, ds in SEG.items()} for b in BOARDS}
KEYS = ["합", "MDD", "최악", "월 양수율", "월 양수", "위5 몫", "비", "거래 날"]
for row in J["후보 표(1~6월)"]:
    b = row["판"]; r = REC[b]["고르기 1~6월"]
    bad = [k for k in KEYS if not same(row[k], r[k])]
    cnt = {}
    for d in DAYS: cnt[str(PK[b][d])] = cnt.get(str(PK[b][d]), 0) + 1
    if cnt != row["고른 팔 수"]: bad.append("고른 팔 수")
    rep(not bad, f"5 후보 표 {b}", f"다름 {bad}")
for b in BOARDS:
    for s in SEG:
        g = J["판별 구간 성적"][b][s]
        bad = [k for k in KEYS if k in g and not same(g[k], REC[b][s][k])]
        rep(not bad, f"5 구간 {b} / {s}", f"다름 {bad}")
# 6
rows = [dict(REC[b]["고르기 1~6월"], 판=b) for b in BOARDS]
for r in rows: r["자격"] = r["합"] > 0 and r["최악"] >= -15 - 1e-9 and r["MDD"] >= -15 - 1e-9
rep(all(r["자격"] == x["자격"] for r, x in zip(rows, J["후보 표(1~6월)"])), "6 자격 표시 일치")
el = [r for r in rows if r["자격"]]
mx = max(r["월 양수율"] for r in el); el = [r for r in el if abs(r["월 양수율"] - mx) <= 1e-12]
sub = [r for r in el if r["위5 몫"] is not None and r["위5 몫"] <= 0.35]
grp = sub if sub else el
grp.sort(key=lambda r: (-r["비"], -r["합"], r["판"]))
rep(grp[0]["판"] == J["고른 판"], "6 고른 판 재현", f"재계산={grp[0]['판']} 출력={J['고른 판']}")
ch = REC[J["고른 판"]]["참고 7~10월"]; a2 = REC["대조 A2 P2"]["참고 7~10월"]
mon = {}
for d in CHK: mon.setdefault(d[:6], 0.0); mon[d[:6]] += BR[J["고른 판"]][d]
cond = {"① 4달 중 양수 ≥ 3": sum(v > 0 for v in mon.values()) >= 3, "② MDD ≥ −15": ch["MDD"] >= -15 - 1e-9,
        "③ 최악 ≥ −15": ch["최악"] >= -15 - 1e-9, "④ 위5 ≤ 35%": ch["위5 몫"] is not None and ch["위5 몫"] <= 0.35,
        "⑤ 비 ≥ 대조 A2": ch["비"] >= a2["비"]}
rep(cond == J["참고 조건"], "6 참고 조건", json.dumps(cond, ensure_ascii=False))
rep((J["참고 판정"] == "참고 지지 안 됨") == (not all(cond.values())), "6 참고 판정", J["참고 판정"])
mb = J["7~10월 달별(고른 판)"]
rep(all(abs((mb[m] if not isinstance(mb[m], dict) else mb[m].get("합")) - mon[m]) <= EPS for m in mon) and set(mb) == set(mon),
    "6 7~10월 달별")
# 7 RESULT.md 수치(보인 반올림대로)
def has(s): return s.replace("-", "−") in RES or s in RES
def f(x, n): return f"{x:.{n}f}".replace("-", "−")
def pct(x): return f"{x*100:.1f}%"
NM = {"대조 A1 v12a": "A1", "대조 A2 P2": "A2", "대조 A3 나누기": "A3"}
for b in NM:
    r = REC[b]["고르기 1~6월"]
    toks = [f(r["합"], 1), f(r["MDD"], 2), f(r["최악"], 2), pct(r["위5 몫"]), f(r["비"], 2)]
    miss = [t for t in toks if t not in RES]
    rep(not miss, f"7 RESULT 후보 표 {b}", f"없음 {miss}")
def trim(t): return t
for b in LEARN:
    r = REC[b]["고르기 1~6월"]
    toks = [f(r["합"], 1), f(r["비"], 1)] + ([] if b.startswith("D") else [f"{r['위5 몫']*100:.1f}"])  # D 위5는 '최소 ~ 최대' 범위로만 적혀 아래 범위 검사로 봄  # 위5는 표에 '30.6 ~ 34.6%' · '37.5 / 34.4%'처럼 묶어 적혀 % 없이 찾음
    m1 = f(r["MDD"], 1).rstrip("0").rstrip("."); m2 = f(r["MDD"], 2)
    miss = [t for t in toks if t not in RES]
    if m1 not in RES and m2 not in RES: miss.append(f"MDD {m2}")
    rep(not miss, f"7 RESULT 후보 표 {b}", f"없음 {miss} (범위로 적힌 위5는 아래에서 따로)" if miss else "")
# 학습기 위5 범위 30.6 ~ 34.6% (D 판)
dv = [REC[b]["고르기 1~6월"]["위5 몫"] for b in LEARN if b.startswith("D")]
rep(f"{min(dv)*100:.1f} ~ {max(dv)*100:.1f}%" in RES, "7 RESULT D 위5 범위", f"재계산 {min(dv)*100:.1f} ~ {max(dv)*100:.1f}%")
# 고른 팔 수 문구(RESULT 표의 R · W 칸과 D 범위)
def cnt_of(b):
    c = {}
    for d in DAYS: c[PK[b][d]] = c.get(PK[b][d], 0) + 1
    return c
R1, R10, W10, W20 = (cnt_of(x) for x in ("R λ1", "R λ10", "W n10", "W n20"))
t = f"A2 {R1[2]}/{R10[2]} · A1 {R1[1]}/{R10[1]} · A3 {R1[3]}/{R10[3]} · A0 {R1.get(0,0)}/{R10.get(0,0)}"
rep(t in RES, "7 RESULT 고른 팔 수 R", t)
t = f"A2 {W10[2]}/{W20[2]} · A1 {W10[1]}/{W20[1]} · A3 {W10[3]}/{W20[3]} · A0 {W10.get(0,0)}/{W20.get(0,0)}"
rep(t in RES, "7 RESULT 고른 팔 수 W", t)
DC = [cnt_of(x) for x in LEARN if x.startswith("D")]
t = " · ".join(f"A{k} {min(c.get(k,0) for c in DC)}~{max(c.get(k,0) for c in DC)}" for k in (2, 1, 3))
rep(t in RES, "7 RESULT 고른 팔 수 D", t)
for b in LEARN:
    cnt = {}
    for d in DAYS: cnt[PK[b][d]] = cnt.get(PK[b][d], 0) + 1
    OUT.append(f"INFO 고른 팔 수 {b} {dict(sorted(cnt.items()))}")
# 구간 표
for b in NM:
    for s, n2 in (("참고 7~10월", True), ("9~10월", False), ("09-21 이후", False), ("전체", True)):
        r = REC[b][s]
        toks = [f(r["합"], 1), f(r["MDD"], 2)] + ([pct(r["위5 몫"])] if n2 else [])
        line = [l for l in RES.splitlines() if l.startswith(f"| {'**' if b.endswith('나누기') else ''}{NM[b]}") or l.startswith(f"| {NM[b]}")]
        L = " ".join(line)
        miss = [t for t in toks if t not in L and t.rstrip("0").rstrip(".") not in L]
        rep(not miss, f"7 RESULT 구간 {b} / {s}", f"없음 {miss} 재계산 {toks}")
# 학습기 범위
for s, lab in (("참고 7~10월", "7~10"), ("9~10월", "9~10"), ("09-21 이후", "09-21"), ("전체", "전체")):
    v = [REC[b][s]["합"] for b in LEARN]
    t = f"{min(v):.1f} ~ {max(v):.1f}"
    rep(t in RES, f"7 RESULT 학습기 범위 {s}", f"재계산 {t}")
v = [REC[b]["전체"]["MDD"] for b in LEARN]
t = f"MDD {f(max(v),2)} ~ {f(min(v),1)}"
rep(t in RES, "7 RESULT 학습기 전체 MDD 범위", f"재계산 {t}")
# 참고 판정 수치
r = REC[J["고른 판"]]["참고 7~10월"]
for t in (f(r["MDD"], 2), f(r["최악"], 1), pct(r["위5 몫"])):
    rep(t in RES.split("## 3.")[1].split("## 4.")[0], f"7 RESULT 참고 판정 수치 {t}")
OUT.append(f"합계 PASS={NP} FAIL={NF}")
print("\n".join(OUT))
