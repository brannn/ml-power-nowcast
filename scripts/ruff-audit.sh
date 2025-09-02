#!/usr/bin/env bash
# Ruff audit script - checks only, no modifications

set -euo pipefail

echo "🔍 Running Ruff Audit (Check-Only Mode)"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track if any issues found
HAS_ISSUES=0

# Run Ruff check (linting)
echo "📋 Checking code style and linting issues..."
if ruff check src/ tests/ --no-fix --statistics; then
    echo -e "${GREEN}✓ No linting issues found${NC}"
else
    echo -e "${YELLOW}⚠ Linting issues detected (see above)${NC}"
    HAS_ISSUES=1
fi

echo ""

# Run Ruff format check
echo "📐 Checking code formatting..."
if ruff format src/ tests/ --check > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Code formatting is correct${NC}"
else
    echo -e "${YELLOW}⚠ Formatting issues detected. Run 'ruff format --diff src/ tests/' to see differences${NC}"
    HAS_ISSUES=1
fi

echo ""

# Show summary
echo "========================================="
if [ $HAS_ISSUES -eq 0 ]; then
    echo -e "${GREEN}✨ All Ruff checks passed!${NC}"
    exit 0
else
    echo -e "${YELLOW}📝 Ruff found issues that need review${NC}"
    echo ""
    echo "To see detailed formatting differences:"
    echo "  ruff format src/ tests/ --diff"
    echo ""
    echo "To see which files have issues:"
    echo "  ruff check src/ tests/ --no-fix"
    echo ""
    echo "Note: This audit does NOT modify any files."
    echo "Fix issues manually or use 'ruff check --fix' at your own discretion."
    exit 1
fi