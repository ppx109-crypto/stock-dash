"""MPOS-0010 검사 함수(영수증 PASS를 내는 코드 · 반대 검토 결함 1: 단계 묶음 STAGE에 들어감 · 순수 함수라 test_checks10.py로 검사 도구 자체를 시험)."""
import csv
import json
import os

OLD_N = 495


def ledger_ok(led, meta, raw_old, slots=10):
    """(통과, 까닭, 칸 최대). 기존 495줄 그대로 · 날마다 칸 ≤ 10 · 새 문 줄 순서 = 들어간 순서(산 날 · 그날 순위)."""
    msg = []
    if led[:OLD_N] != raw_old:
        msg.append("기존 495줄 바뀜")
    ev = {}
    for _, b, e, _, s in led:
        ev[b] = ev.get(b, 0) + s
        if e != "99999999":
            ev[e] = ev.get(e, 0) - s
    cur = worst = 0
    for d in sorted(ev):
        cur += ev[d]
        worst = max(worst, cur)
    if worst > slots + 1e-9:
        msg.append(f"칸 최대 {worst}")
    keys = [(m["산 날"], m["그날 순위"]) for m in meta]
    new = led[len(led) - len(meta):] if meta else []
    if keys != sorted(keys) or len(set(keys)) != len(keys) or [r[1] for r in new] != [m["산 날"] for m in meta]:
        msg.append("새 문 순서 ≠ 들어간 순서")
    return not msg, "; ".join(msg), worst


def new_rows(led, meta):
    return led[len(led) - len(meta):] if meta else []


def cut_compare(full, part, fullnav, partnav, ct):
    """자른 날까지 ① 순서 있는 진입(종목 · 산 날 · 칸) ② 판 줄 전체 ③ 보유 중 ④ 계좌 날마다 줄 전체 — 하나라도 다르면 FAIL."""
    e1, e2 = [(r[0], r[1], r[4]) for r in full if r[1] <= ct], [(r[0], r[1], r[4]) for r in part if r[1] <= ct]
    s1, s2 = [r for r in full if r[2] <= ct], [r for r in part if r[2] <= ct]
    o1, o2 = [(r[0], r[1]) for r in full if r[1] <= ct < r[2]], [(r[0], r[1]) for r in part if r[1] <= ct and r[2] == "99999999"]
    days = [d for d in sorted(fullnav) if d <= ct]
    nd = [d for d in days if partnav.get(d) != fullnav[d]]
    ok = e1 == e2 and s1 == s2 and o1 == o2 and not nd and bool(e1) and bool(days)
    return ok, {"진입": len(e1), "판 줄": len(s1), "보유 중": len(o1), "계좌 날": len(days), "진입 순서 다름": e1 != e2, "판 줄 다름": s1 != s2,
                "보유 다름": o1 != o2, "계좌 다른 날": nd[:3]}


def mods_ok(path, ref):
    if not os.path.exists(path):
        return False, "모듈 영수증 없음"
    r = json.load(open(path))
    diff = [k for k, v in r["모듈"].items() if k in ref and ref[k] != v]
    return (not r["바깥"] and not diff), (f"바깥 {r['바깥'][:2]}" if r["바깥"] else "") + (f" 지문 다름 {diff}" if diff else "")


def nav_rows(p):
    return {r["날"]: r for r in csv.DictReader(open(p, encoding="utf-8"))}
