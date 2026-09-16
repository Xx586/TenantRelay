#!/usr/bin/env sh
set -eu

base_url="${TENANTRELAY_BASE_URL:-http://localhost:8000}"
curl --fail --silent --show-error "${base_url}/health"
printf '\nTenantRelay health check passed.\n'
