#!/usr/bin/env bash
# 15분봉 연구 실험 줄 세워 돌리기(사용자 2026-10-02 "한 회차에 연구시간 남는 것 같은데 더 효율적으로").
# 쓰는 법: research/qqueue.sh 줄파일 [동시에 몇 개, 기본 3] [마감 분, 기본 45]
#   줄파일 한 줄 = "이름|환경변수들|스크립트"  예) q040a|Q_PART=1|research/q040.py
# 결과: $SP/out/이름.out · 다 끝나면 $SP/out/_끝_줄파일이름 표시. 마감 분이 지나면 새 줄은 띄우지 않음(도는 것은 끝까지).
# 이동평균 상태는 HLAB_ST_CACHE에 남겨 두 번째부터 준비가 90초 → 1초.
set -u
LIST="$1"; JOBS="${2:-3}"; LIMIT_MIN="${3:-45}"
SP="${SP:-/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad}"
export HLAB_ST_CACHE="${HLAB_ST_CACHE:-$SP/stcache}"
export M15_HOME="${M15_HOME:-$SP/m15snap161}"
mkdir -p "$SP/out"
START=$(date +%s)
run_one() {
  IFS='|' read -r name envs script <<< "$1"
  if [ $(( ($(date +%s) - START) / 60 )) -ge "$LIMIT_MIN" ]; then echo "마감 지나 건너뜀" > "$SP/out/$name.out"; return; fi
  env $envs timeout 2700 python3 -u "$script" > "$SP/out/$name.out" 2>&1
}
export -f run_one; export START LIMIT_MIN SP
grep -v '^\s*#' "$LIST" | grep -v '^\s*$' | xargs -d '\n' -P "$JOBS" -I{} bash -c 'run_one "$@"' _ {}
touch "$SP/out/_끝_$(basename "$LIST")"
