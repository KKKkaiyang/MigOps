#!/usr/bin/env bash
# 启动 MigOps 前后端（开发模式）
#
# 用法:
#   ./start.sh            启动后端 + 前端
#   ./start.sh backend    仅启动后端 (uvicorn :8999, --reload)
#   ./start.sh frontend   仅启动前端 (vite :5273, 代理 /api -> 8999)
#
# 说明:
#   - 日志写入 bin/.runtime/logs/，PID 写入 bin/.runtime/pids/
#   - 环境变量可覆盖端口: BACKEND_PORT / FRONTEND_PORT
#   - 后端默认使用 backend/.venv 内的 uvicorn；如需自定义 DB 等环境，
#     请在调用前 export（如 DB_TYPE / MYSQL_URL），脚本不硬编码环境。
#   - 启动后做健康检查：后端探测 /health，前端探测端口监听；
#     任一未就绪会打印日志尾部并以非 0 退出，避免「假启动成功」。

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNTIME_DIR="$SCRIPT_DIR/.runtime"
PID_DIR="$RUNTIME_DIR/pids"
LOG_DIR="$RUNTIME_DIR/logs"
mkdir -p "$PID_DIR" "$LOG_DIR"

WHAT="${1:-all}"
BACKEND_PORT="${BACKEND_PORT:-8999}"
FRONTEND_PORT="${FRONTEND_PORT:-5273}"
BACKEND_HOST="127.0.0.1"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-30}"

command -v curl >/dev/null 2>&1 || { echo "缺少 curl，无法做健康检查" >&2; exit 1; }

# 用全局变量承载 PID，规避 local + $! + set -u 的边界问题
BE_PID=""
FE_PID=""

wait_for_port() {
  local host="$1" port="$2" timeout="$3" i
  for ((i = 0; i < timeout; i++)); do
    if curl -s -m 1 "http://${host}:${port}/" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

start_backend() {
  local pidfile="$PID_DIR/backend.pid"
  if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "后端已在运行 (PID $(cat "$pidfile"))"
    return 0
  fi

  echo "启动后端 (uvicorn :$BACKEND_PORT, --reload) ..."
  cd "$CODE_DIR/backend"

  local cmd
  if [[ -x .venv/bin/uvicorn ]]; then
    cmd=(.venv/bin/uvicorn main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --reload)
  else
    echo "警告: 未找到 backend/.venv/bin/uvicorn，回退到系统 uvicorn" >&2
    cmd=(uvicorn main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --reload)
  fi

  nohup "${cmd[@]}" > "$LOG_DIR/backend.log" 2>&1 < /dev/null &
  BE_PID=$!
  disown || true
  echo "$BE_PID" > "$pidfile"

  echo "等待后端就绪 (最多 ${HEALTH_TIMEOUT}s) ..."
  if wait_for_port "$BACKEND_HOST" "$BACKEND_PORT" "$HEALTH_TIMEOUT"; then
    if curl -s -m 3 "http://${BACKEND_HOST}:${BACKEND_PORT}/health" | grep -q '"status"'; then
      echo "后端已启动 PID $BE_PID，日志: $LOG_DIR/backend.log"
      return 0
    fi
  fi

  echo "后端启动失败，日志尾部:" >&2
  tail -n 30 "$LOG_DIR/backend.log" >&2 || true
  rm -f "$pidfile"
  kill "$BE_PID" 2>/dev/null || true
  exit 1
}

start_frontend() {
  local pidfile="$PID_DIR/frontend.pid"
  if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "前端已在运行 (PID $(cat "$pidfile"))"
    return 0
  fi

  echo "启动前端 (vite :$FRONTEND_PORT) ..."
  cd "$CODE_DIR/frontend"
  nohup npm run dev -- --port "$FRONTEND_PORT" --host 127.0.0.1 > "$LOG_DIR/frontend.log" 2>&1 < /dev/null &
  FE_PID=$!
  disown || true
  echo "$FE_PID" > "$pidfile"

  echo "等待前端就绪 (最多 30s) ..."
  if wait_for_port 127.0.0.1 "$FRONTEND_PORT" 30; then
    echo "前端已启动 PID $FE_PID，日志: $LOG_DIR/frontend.log"
    return 0
  fi

  echo "前端启动失败，日志尾部:" >&2
  tail -n 30 "$LOG_DIR/frontend.log" >&2 || true
  rm -f "$pidfile"
  kill "$FE_PID" 2>/dev/null || true
  exit 1
}

case "$WHAT" in
  backend)  start_backend ;;
  frontend) start_frontend ;;
  all)      start_backend; start_frontend ;;
  *) echo "未知参数: $WHAT (可选: backend|frontend|all)" >&2; exit 1 ;;
esac

echo "完成。前端访问: http://127.0.0.1:$FRONTEND_PORT  (API 代理到 :$BACKEND_PORT)"
