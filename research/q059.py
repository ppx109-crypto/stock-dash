"""RNA 22라운드(15분봉) — D3 60일 오름 문턱(+20%)을 흔들림 맞춤(VX: 60일 오름 ≥ z × 변동성 × √60)으로 바꿔 22회차 후보에.
Q_VX=z(비우면 DNA). 일봉 재료(추세 문)는 hlab.daily_tables에서만 바꿈 · 전 거래일 값 그대로(미래 참조 없음). 161종목 · 씨앗 16 · 두 반."""
import inspect
import os
import sys
sys.path.insert(0, "/home/user/stock-dash")
sys.path.insert(0, "/home/user/stock-dash/research")
import hlab as _H

if os.environ.get("Q_VX"):
    _z = float(os.environ["Q_VX"])
    _src = inspect.getsource(_H.daily_tables).replace(
        '(r.get("60일 전 대비") or -99) >= rule.SIXTY',
        f'(r.get("60일 전 대비") or -99) >= {_z} * (r.get("변동성") or 99) * 60 ** 0.5')
    assert "60 ** 0.5" in _src
    exec(_src, _H.__dict__)
exec(open("/home/user/stock-dash/research/q027.py", encoding="utf-8").read().split('\npart = os.environ')[0])
print(f"== 15분봉 RNA 22라운드: 60일 문턱 {'VX ' + os.environ['Q_VX'] if os.environ.get('Q_VX') else 'DNA +20%'} ({len(data)}종목) ==", flush=True)
go("22회차 후보")
