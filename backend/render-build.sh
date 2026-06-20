#!/usr/bin/env bash
set -o errexit

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

echo "==> Build complete."
