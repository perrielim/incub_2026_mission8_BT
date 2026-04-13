#!/usr/bin/env bash
set -e

# Python env fix
python3 -m pip install --break-system-packages -r requirements.txt

# Generate plan + XML
# python3 scripts/planner_agent.py
# python3 scripts/compile_bt.py

# Clean + build
rm -rf build
cmake -S . -B build
cmake --build build -j

# Run
./build/bt_runner