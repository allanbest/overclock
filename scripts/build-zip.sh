#!/usr/bin/env bash
# Build dist/overclock.zip for Claude Cowork plugin upload.
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf dist && mkdir -p dist/stage
cp -R .claude-plugin claude-agents hooks skills assets plugin.json hooks.json README.md LICENSE dist/stage/

# Strip macOS metadata and Python bytecode caches from staged bundle
find dist/stage -name '.DS_Store' -delete
find dist/stage -name '__pycache__' -type d -exec rm -rf {} +
find dist/stage -name '*.pyc' -delete

(cd dist/stage && zip -qr ../overclock.zip .)
rm -rf dist/stage
echo "Built:"
ls -lh dist/overclock.zip
