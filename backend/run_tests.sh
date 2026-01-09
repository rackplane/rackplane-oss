#!/bin/bash
# Helper script to run tests inside Docker container

echo "Running DCMS Test Suite..."
echo "=========================="
echo ""

# Check if Docker is running
if ! docker compose ps backend > /dev/null 2>&1; then
    echo "ERROR: Backend container is not running!"
    echo "Please start the services first:"
    echo "  docker compose up -d"
    exit 1
fi

# Run tests inside the backend container
docker compose exec backend python test_suite.py

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "✓ All tests passed!"
else
    echo ""
    echo "✗ Some tests failed (exit code: $exit_code)"
fi

exit $exit_code

