#!/usr/bin/env bash
# 重启 weave-note。
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
"$DIR/script/linux/stop.sh"
"$DIR/script/linux/start.sh"
