#!/usr/bin/env bash
set -e

echo "==========================================="
echo "   Argus AI — macOS Build & Package Tool   "
echo "==========================================="

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH."
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is not installed or not in PATH."
    exit 1
fi

echo "📦 1. Installing Node.js dependencies..."
npm install

echo "🐍 2. Installing Python dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "🎨 3. Building React Frontend (Vite)..."
npm run build:frontend

echo "⚙️ 4. Compiling Python Backend for macOS..."
npm run build:backend

echo "🍎 5. Packaging macOS Application (.dmg & .zip)..."
npx electron-builder --mac

echo "==========================================="
echo "✅ Build completed successfully!"
echo "📁 Output files available in release/"
echo "   - Argus AI-2.0.0.dmg (Installer)"
echo "   - Argus AI-2.0.0-mac.zip (Archive)"
echo "==========================================="
