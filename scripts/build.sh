#!/usr/bin/env bash
# 构建 weave-note 前端（Vite）并把 dist 部署到 backend/static（后端静态服务目录）。
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$DIR/frontend"
STATIC_DIR="$DIR/backend/static"

cd "$FRONTEND_DIR"
npm install
npm run build

rm -rf "$STATIC_DIR"
mkdir -p "$STATIC_DIR"
cp -R "$FRONTEND_DIR/dist/." "$STATIC_DIR/"
echo "前端构建完成，静态文件已部署到 $STATIC_DIR"
