#!/bin/bash
# 정직 캐시 비교 판 2(GPT #457 4차 고침) — 정확한 명령 기록
S=/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad
cd $S/m54tree
run_cut(){ NRL_CACHE=/tmp/maxret-0026-cache.pkl PYTHONHASHSEED=0 EX_HC=$S/mpos23/honest_cache.py EX_MODE=CUT EX_CUT=$1 EX_FULL=$S/hc/full.json.pkl EX_OUT=$S/hc2/cut_$1.json EX_TMP=$S/hc2/tmp_$1 python3 $S/r8/research-exchange/claude-to-gpt/MPOS-0010/tree_run.py $S/hc2/cut_$1.mods.json $S/mpos23/run_honest.py > $S/hc2/cut_$1.log 2>&1; echo "$1 끝 $?"; rm -rf $S/hc2/tmp_$1; }
SECONDS=0
run_cut 20181228 & run_cut 20201230 & wait
run_cut 20220615 & run_cut 20221229 & wait
run_cut 20241230
NRL_CACHE=/tmp/maxret-0026-cache.pkl PYTHONHASHSEED=0 EX_HC=$S/mpos23/honest_cache.py EX_MODE=OLD EX_FULL=$S/hc/full.json.pkl EX_LEDGER=$S/z055_d1_raw.json EX_OUT=$S/hc2/old.json python3 $S/r8/research-exchange/claude-to-gpt/MPOS-0010/tree_run.py $S/hc2/old.mods.json $S/mpos23/run_honest.py > $S/hc2/old.log 2>&1; echo "OLD 끝 $?"
echo "${SECONDS}초 끝"
