#!/usr/bin/env bash
# 피드백을 쓴 뒤 리포트를 명령 한 번으로 마무리 (11-22). 저장소 맨 위에서 실행해요.
#   bash tools/report/finish.sh KR_...
# 하는 일: 피드백 파일 검사 → 리포트 데이터 → (prep.sh가 미리 해 둔) 화면 빌드 → 한 파일 리포트 → 글자/오류 확인
#          → 비공개 판이면 피드백 사본을 /mnt/user-data/outputs/ 에 두고 PC 저장 경로를 알려 줘요.
set -euo pipefail
cd "$(dirname "$0")/../.."
ID="$1"
if [ -f "feedback/$ID.json" ]; then FB="feedback/$ID.json"; PRIV=0; else FB="tools/report/private-feedback/$ID.json"; PRIV=1; fi
[ -f "$FB" ] || { echo "피드백 파일이 없어요: $FB"; exit 1; }
python3 -c "import json,sys; json.load(open(sys.argv[1], encoding='utf-8'))" "$FB" || { echo "피드백 JSON 형식 오류"; exit 1; }
DOTS=$( (grep -o '·' "$FB" || true) | wc -l); [ "$DOTS" -eq 0 ] || echo "주의: 피드백에 가운뎃점 ${DOTS}개"

for i in $(seq 1 120); do [ -f /tmp/web_ready ] && break; sleep 1; done
if [ ! -f /tmp/web_ready ]; then   # prep.sh 없이 왔거나 뒤 빌드가 실패했으면 여기서 빌드해요
  (cd web && { [ -d node_modules ] || npm ci --silent; } && npm run build:single --silent) >/dev/null
  python3 -c "import brotli" 2>/dev/null || pip install -q --break-system-packages brotli
fi
python3 tools/report/report_data.py "$ID" >/tmp/report_data.log 2>&1 || { tail -5 /tmp/report_data.log; exit 1; }
python3 tools/report/single.py "$ID"
python3 tools/report/check_page.py "$ID"
python3 tools/report/fb_brief.py "$ID" | grep '^artifact 제목'
echo "올릴 파일: $(pwd)/tools/report/${ID}_single.html"
if [ "$PRIV" = 1 ]; then
  mkdir -p /mnt/user-data/outputs && cp "$FB" "/mnt/user-data/outputs/$ID.json"
  echo "PC 저장: /mnt/user-data/outputs/$ID.json → C:\\Users\\tstor\\Documents\\기타\\아카이브\\ranked-archive-workfiles\\feedback\\$ID.json"
fi
