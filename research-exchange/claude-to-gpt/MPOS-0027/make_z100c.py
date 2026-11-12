"""z100c = z100g(MPOS-0012) 진단 사본(PREREG 2판 3절): 1일봉 요청 · 배정 · 못 산 이유 · 매매마다 실제 원 손익을 Z_EVT(json)에 적음.
원문에 기록 줄만 끼움(정확한 문자열 치환 · 한 번씩) · 바탕 csv는 z100g와 바이트까지 같아야 함(실행 뒤 대조).
python3 make_z100c.py <z100g.py> <z100c.py>"""
import sys

src = open(sys.argv[1], encoding="utf-8").read()
rep = [
    ("    pl = _dd(float)\n", "    pl = _dd(float)\n    EVT_REQ, EVT_PAID, EVT_PROC, EVT_SELLDAY = [], {}, {}, {}\n"),
    ("        cash += amt - c\n        costs += c\n        pl[lane(p)] -= c\n",
     "        cash += amt - c\n        costs += c\n        pl[lane(p)] -= c\n        if p[\"bot\"] == \"1d\":\n            EVT_PROC[key] = EVT_PROC.get(key, 0.0) + amt - c\n            EVT_SELLDAY[key] = d\n"),
    ("        cash -= money\n        costs += c\n        pos[key] = dict(bot=bot, code=code, val=money - c, px=px, day=d, **kw)\n",
     "        cash -= money\n        costs += c\n        pos[key] = dict(bot=bot, code=code, val=money - c, px=px, day=d, **kw)\n        if bot == \"1d\":\n            EVT_PAID[key] = money\n"),
    ("            ratio = min(1.0, room * 0.995 / need)\n            for tag, k, c, want in grp:\n                got = buy((tag, k), \"1d\", c, d, want * ratio)\n",
     "            ratio = min(1.0, room * 0.995 / need)\n            _rc = min(cash * 0.98, cash / MARGIN)\n"
     "            _ra = max(0.0, acc_allowed * total() - sum(p[\"val\"] for p in pos.values())) if ACC_VOL > 0 else float(\"inf\")\n"
     "            for tag, k, c, want in grp:\n                got = buy((tag, k), \"1d\", c, d, want * ratio)\n"
     "                EVT_REQ.append(dict(날=d, k=k, 종목=c, 요청=want, 비율=ratio, 배정=got, 이유=(\"가격 없음\" if not price(c, d) else \"다 삼\" if got >= want * 0.99 "
     "else (\"현금 모자람\" if _rc <= _ra else \"흔들림 상한\") if ratio < 1.0 else \"매수 함수 안 제한\")))\n"),
    ("        need = sum(w for _, _, c, w in grp if price(c, d))\n        if need > 0:\n",
     "        need = sum(w for _, _, c, w in grp if price(c, d))\n        if need <= 0:\n            for tag, k, c, want in grp:\n                EVT_REQ.append(dict(날=d, k=k, 종목=c, 요청=want, 비율=0.0, 배정=0.0, 이유=\"가격 없음\"))\n        if need > 0:\n"),
    ("    if out:\n        N.round(0).to_csv(out)\n",
     "    if out:\n        N.round(0).to_csv(out)\n    if os.getenv(\"Z_EVT\"):\n"
     "        json.dump({\"요청\": EVT_REQ, \"매매\": [dict(k=key[1], 종목=led1[key[1]][0], 산날=led1[key[1]][1], 판날=EVT_SELLDAY.get(key), 낸돈=v, 받은돈=EVT_PROC.get(key), "
     "손익=(EVT_PROC.get(key, 0.0) - v) if key in EVT_SELLDAY else None, 끝까지보유=key in pos) for key, v in EVT_PAID.items()]}, open(os.getenv(\"Z_EVT\"), \"w\"), ensure_ascii=False)\n"),
]
for a, b in rep:
    assert src.count(a) == 1, a[:80]
    src = src.replace(a, b)
open(sys.argv[2], "w", encoding="utf-8").write(src)
print("z100c 만듦")
