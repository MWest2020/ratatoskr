#!/usr/bin/env bash
# Every check this repository has; CI runs exactly this script. Builders extend
# it with their tests (workflow files are out of their reach, this script is not).
set -euo pipefail
cd "$(dirname "$0")"
if [ -f package.json ]; then npm test; fi
if [ -d tests ] && ls tests/test_*.py >/dev/null 2>&1; then python3 -m unittest discover -s tests; fi
echo "verify: ok"
