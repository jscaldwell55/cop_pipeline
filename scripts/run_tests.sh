#!/bin/bash
# File: scripts/run_tests.sh

# Run all tests

set -e

echo "=== Running CoP Pipeline Tests ==="

# Activate virtual environment
source venv/bin/activate

# Run tests with coverage
echo "Running pytest with coverage..."
pytest tests/ \
    --cov=. \
    --cov-report=html \
    --cov-report=term \
    -v \
    --tb=short

echo "✓ Tests complete!"
echo "Coverage report: htmlcov/index.html"