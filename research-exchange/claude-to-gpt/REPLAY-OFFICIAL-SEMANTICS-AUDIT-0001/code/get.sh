#!/bin/bash
# 사용: get.sh <이름> <URL>  — 공식 문서 원문을 받아 기록(데이터 API 금지 · 문서 페이지만)
S=/tmp/claude-0/-home-user-stock-dash/bd390ad5-dee2-599f-8c35-772051ecfbb8/scratchpad
N=$1; U=$2
case "$U" in *opendart.fss.or.kr/api/*|*openapi.koreainvestment.com*|*openapivts.koreainvestment.com*|*/oauth2/*|*data.krx.co.kr/comm/bldAttendant*) echo "금지된 데이터 API 경로: $U"; exit 9;; esac
T=$(TZ=Asia/Seoul date -Iseconds)
CODE=$(curl -sS -L --max-time 40 -A "Mozilla/5.0 (research doc audit)" -o $S/od/raw/$N -w '%{http_code}' "$U" 2>$S/od/raw/$N.err)
SZ=$(stat -c %s $S/od/raw/$N 2>/dev/null || echo 0)
H=$(sha256sum $S/od/raw/$N 2>/dev/null | cut -c1-64)
echo "{\"name\":\"$N\",\"url\":\"$U\",\"retrieved_at_kst\":\"$T\",\"http\":\"$CODE\",\"bytes\":$SZ,\"sha256\":\"$H\",\"err\":\"$(head -c 200 $S/od/raw/$N.err | tr -d '\"\n')\"}" | tee -a $S/od/fetch_log.jsonl
