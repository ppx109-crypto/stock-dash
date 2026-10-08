"""옛 features.json(읽기만)과 지금 가격으로 다시 센 '변동성' 줄을 종목별로 견줘 달별 조용함 문턱 차이의 원인을 찾음.
python3 -E -P rf_calmscan.py <b2> <features.json> <출력 json>"""
import json, os, re, sys, time
from collections import defaultdict
from pathlib import Path
import numpy as np
BASE, FEAT, OUTF = sys.argv[1], sys.argv[2], sys.argv[3]
os.chdir(BASE); sys.path[:0] = [BASE]
import lab, rule, study
t0 = time.time()
HEAD = re.compile(rb'"code": "([0-9A-Z]+)", "date": "(\d{8})"')
KEY = '"변동성": '.encode()
old_n, old_v, vals_old = defaultdict(int), defaultdict(float), []
first_old = {}


def one(piece):
    m = HEAD.search(piece, 0, 80)
    c, d = m.group(1).decode(), m.group(2).decode()
    first_old.setdefault(c, d)
    k = piece.find(KEY)
    e = k + len(KEY)
    j = e
    while piece[j:j + 1] not in (b",", b"}"):
        j += 1
    v = piece[e:j]
    if d < "20260901" and v != b"null":
        old_n[c] += 1
        old_v[c] += float(v)
        vals_old.append(float(v))


SEP = b'},{"code"'
buf = b""
with open(FEAT, "rb") as f:
    while True:
        chunk = f.read(1 << 25)
        if not chunk:
            break
        buf += chunk
        cut = buf.rfind(SEP)
        if cut < 0:
            continue
        part, buf = buf[:cut], buf[cut + 2:]
        for piece in part.split(SEP):
            one(piece if piece.startswith(b'{"code"') or piece.startswith(b'[{"code"') else b'{"code"' + piece)
one(buf)
print("옛 표 훑음", round(time.time() - t0), "초", len(old_n), "종목", len(vals_old), "줄", flush=True)
P = study.load_prices()
new_n, new_v, vals_new, first_new = {}, {}, [], {}
for c, b in P.items():
    rows = [x for x in b["rows"] if x[0] <= "20260930"]
    closes = [x[1] for x in rows]
    if len(closes) <= 120 + 60:
        continue
    vol = lab.rolling_std(closes)
    got = [(rows[i][0], vol[i]) for i in range(120, len(closes) - 5) if vol[i] is not None]
    first_new[c] = rows[120][0]
    sel = [v for d, v in got if d < "20260901"]
    new_n[c], new_v[c] = len(sel), sum(sel)
    vals_new += sel
q = lambda vals: float(np.partition(np.array(vals), int(len(vals) * rule.CALM))[int(len(vals) * rule.CALM)])
out = {"old_rows_lt_0901": len(vals_old), "new_rows_lt_0901": len(vals_new), "calm_0901_old_scan": q(vals_old), "calm_0901_new": q(vals_new),
       "codes_only_old": sorted(set(old_n) - set(new_n)), "codes_only_new": sorted(set(new_n) - set(old_n)),
       "count_diff": {c: [old_n.get(c, 0), new_n.get(c, 0), first_old.get(c), first_new.get(c)] for c in sorted(set(old_n) | set(new_n)) if old_n.get(c, 0) != new_n.get(c, 0)},
       "volsum_diff_codes(같은 줄 수)": sorted(c for c in set(old_n) & set(new_n) if old_n[c] == new_n[c] and abs(old_v[c] - new_v[c]) > 1e-6 * max(1, abs(old_v[c])))}
Path(OUTF).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: (v if not isinstance(v, (list, dict)) or len(v) < 40 else f"{len(v)}개") for k, v in out.items()}, ensure_ascii=False), flush=True)
