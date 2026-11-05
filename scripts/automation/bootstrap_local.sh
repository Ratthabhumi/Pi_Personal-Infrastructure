#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'BLOCKED: automatic bootstrap/deployment is disabled during recovery.' \
  'Follow docs/recovery/HOMELAB_RECOVERY_REPORT.md after storage/network review.' >&2
exit 1
