#!/bin/sh
set -e

# Install dependencies if node_modules is missing or incomplete
# Check for vite to ensure all deps are present
if [ ! -d "node_modules" ] || [ ! -d "node_modules/vite" ]; then
  echo "⚠️  Dependencies missing or incomplete, installing..."
  # Note: --legacy-peer-deps is used to handle peer dependency conflicts
  # between React 18 and some older packages. This is a temporary workaround.
  # See PEER_DEPENDENCY_CONFLICTS.md for details.
  # TODO: Resolve peer dependency conflicts properly by upgrading conflicting packages.
  npm install --legacy-peer-deps
  echo "✅ Dependencies installed"
fi

# Serve the dist folder on port 3000 (Vite output directory)
echo "✅ Starting production server..."
exec serve -s dist -l 3000
