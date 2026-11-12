#!/bin/bash
# MIX-0054 정직 캐시 재셈 — 바탕(z100g) 세 판 · 정확한 명령 기록(환경 = mpos12.ENV 그대로 · NRL_CACHE · Z_D1_LED만 칸마다)
S=/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad
cd $S/m54tree
ENVS="Z_ACC_VOL=0.010911 Z_FROM=20170201 Z_TO=20260930 Z_MARGIN=1.30 Z_ACC=1e8 Z_D1_VOL=0 Z_LOOK=20 Z_ACC_STRICT=1 Z_STOCK_CAP=0 Z_PARK=0 Z_BASKET_BEAR=0 Z_STOCK_VOL=0 Z_TRIM_BAND=0 Z_SHARE_1D=0.5 Z_SHARE_15M=0.5 Z_SHARE_BASKET=0.3 PYTHONHASHSEED=0 Z_DROP=15m CAPS_ADJ=0"
run(){ env -i PATH=$PATH HOME=$HOME LANG=$LANG $ENVS NRL_CACHE=$2 Z_D1_LED=$3 Z_OUT=$S/rc/base_$1.csv python3 $S/r8/research-exchange/claude-to-gpt/MPOS-0010/tree_run.py $S/rc/base_$1.mods.json /tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/r8/research-exchange/claude-to-gpt/MPOS-0012/z100g.py > $S/rc/base_$1.log 2>&1; echo "$1 끝 $?"; }
SECONDS=0
run REPRO_G /tmp/maxret-0026-cache.pkl $S/z055_d1_raw.json &
run HONEST $S/rc/nrl_honest.pkl $S/rc/led_HONEST.json &
run HLED_OLDNRL /tmp/maxret-0026-cache.pkl $S/rc/led_HONEST.json &
wait
echo "${SECONDS}초 끝"
