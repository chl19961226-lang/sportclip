#!/usr/bin/env bash
# 一键启动后端 + 前端（开发模式）
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------- backend ----------
cd "$ROOT/backend"
# 优选更稳定的解释器（某些依赖在 3.14 尚无 wheel）
PY=""
for cand in python3.11 python3.12 python3.13 python3; do
  if command -v "$cand" >/dev/null 2>&1; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then echo "未找到 python3，请先安装"; exit 1; fi
echo "using $PY ($($PY --version))"

if [ ! -d .venv ]; then
  "$PY" -m venv .venv
  source .venv/bin/activate
  pip install -U pip
  pip install -r requirements.txt
else
  source .venv/bin/activate
fi
[ -f .env ] || cp .env.example .env
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# ---------- frontend ----------
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  npm install
fi
npm run dev &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true" EXIT
echo "Backend  : http://localhost:8000"
echo "Frontend : http://localhost:3000"
wait
