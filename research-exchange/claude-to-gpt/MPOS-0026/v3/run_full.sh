#!/bin/bash
# 판 3 전체 판 두 개(SHARES_NEXT.md) — 정확한 명령 기록
S=/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad
cd $S/m54tree
full(){ CAPS_ADJ=0 NRL_CACHE=/tmp/maxret-0026-cache.pkl PYTHONHASHSEED=0 EX_HC=$S/mpos27/honest_cache.py EX_MODE=FULL EX_SHARES=$1 EX_OUT=$S/hc3/full_$1.json EX_TMP=$S/hc3/tmp_$1 python3 $S/r8/research-exchange/claude-to-gpt/MPOS-0010/tree_run.py $S/hc3/full_$1.mods.json $S/mpos27/run_honest.py > $S/hc3/full_$1.log 2>&1; echo "$1 끝 $?"; rm -rf $S/hc3/tmp_$1; }
SECONDS=0
full same & full next & wait
echo "${SECONDS}초 끝"
# 같은 모집단 비교(뒤에 붙임 · 따로 실행)
# cd $S/m54tree; CAPS_ADJ=0 NRL_CACHE=/tmp/maxret-0026-cache.pkl PYTHONHASHSEED=0 EX_HC=$S/mpos27/honest_cache.py EX_MODE=COMPARE EX_A=$S/hc3/full_same.json.pkl EX_B=$S/hc3/full_next.json.pkl EX_OUT=$S/hc3/compare.json python3 $S/r8/research-exchange/claude-to-gpt/MPOS-0010/tree_run.py $S/hc3/compare.mods.json $S/mpos27/run_honest.py
