#!/bin/bash
cd /home/user/stock-dash
S=/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad/imp20
run() {
  name=$1; shift
  env NRL_CACHE=/tmp/nrl-cache.pkl Z_ACC_VOL=0.010911 "$@" Z_OUT=$S/nav/$name.csv python3 research/z096.py > $S/log/$name.log 2>&1
  echo "$name 끝 $?"
}
export -f run; export S
cat <<L | xargs -P 3 -L 1 bash -c 'run "$@"' _
F Z_BASKET_PURE=0
pure Z_BASKET_PURE=1
cut_pure Z_BASKET_PURE=1 Z_TO=20231231
L
mv $S/nav/cut_pure.csv $S/cut_pure_T20231231.csv
