#!/usr/bin/env bash
set -euo pipefail

ETL_BASE="${ETL_BASE:-http://localhost:8002}"
ID="${1:-$(date +%s)}"
DATE_UTC="$(date -u +"%Y-%m-%d")"

read -r -d '' PAYLOAD << 'JSON'
{
  "action": "post_created",
  "post_id": __POST_ID__,
  "title": "보이스피싱 주의 안내",
  "body": "최근 보이스피싱 및 메신저피싱 시도가 증가하고 있습니다.\n\n주요 수법\n- 가족/지인 사칭 후 금전 요구\n- 수사기관/금융기관 사칭하여 개인정보/계좌이체 유도\n- 링크 클릭 유도 후 악성앱 설치\n\n대응 절차\n1) 의심 연락은 즉시 종료 및 차단\n2) 계좌/개인정보를 제공하지 않음\n3) 피해 의심 시 즉시 112 또는 금융감독원 1332 신고\n4) 계좌 지급정지 요청(은행 고객센터)\n\n내부 정책\n- 미확인 파일/앱 설치 금지, 외부 링크 접속 자제\n- 의심 메일/메신저는 보안팀 신고\n\n문의: 보안팀(security@example.com)",
  "tags": ["보이스피싱","보안","공지"],
  "category": "Notice",
  "date": "__DATE__",
  "severity": "high",
  "attachments": []
}
JSON

PAYLOAD="${PAYLOAD/__POST_ID__/$ID}"
PAYLOAD="${PAYLOAD/__DATE__/$DATE_UTC}"

echo "Seeding sample post to ${ETL_BASE}/ingest/webhook (post_id=${ID})"
echo "Payload:" >&2
echo "$PAYLOAD" >&2
curl -v -X POST "${ETL_BASE}/ingest/webhook" -H 'Content-Type: application/json' -d "$PAYLOAD" | jq .

echo "Done. You can now query rag-api and expect citations once indexing finishes."

