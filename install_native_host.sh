#!/usr/bin/env bash
set -euo pipefail

HOST_NAME="com.v0rt3x.ytdlp_bridge"
EXTENSION_ID="ytdlp-bridge@example.local"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_HOST_SCRIPT="${SCRIPT_DIR}/native-host/ytdlp_bridge_host.py"

TARGET_DIR="${HOME}/.local/share/ytdlp-bridge"
TARGET_HOST_SCRIPT="${TARGET_DIR}/ytdlp_bridge_host.py"
MANIFEST_DIR="${HOME}/.mozilla/native-messaging-hosts"
MANIFEST_PATH="${MANIFEST_DIR}/${HOST_NAME}.json"

mkdir -p "${TARGET_DIR}"
mkdir -p "${MANIFEST_DIR}"

cp "${SOURCE_HOST_SCRIPT}" "${TARGET_HOST_SCRIPT}"
chmod 755 "${TARGET_HOST_SCRIPT}"

cat > "${MANIFEST_PATH}" <<EOF
{
  "name": "${HOST_NAME}",
  "description": "Native host for YouTube yt-dlp bridge",
  "path": "${TARGET_HOST_SCRIPT}",
  "type": "stdio",
  "allowed_extensions": [
    "${EXTENSION_ID}"
  ]
}
EOF

echo "Installed native host manifest: ${MANIFEST_PATH}"
echo "Host script: ${TARGET_HOST_SCRIPT}"
