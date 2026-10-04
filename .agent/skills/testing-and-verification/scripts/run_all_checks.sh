#!/usr/bin/env bash
#
# scripts/run_all_checks.sh
#
# Usage:
#     bash scripts/run_all_checks.sh
#     ./scripts/run_all_checks.sh
#
# Description:
#     Unified quality verification script for the Marketplace Keyword Agent project.
#     Executes Python linting (ruff), backend unit & integration tests (pytest),
#     TypeScript static type checking (tsc), frontend tests (vitest), and production
#     build verification (vite build).
#
# Exit codes:
#     0 if all suites pass, 1 if any check fails.
#

set -e

echo "=========================================================="
echo "RUNNING ALL QUALITY CHECKS: Marketplace Keyword Agent"
echo "=========================================================="

FAILED=0

# 1. Python Linting & Formatting (Ruff)
echo -e "\n[1/5] Checking Python linting with ruff..."
if command -v ruff &> /dev/null; then
    ruff check backend/ || FAILED=1
else
    echo "  [SKIP] ruff not found in PATH. Install with 'pip install ruff'."
fi

# 2. Python Tests (pytest with pytest-asyncio & respx)
echo -e "\n[2/5] Running backend test suite with pytest..."
if command -v pytest &> /dev/null; then
    pytest tests/ -v || FAILED=1
else
    echo "  [SKIP] pytest not found in PATH. Install with 'pip install pytest pytest-asyncio respx'."
fi

# 3. TypeScript Type Checking (tsc --noEmit)
echo -e "\n[3/5] Checking TypeScript types (tsc --noEmit)..."
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    (cd frontend && npx tsc --noEmit) || FAILED=1
else
    echo "  [SKIP] frontend directory or package.json not found."
fi

# 4. Frontend Unit Tests (Vitest)
echo -e "\n[4/5] Running frontend unit tests (Vitest)..."
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    (cd frontend && npx vitest run) || FAILED=1
else
    echo "  [SKIP] frontend directory or package.json not found."
fi

# 5. Production Bundle Verification (Vite build)
echo -e "\n[5/5] Testing production bundle compilation (vite build)..."
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    (cd frontend && npm run build) || FAILED=1
else
    echo "  [SKIP] frontend directory or package.json not found."
fi

echo -e "\n=========================================================="
if [ $FAILED -eq 0 ]; then
    echo "ALL VERIFICATION CHECKS PASSED SUCCESSFULLY [OK]"
    echo "=========================================================="
    exit 0
else
    echo "VERIFICATION CHECKS FAILED [ERROR]"
    echo "=========================================================="
    exit 1
fi
