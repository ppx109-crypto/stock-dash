#!/bin/bash
# 판 3 다섯 컷(next · 공시 접수일 ≤ c) + 당일 공시 누수 대조(c* = 20200330 · 공시 접수일 < c* · same · next) — 정확한 명령 기록
S=/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad
cd $S/m54tree
run(){ CAPS_ADJ=0 NRL_CACHE=/tmp/maxret-0026-cache.pkl PYTHONHASHSEED=0 EX_HC=$S/mpos27/honest_cache.py EX_MODE=CUT EX_SHARES=$2 EX_CUT=$3 EX_FSTRICT=$4 EX_FULL=$S/hc3/full_$2.json.pkl EX_OUT=$S/hc3/$1.json EX_TMP=$S/hc3/tmp_$1 python3 $S/r8/research-exchange/claude-to-gpt/MPOS-0010/tree_run.py $S/hc3/$1.mods.json $S/mpos27/run_honest.py > $S/hc3/$1.log 2>&1; echo "$1 끝 $?"; rm -rf $S/hc3/tmp_$1; }
SECONDS=0
run cut_20181228 next 20181228 0 & run cut_20201230 next 20201230 0 & wait
run cut_20220615 next 20220615 0 & run cut_20221229 next 20221229 0 & wait
run cut_20241230 next 20241230 0 & run leak_next next 20200330 1 & wait
run leak_same same 20200330 1
echo "${SECONDS}초 끝"
