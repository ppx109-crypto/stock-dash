#!/bin/bash
# MPOS-0027 대조 판 2(confirm27 v2: nrl을 로더 바꿔 끼우기 뒤에 import) — 정확한 명령 기록 · 동시에 2개씩
S=/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad
TR=$S/r8/research-exchange/claude-to-gpt/MPOS-0010/tree_run.py
cd $S/m54tree
c27(){ name=$1; v=$2; shift 2; env CAPS_ADJ=0 NRL_CACHE=$S/c27/nrl_$v.pkl PYTHONHASHSEED=0 EX_HC=$S/mpos27/honest_cache.py EX_FULL=$S/hc3/full_$( [ $v = N ] && echo next || echo same ).json.pkl EX_OUT=$S/c27/$name.json "$@" python3 $TR $S/c27/$name.mods.json $S/mpos27/confirm27.py > $S/c27/$name.log 2>&1; echo "$name $?"; }
SECONDS=0
c27 pre_N N EX_MODE=PRE & c27 pre_S S EX_MODE=PRE & wait
c27 led_N N EX_MODE=LED EX_LED=$S/c27/ledger_N.json & c27 led_S S EX_MODE=LED EX_LED=$S/c27/ledger_S.json & wait
c27 sig_N N EX_MODE=SIG & c27 lead1_N N EX_MODE=LED EX_MUT=lead1 & wait
c27 lag0_N N EX_MODE=LED EX_MUT=lag0 & c27 dp_N N EX_MODE=LED EX_DPOISON=20240102 & wait
c27 dp_lag0 N EX_MODE=LED EX_MUT=lag0 EX_DPOISON=20240102
for c in 20201230 20221229 20241230; do
  c27 cut_d_$c N EX_MODE=LED EX_FCUT=$c EX_FMODE=drop EX_LED=$S/c27/ledger_cd$c.json & c27 cut_p_$c N EX_MODE=LED EX_FCUT=$c EX_FMODE=poison & wait
  c27 lead1_d_$c N EX_MODE=LED EX_MUT=lead1 EX_FCUT=$c EX_FMODE=drop & c27 lead1_p_$c N EX_MODE=LED EX_MUT=lead1 EX_FCUT=$c EX_FMODE=poison & wait
done
for c in 20201230 20221229 20241230; do
  c27 cmp_d_$c N EX_MODE=CMP EX_CUT=$c EX_A=$S/c27/led_N.json.events.json EX_B=$S/c27/cut_d_$c.json.events.json
  c27 cmp_p_$c N EX_MODE=CMP EX_CUT=$c EX_A=$S/c27/led_N.json.events.json EX_B=$S/c27/cut_p_$c.json.events.json
  c27 cmp_lead1d_$c N EX_MODE=CMP EX_CUT=$c EX_A=$S/c27/lead1_N.json.events.json EX_B=$S/c27/lead1_d_$c.json.events.json
  c27 cmp_lead1p_$c N EX_MODE=CMP EX_CUT=$c EX_A=$S/c27/lead1_N.json.events.json EX_B=$S/c27/lead1_p_$c.json.events.json
done
c27 cmp_dp_N N EX_MODE=CMP EX_CUT=20240102 EX_A=$S/c27/led_N.json.events.json EX_B=$S/c27/dp_N.json.events.json
c27 cmp_dp_lag0 N EX_MODE=CMP EX_CUT=20240102 EX_A=$S/c27/lag0_N.json.events.json EX_B=$S/c27/dp_lag0.json.events.json
echo "${SECONDS}초 끝"
# 추가(결과 본 뒤 · 도구 검출력 시험): 당일 독 날 = lag0 판 2022 ~ 2024 매수 최다 날 20230602 · dp2_N · dp2_lag0 · cmp_dp2_*
