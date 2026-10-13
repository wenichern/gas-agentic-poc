#!/usr/bin/env bash
# POC folders reuse module names (agent, tools, llm), so each POC's tests run in their own pytest process.
set -e
cd "$(dirname "$0")/.."
python -m pytest -q tests/test_poc1.py tests/test_poc1_streaming.py
python -m pytest -q tests/test_poc3.py
