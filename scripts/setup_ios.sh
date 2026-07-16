#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../ios-app"

# Install xcodegen if not present
if ! command -v xcodegen &> /dev/null; then
    echo "Installing xcodegen..."
    brew install xcodegen
fi

echo "Generating Xcode project..."
xcodegen generate

echo "Done! You can now open ios-app/Ipadtrackapd.xcodeproj"
