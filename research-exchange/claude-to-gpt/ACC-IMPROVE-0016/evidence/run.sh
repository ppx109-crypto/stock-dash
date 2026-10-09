#!/bin/bash
cd /home/user/stock-dash
S=/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/imp16
run() {
  name=$1; shift
  env NRL_CACHE=/tmp/nrl-cache.pkl Z_ACC_VOL=0.010911 "$@" Z_OUT=$S/nav/$name.csv python3 research/z094.py > $S/log/$name.log 2>&1
  echo "$name 끝 $?"
}
export -f run; export S
cat <<L | xargs -P 4 -L 1 bash -c 'run "$@"' _
F Z_TRIM_BAND=0
band02 Z_TRIM_BAND=0.02
band05 Z_TRIM_BAND=0.05
band10 Z_TRIM_BAND=0.10
L
