#!/usr/bin/env sh
set -eu

base_url="${TENANTRELAY_BASE_URL:-http://localhost:8000}"
tenant_id="${SAAS_DEMO_TENANT_ID:-demo-tenant}"
api_key="${SAAS_DEMO_API_KEY:-demo-key-change-me}"

curl --fail --silent --show-error -X POST "${base_url}/chat" \
  -H 'Content-Type: application/json' \
  -H "X-Tenant-ID: ${tenant_id}" \
  -H "X-API-Key: ${api_key}" \
  -d '{"message":"Python SDK 上传接口返回 403，我们刚降级到 basic 套餐","user_id":"demo-user","product":"AcmeCloud","environment":"production"}'
printf '\n'
