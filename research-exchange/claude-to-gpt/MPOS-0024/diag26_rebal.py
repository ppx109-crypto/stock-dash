"""GPT-RNA-C 성과 전 진단(GPT #455 4차 · 새 가설 · 사전등록 아님): MIX-0054 BASE 계좌(regime_dev.account)의 거래를 종류별로 나눔.
account 원문에 기록 줄만 끼워(inspect) 같은 셈을 돌리고 날별 NAV가 원본과 같음을 assert(diag25_cash.py와 같은 조립).
종류: ① 국면 바뀜 맞춤(필수 · 규칙 신호) ② 달 첫날 같은 국면 맞춤(선택적 재맞춤 후보) ③ 띠 벗어남(band=None이라 0이어야 함)
④ ETF 억지 줄이기(1일봉이 현금을 다시 씀 · 필수) ⑤ 1일봉 억지 줄이기(필수).
보고: 종류별 건수 · 거래액(NAV 대비) · 비용 합(절감 상한 = ②의 비용 전부 · 실제 절감은 띠가 일부만 건너뜀 · 보유 이탈 효과는 셈 안 함)
· ② 가운데 거래액이 NAV의 1 · 2 · 5% 미만인 건수. 손익 · 수익률은 출력하지 않음."""
import hashlib
import inspect
import json
import os
import sys
import textwrap
from pathlib import Path

SP = Path(os.environ.get("HUSD_SP", "/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad"))
sys.path.insert(0, str(SP / "r8/research-exchange/claude-to-gpt/MPOS-0012"))
import mpos12 as M  # noqa: E402

Dv = M.Dv
BASE_CSV = Path(os.environ.get("HUSD_BASE_CSV", str(SP / "mpos21/base_BASE.csv")))
Dv.BASE_CSV, Dv.DATA, Dv.FEAT = BASE_CSV, None, None
ref = Dv.account(dict(M.CFG))[0]
src = textwrap.dedent(inspect.getsource(Dv.account))


def ins(after, line):
    global src
    assert src.count(after) == 1, after
    src = src.replace(after, after + line)


ins("            fb, c_new, fe = tgt\n", "            kind = '국면 바뀜' if pending != s_prev else ('달 첫날 같은 국면' if d[:6] != p[:6] else '띠 벗어남')\n"
    "            vb0, ve0, code0 = vb, ve, code\n")
ins("            A -= cost\n", "            LOG.append((d, kind, cost, abs(tb - vb0), (abs(te - ve0) if c_new == code0 else ve0 + te), A + cost, code0, c_new, tb - vb0))\n")
ins("            trims[0] += 1\n", "            LOG.append((d, 'ETF 억지 줄이기', cut * COST_ETF, 0.0, cut, vb + ve + cash, code, code, 0.0))\n")
ins("            trims[1] += 1\n", "            LOG.append((d, '1일봉 억지 줄이기', x * COST_BASE_DOWN, x, 0.0, vb + ve + cash, code, code, -x))\n")
src = src.replace("def account(", "def account_log(")
LOG = []
g = dict(Dv.__dict__)
g["LOG"] = LOG
exec(compile(src, "regime_dev.account+기록", "exec"), g)
Dv.DATA, Dv.FEAT = None, None
navs = g["account_log"](dict(M.CFG))[0]
assert navs == ref, "기록판 NAV가 원본과 다름"
KINDS = ("국면 바뀜", "달 첫날 같은 국면", "띠 벗어남", "ETF 억지 줄이기", "1일봉 억지 줄이기")
summ = {}
for k in KINDS:
    ev = [e for e in LOG if e[1] == k]
    summ[k] = {"건수": len(ev), "비용 합(NAV 비율 합 · 각 건 비용 ÷ 그날 NAV)": round(sum(e[2] / e[5] for e in ev) * 100, 4),
               "1일봉 거래액 ÷ NAV 가운데 %": round(sorted(e[3] / e[5] for e in ev)[len(ev) // 2] * 100, 3) if ev else None,
               "ETF 거래액 ÷ NAV 가운데 %": round(sorted(e[4] / e[5] for e in ev)[len(ev) // 2] * 100, 3) if ev else None}
opt = [e for e in LOG if e[1] == "달 첫날 같은 국면"]
small = {}
for th in (0.01, 0.02, 0.05):
    sel = [e for e in opt if (e[3] + e[4]) / e[5] < th]
    small[f"거래액(1일봉 + ETF) < NAV {int(th * 100)}%"] = {"건수": len(sel), "비용 합 %": round(sum(e[2] / e[5] for e in sel) * 100, 4)}
summ["달 첫날 같은 국면 — 작은 거래"] = small
CB_DOWN, CB_UP, CE = Dv.COST_BASE_DOWN, Dv.COST_BASE_UP, Dv.COST_ETF


def split(e):
    """비용을 1일봉 몫 줄이기(0.30%) · 늘리기(0.05%) · ETF(0.05%)로 나눔(account 비용식 그대로)."""
    db = e[8]
    base_c = CB_DOWN * max(0.0, -db) + CB_UP * max(0.0, db)
    return base_c, e[2] - base_c


for k in KINDS:
    ev = [e for e in LOG if e[1] == k]
    summ[k]["비용 나눔 %(1일봉 몫 · ETF)"] = [round(sum(split(e)[0] / e[5] for e in ev) * 100, 7), round(sum(split(e)[1] / e[5] for e in ev) * 100, 7)]
summ["달 첫날 같은 국면 — 1일봉 몫 거래"] = {"줄이기(0.30%)": sum(1 for e in opt if e[8] < -1e-12), "늘리기(0.05%)": sum(1 for e in opt if e[8] > 1e-12),
                                    "거래 없음": sum(1 for e in opt if abs(e[8]) <= 1e-12)}
tot = sum(e[2] / e[5] for e in LOG)
summ["모든 종류 비용 합 %"] = round(tot * 100, 4)


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


out = {"원본 NAV와 같음": True, "base csv sha256": sha(BASE_CSV), "모듈 지문": {"regime_dev.py": sha(Dv.__file__), "mpos12.py": sha(M.__file__), "이 코드": sha(__file__)},
       "기간": [min(navs), max(navs)], "요약": summ,
       "주의": "비용 합은 원 BASE 경로에서 건마다 '비용 ÷ 그날 NAV'를 더한 직접 비용 예산(복리 아님). 거래를 건너뛰면 보유 · NAV · 다음 목표 · 억지 줄이기가 달라지므로 동적 전략의 총 효과나 연 수익 개선 상한이 아님 · 손익 · 수익률 아님"}
json.dump(out, open(Path(__file__).with_suffix(".json"), "w"), ensure_ascii=False, indent=1)
json.dump(LOG, open(Path(__file__).parent / "rebal_log_base.json", "w"), ensure_ascii=False)
print(json.dumps(out, ensure_ascii=False, indent=1))
