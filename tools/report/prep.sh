#!/usr/bin/env bash
# 리포트 준비를 명령 한 번으로 (11-22). 저장소 맨 위에서 실행해요.
#   bash tools/report/prep.sh            # 가장 최근 판
#   bash tools/report/prep.sh KR_...     # 고른 판
# 하는 일: 리포트 데이터 만들기 → 피드백용 요약 한 장 + 그 판에 필요한 규칙 장을 한 번에 출력.
# 화면 빌드는 그동안 뒤에서 미리 해 둬요(끝나면 /tmp/web_ready). 출력은 /tmp/prep_<ID>.txt 에도 남아요.
set -euo pipefail
cd "$(dirname "$0")/../.."
ID="${1:-$(ls raw/ | grep -E '^KR_[0-9]+\.json\.gz$' | sed 's/\.json\.gz//' | sort -t_ -k2 -n | tail -1)}"

rm -f /tmp/web_ready; touch /tmp/web_building
setsid nohup bash -c 'trap "rm -f /tmp/web_building" EXIT; (cd web && { [ -d node_modules ] || npm ci --silent; } && npm run build:single --silent) \
  && { python3 -c "import brotli" 2>/dev/null || pip install -q --break-system-packages brotli; } && touch /tmp/web_ready' \
  >/tmp/web_build.log 2>&1 </dev/null &

python3 tools/report/report_data.py "$ID" >/tmp/report_data.log 2>&1 || { tail -5 /tmp/report_data.log; exit 1; }
{
  python3 tools/report/fb_brief.py "$ID"
  ROLE=$(python3 - "$ID" <<'PY'
import gzip, json, sys
m = json.load(gzip.open(f"raw/{sys.argv[1]}.json.gz"))["match"]["info"]["participants"]
me = [p for p in m if p.get("riotIdGameName") == "Certa"]
print(me[0]["teamPosition"] if me else "BOTTOM")
PY
)
  echo; echo "======== 규칙 (knowledge/rules.md, 역할 $ROLE) ========"
  # 글쓰기부터 원딜 체크리스트까지(미드/서폿 장 앞까지) + 역할에 맞는 장
  awk '/^## 글쓰기/{on=1} /^### 미드/{on=0} on' knowledge/rules.md
  case "$ROLE" in
    MIDDLE)  awk '/^### 미드/{on=1;print;next} /^###? /{on=0} on' knowledge/rules.md ;;
    UTILITY) awk '/^### 서폿/{on=1;print;next} /^###? /{on=0} on' knowledge/rules.md ;;
  esac
  PUB=$(python3 -c "import json,sys;print(sys.argv[1] in json.load(open('tools/report/public.json'))['public'])" "$ID")
  echo; echo "======== 다음 ========"
  if [ "$PUB" = True ]; then FB="feedback/$ID.json"; else FB="tools/report/private-feedback/$ID.json"; fi
  echo "피드백 파일: $FB  →  쓴 뒤 bash tools/report/finish.sh $ID"
} | tee "/tmp/prep_$ID.txt"
