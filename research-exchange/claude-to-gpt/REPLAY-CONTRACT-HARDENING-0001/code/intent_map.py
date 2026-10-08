"""REPLAY-CONTRACT-HARDENING-0001 · 148체결 → 결정적 의도(target_adj) 변환 고정 — 성과 · 재생 없음 · 네트워크 없음.
python3 -E -P intent_map.py <PR76 fixed_local_only.json> <옛 nrl-cache.pkl> <salt> <PR86 로컬 대상 148.json> <공개 출력.json> <로컬 의도 출력.json>

PR #76 계약(et_replay.py 7 · 8 · 91줄): t 종가 뒤 목표 수량 target_{t+1}(c) = floor(E × k × 통제수량_t(c))를 잠그고 t+1 종가에 그 수량으로 맞춤.
t+1 종가로 목표를 다시 맞추지 않음. → 원주가 재생의 의도도 '금액'이 아니라 '판단일 목표 수량'.
- 의도 = {decided_at = 체결 앞 거래일, for = 체결일, target_adj = 그 결정 기록의 정수 목표, adj_close_decided = 저장 수정종가_t}
- 원주가 재생 때 target_raw = floor(target_adj × 저장 수정종가_t ÷ 공식 원주가_t) (raw_replay_v2.convert_target)
  · 저장 수정종가가 미래 기업행동까지 반영한 값이어도, 통제수량도 같은 스냅숏 위에서 셌기 때문에 F_t가 그 배율을 되돌림.
- 주문 = 목표 − 보유(기업행동 조정 뒤 원수량) · 팔기 먼저 · 종목 코드 오름차순 · floor는 목표 환산 한 번만.
검사: 결정 있음 · 목표에 종목 있음 · 방향이 (목표 vs 보유)와 맞음 · 매도 수량 = 보유 − 목표 · 매수 수량 ≤ 목표 − 보유 · 판단일 저장가 있음 · 같은 날 같은 종목 둘 없음 · 저장 순서 = 규칙 순서.
공개: 상태별 개수 · fill_id → sha256(salt|종목|날짜|방향|목표) 앞 16자. 로컬 전용: 실제 종목 · 날짜 · 목표 · 가격."""
import hashlib
import json
import pickle
import random
import socket
import sys
from collections import Counter, defaultdict
from pathlib import Path

socket.socket = socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("네트워크 금지"))
L76, OLD, SALT, T148, PUB, LOC = sys.argv[1:7]
salt = Path(SALT).read_text().strip()
H = lambda *x: hashlib.sha256((salt + "|" + "|".join(map(str, x))).encode()).hexdigest()[:16]
CL = {c: dict(v["rows"]) for c, v in pickle.load(open(OLD, "rb"))[0].items()}
l76 = json.load(open(L76))
t148 = json.load(open(T148))
cls_of = {r["fill_id"]: r["class"] for r in t148}


def build(trades_order_seed=None):
    out, order_ok, dup = [], Counter(), Counter()
    for sleeve in ("D1", "BASKET"):
        dec = {x["for"]: x for x in l76[sleeve]["decisions"]}
        trades = list(enumerate(l76[sleeve]["trades"]))
        held = defaultdict(int)
        by_day = defaultdict(list)
        for i, t in trades:
            by_day[t[0]].append((i, t))
        days = sorted(by_day)
        for d in days:
            todays = by_day[d]
            if trades_order_seed is not None:                              # 입력 순서를 섞어도 결과가 같아야 함
                todays = todays[:]
                random.Random(trades_order_seed + int(d) % 997).shuffle(todays)
            rule = sorted(todays, key=lambda z: (z[1][2] != "sell", z[1][1]))
            order_ok["same" if [z[0] for z in rule] == sorted(z[0] for z in todays) else "diff"] += 1
            seen = Counter((t[1], t[2]) for _, t in todays)
            for i, (d_, c, s, n) in rule:
                fid = f"{sleeve}-{i:04d}"
                x = dec.get(d)
                why = None
                if seen[(c, s)] > 1 or sum(1 for _, t in todays if t[1] == c) > 1:
                    why = "BLOCKED_DUP_INTENT"
                    dup[fid] += 1
                elif x is None:
                    why = "BLOCKED_NO_DECISION"
                elif c not in x["targets"]:
                    why = "BLOCKED_NO_TARGET_FOR_CODE"
                tgt = x["targets"].get(c) if x else None
                h = held[c]
                if why is None:
                    if s == "sell" and not (tgt < h and n == h - tgt):
                        why = "BLOCKED_SIDE_OR_QTY_MISMATCH"
                    elif s == "buy" and not (tgt > h and 0 < n <= tgt - h):
                        why = "BLOCKED_SIDE_OR_QTY_MISMATCH"
                    elif CL.get(c, {}).get(x["decided_at"]) in (None, 0):
                        why = "BLOCKED_NO_ADJ_AT_DECISION"
                    elif x["decided_at"] >= d:
                        why = "BLOCKED_DECISION_NOT_BEFORE_FILL"
                held[c] += n if s == "buy" else -n
                out.append({"fill_id": fid, "sleeve": sleeve, "date": d, "code": c, "side": s,
                            "status": why or "MAPPED_PENDING_OFFICIAL_RAW",
                            "intent": None if why else {"kind": "target_adj", "decided_at": x["decided_at"], "target_adj": tgt,
                                                       "adj_close_decided": CL[c][x["decided_at"]],
                                                       "buy_reduced_in_pr76": bool(s == "buy" and n < tgt - h)},
                            "class": cls_of.get(fid)})
    return out, order_ok, dup


res, order_ok, dup = build()
res2, _, _ = build(trades_order_seed=7)
canon = lambda rs: hashlib.sha256(json.dumps(sorted(rs, key=lambda r: r["fill_id"]), sort_keys=True, ensure_ascii=False).encode()).hexdigest()
det_same = canon(res) == canon(res2)
assert len(res) == 148 and len(t148) == 148 and {r["fill_id"] for r in res} == set(cls_of), "148 분모 불일치"
st = Counter(r["status"] for r in res)
# 결정 기록 전체 중 체결 없는 (날, 종목) 목표 — 원주가 재생은 결정 기록으로 돌아 floor 차이로 추가 체결이 생길 수 있음(그때 EXTRA로 공개)
dec_total = {s: sum(len(x["targets"]) for x in l76[s]["decisions"]) for s in ("D1", "BASKET")}
pub = {"fills": len(res), "status": dict(st),
       "mapped_plus_blocked": sum(st.values()),
       "by_class_status": {f"{k[0]}|{k[1]}": v for k, v in Counter((r["class"], r["status"]) for r in res).items()},
       "by_sleeve_side_status": {f"{k[0]}_{k[1]}|{k[2]}": v for k, v in Counter((r["sleeve"], r["side"], r["status"]) for r in res).items()},
       "buy_reduced_in_pr76": sum(1 for r in res if r["intent"] and r["intent"]["buy_reduced_in_pr76"]),
       "same_day_order_rule_matches_pr76_storage": dict(order_ok),
       "dup_same_day_same_code": len(dup),
       "deterministic_under_shuffled_input": det_same,
       "decision_targets_total(날 × 종목)": dec_total,
       "intent_hashes(fill_id: sha(code|date|side|target_adj))": {r["fill_id"]: H(r["code"], r["date"], r["side"], r["intent"]["target_adj"] if r["intent"] else "NA") for r in res},
       "salt_sha256": hashlib.sha256(salt.encode()).hexdigest(),
       "mapping_rule": "target_raw = floor(target_adj × 저장 수정종가_t ÷ 공식 원주가_t) · 주문 = 목표 − 보유 · 팔기 먼저 · 종목 코드 오름차순",
       "pending": "공식 원주가_t가 없어 수치 목표는 아직 없음(실제 수집 TASK에서 환산)"}
Path(PUB).write_text(json.dumps(pub, ensure_ascii=False, indent=1))
Path(LOC).write_text(json.dumps(res, ensure_ascii=False))
print(json.dumps({k: v for k, v in pub.items() if not k.startswith("intent_hashes")}, ensure_ascii=False))
