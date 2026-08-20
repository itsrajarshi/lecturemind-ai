#!/usr/bin/env bash
# Render build script. Runs from the `backend/` root directory.
set -euo pipefail

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Building frontend..."
cd ../frontend
npm ci
npm run build

echo "==> Copying frontend build to backend/static..."
rm -rf ../backend/static
mkdir -p ../backend/static
cp -r dist/* ../backend/static/

echo "==> Verifying backend imports..."
cd ../backend
python -c "import app"

echo "==> Build complete."