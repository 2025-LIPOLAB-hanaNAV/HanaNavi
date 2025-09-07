#!/usr/bin/env bash
set -euo pipefail

ETL_BASE="${ETL_BASE:-http://localhost:8002}"
ID="${1:-$(date +%s)}"
DATE_UTC="$(date -u +"%Y-%m-%d")"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

PDF_PATH="$TMPDIR/voice_phishing_notice.pdf"

# Create a tiny placeholder PDF-like file (not fully rendered but sufficient as an attachment test)
# We force content-type to application/pdf on upload.
cat > "$PDF_PATH" << 'EOF'
%PDF-1.1
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R >> endobj
4 0 obj << /Length 44 >> stream
BT /F1 12 Tf 50 150 Td (Voice Phishing Notice) Tj ET
endstream endobj
trailer << /Root 1 0 R /Size 5 >>
%%EOF
EOF

echo "Uploading attachment to ${ETL_BASE}/upload ..." >&2
UP_JSON=$(curl -sS -F "file=@${PDF_PATH};type=application/pdf" "${ETL_BASE}/upload")
echo "$UP_JSON" | jq . >&2 || true

FILENAME=$(echo "$UP_JSON" | jq -r .filename)
SHA1=$(echo "$UP_JSON" | jq -r .sha1)
URL=$(echo "$UP_JSON" | jq -r .url)
PUB=$(echo "$UP_JSON" | jq -r .public_url)

read -r -d '' PAYLOAD << 'JSON'
{
  "action": "post_created",
  "post_id": __POST_ID__,
  "title": "보이스피싱 주의 안내(첨부 포함)",
  "body": "첨부된 안내문을 참고하세요. 주요 수법과 대응 절차가 정리되어 있습니다.",
  "tags": ["보이스피싱","보안","공지"],
  "category": "Notice",
  "date": "__DATE__",
  "severity": "medium",
  "attachments": [
    {"filename": "__FILENAME__", "url": "__URL__", "sha1": "__SHA1__", "public_url": "__PUBLIC__"}
  ]
}
JSON

PAYLOAD="${PAYLOAD/__POST_ID__/$ID}"
PAYLOAD="${PAYLOAD/__DATE__/$DATE_UTC}"
PAYLOAD="${PAYLOAD/__FILENAME__/$FILENAME}"
PAYLOAD="${PAYLOAD/__URL__/$URL}"
PAYLOAD="${PAYLOAD/__SHA1__/$SHA1}"
PAYLOAD="${PAYLOAD/__PUBLIC__/$PUB}"

echo "Seeding sample post with attachment (post_id=${ID}) ..." >&2
curl -sS -X POST "${ETL_BASE}/ingest/webhook" -H 'Content-Type: application/json' -d "$PAYLOAD" | jq . || true

echo "Seed complete. Post ${ID} now has one PDF attachment."

