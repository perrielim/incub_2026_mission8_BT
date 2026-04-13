#!/usr/bin/env bash
set -euo pipefail

# python3 scripts/planner_agent.py
# python3 scripts/compile_bt.py
cmake -S . -B build
cmake --build build -j
./build/bt_runner