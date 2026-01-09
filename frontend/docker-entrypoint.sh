#!/bin/sh
set -e

# Install dependencies if node_modules is missing or incomplete
# Check for both tailwind-merge and react-scripts to ensure all deps are present
if [ ! -d "node_modules" ] || [ ! -d "node_modules/tailwind-merge" ] || [ ! -d "node_modules/react-scripts" ]; then
  echo "⚠️  Dependencies missing or incomplete, installing..."
  npm install
  echo "✅ Dependencies installed"
fi





# Serve the build folder on port 3000
echo "✅ Starting production server..."
exec serve -s build -l 3000

