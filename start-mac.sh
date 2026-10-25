#!/usr/bin/env bash
set -e

echo "==========================================="
echo "       Argus AI — macOS Launcher           "
echo "==========================================="

if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is required. Install via Homebrew: brew install node"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required. Install via Homebrew: brew install python"
    exit 1
fi

if [ ! -d "node_modules" ]; then
    echo "📦 Installing npm packages..."
    npm install
fi

if [ ! -d "dist" ]; then
    echo "🎨 Building frontend..."
    npm run build
fi

echo "✨ Launching Argus AI..."
npm start
