"""RNA 22라운드(15분봉) — D3 60일 오름 문턱(+20%)을 흔들림 맞춤(VX: 60일 오름 ≥ z × 변동성 × √60)으로 바꿔 22회차 후보에.
Q_VX=z(비우면 DNA). 일봉 재료(추세 문)는 hlab.daily_tables에서만 바꿈 · 전 거래일 값 그대로(미래 참조 없음). 161종목 · 씨앗 16 · 두 반."""
import inspect
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import hlab as _H

if os.environ.get("Q_VX"):
    # hlab.cached_tables(.cache 저장본)를 그대로 두고 추세 문 표만 바꿔 끼움 — 표는 일봉 표 한 번 읽어 DNA · VX를 함께 구운 것
    #  (scratchpad r22/build.py · DNA 판이 저장본과 474건 모두 같음을 확인)
    import pickle as _pk
    from pathlib import Path as _P
    _orig = _H.cached_tables
    _tr = _pk.load(open(os.environ.get("Q_TREND_DIR", "") + f"/trend_{os.environ['Q_VX']}.pkl", "rb"))

    def _cached(since="20220101"):
        saved = _pk.loads((_P(".cache") / "hourly_tables.pkl").read_bytes())
        return _H._limit_tables(saved["ranks"], _tr)
    _H.cached_tables = _cached
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])
print(f"== 15분봉 RNA 22라운드: 60일 문턱 {'VX ' + os.environ['Q_VX'] if os.environ.get('Q_VX') else 'DNA +20%'} ({len(data)}종목) ==", flush=True)
go("22회차 후보")
