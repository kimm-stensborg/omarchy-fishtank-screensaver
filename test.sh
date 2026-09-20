#!/bin/bash
# Run the checks. ./test.sh --quick skips the slower sweeps.
exec python3 "$(dirname "${BASH_SOURCE[0]}")/tools/test.py" "$@"
