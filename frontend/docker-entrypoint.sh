#!/bin/sh
# node_modules lives in a named volume that outlives image rebuilds, so
# reinstall whenever package-lock.json no longer matches what is installed.
set -e
if ! cmp -s package-lock.json node_modules/.lock-stamp; then
  echo "package-lock.json changed: running npm ci"
  npm ci --no-audit --no-fund
  cp package-lock.json node_modules/.lock-stamp
fi
exec "$@"
