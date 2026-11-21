#!/usr/bin/env bash
# 피드백 글까지 넣은 뒤 리포트를 한 번에 만들어요 (11-21). 저장소 맨 위에서 실행해요.
#   bash tools/report/make_report.sh KR_8467951138
# 순서: 리포트 데이터 → 화면 빌드(한 번만) → 한 파일 리포트(아이콘 동시 받기)
# 결과: tools/report/<경기ID>_single.html  → publish_files로 artifact에 올려요.
set -euo pipefail
ID="$1"
python3 tools/report/report_data.py "$ID"
if [ ! -d web/node_modules ]; then (cd web && npm ci --silent); fi
(cd web && npm run build:single --silent) > /dev/null
python3 -c "import brotli" 2>/dev/null || pip install -q --break-system-packages brotli 2>/dev/null
python3 tools/report/single.py "$ID"
