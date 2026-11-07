#!/bin/bash
# MPOS-0027 바탕 대조(z100c · 손익 요약 없음) — 정확한 명령 기록
S=/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad
python3 $S/mpos27/make_z100c.py $S/r8/research-exchange/claude-to-gpt/MPOS-0012/z100g.py $S/c27/z100c.py
python3 $S/mpos27/perturb27.py $S/c27/ledger_N.json $S/c27/ledger_Q.json $S/c27/nrl_N.pkl
cd $S/m54tree
ENVS="Z_ACC_VOL=0.010911 Z_FROM=20170201 Z_TO=20260930 Z_MARGIN=1.30 Z_ACC=1e8 Z_D1_VOL=0 Z_LOOK=20 Z_ACC_STRICT=1 Z_STOCK_CAP=0 Z_PARK=0 Z_BASKET_BEAR=0 Z_STOCK_VOL=0 Z_TRIM_BAND=0 Z_SHARE_1D=0.5 Z_SHARE_15M=0.5 Z_SHARE_BASKET=0.3 PYTHONHASHSEED=0 Z_DROP=15m CAPS_ADJ=0"
zc(){ env -i PATH=$PATH HOME=$HOME LANG=$LANG $ENVS NRL_CACHE=$S/c27/nrl_N.pkl Z_D1_LED=$2 Z_OUT=$S/c27/zc_$1.csv Z_EVT=$S/c27/zc_$1.evt.json python3 $S/r8/research-exchange/claude-to-gpt/MPOS-0010/tree_run.py $S/c27/zc_$1.mods.json $S/c27/z100c.py > $S/c27/zc_$1.log 2>&1; echo "z100c $1 $?"; }
zc N $S/c27/ledger_N.json & zc cd20201230 $S/c27/ledger_cd20201230.json & zc cd20221229 $S/c27/ledger_cd20221229.json & wait
zc cd20241230 $S/c27/ledger_cd20241230.json & zc Q $S/c27/ledger_Q.json & wait
cd $S/c27 && python3 $S/mpos27/c27_nav.py $S/c27/nav_cmp.json zc_N.csv zc_N.evt.json cd20201230 zc_cd20201230.csv zc_cd20201230.evt.json 20201230 cd20221229 zc_cd20221229.csv zc_cd20221229.evt.json 20221229 cd20241230 zc_cd20241230.csv zc_cd20241230.evt.json 20241230 Q zc_Q.csv zc_Q.evt.json 20211231
