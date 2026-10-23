#!/usr/bin/env bash
# 停止 MigOps 前后端
#
# 用法:
#   ./stop.sh            停止后端 + 前端
#   ./stop.sh backend    仅停止后端
#   ./stop.sh frontend   仅停止前端
#
# 说明:
#   - 优先按 PID 文件精准停止；并对运行命令做 pkill 兜底，
#     清理 --reload 子进程 / npm 拉起的 vite 子进程残留。
#   - 先发 SIGTERM，等待后仍存活则发 SIGKILL，确保进程树彻底退出。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/.runtime/pids"
WHAT="${1:-all}"

# 递归杀死以 $1 为根的进程树（含直接/间接子进程）
kill_tree() {
  local pid="$1"
  [[ -z "$pid" ]] && return 0
  # 收集后代 PID（pkill -P 一层层收敛）
  local children
  children="$(pgrep -P "$pid" 2>/dev/null || true)"
  for c in $children; do
    kill_tree "$c" || true
  done
  kill -TERM "$pid" 2>/dev/null || true
}

# 等待进程退出，超时则 SIGKILL
reap() {
  local pid="$1" i
  for ((i = 0; i < 8; i++)); do
    kill -0 "$pid" 2>/dev/null || return 0
    sleep 1
  done
  echo "  PID $pid 未及时退出，发送 SIGKILL"
  kill -KILL "$pid" 2>/dev/null || true
  # 兜底强杀整个进程树
  pkill -KILL -P "$pid" 2>/dev/null || true
}

stop_backend() {
  local pidfile="$PID_DIR/backend.pid"
  if [[ -f "$pidfile" ]]; then
    local pid
    pid="$(cat "$pidfile")"
    if kill -0 "$pid" 2>/dev/null; then
      echo "停止后端 (PID $pid) ..."
      kill_tree "$pid"
      reap "$pid"
    else
      echo "后端 PID $pid 已不存在"
    fi
    rm -f "$pidfile"
  else
    echo "未找到后端 PID 文件，尝试按命令兜底清理 ..."
  fi
  # 兜底：清理 uvicorn reload 可能残留的子进程
  pkill -f "uvicorn main:app" 2>/dev/null || true
  echo "后端已停止"
}

stop_frontend() {
  local pidfile="$PID_DIR/frontend.pid"
  if [[ -f "$pidfile" ]]; then
    local pid
    pid="$(cat "$pidfile")"
    if kill -0 "$pid" 2>/dev/null; then
      echo "停止前端 (PID $pid) ..."
      kill_tree "$pid"
      reap "$pid"
    else
      echo "前端 PID $pid 已不存在"
    fi
    rm -f "$pidfile"
  else
    echo "未找到前端 PID 文件，尝试按命令兜底清理 ..."
  fi
  # 兜底：清理 npm 拉起的 vite 进程（含其 node 子进程）
  pkill -f "vite" 2>/dev/null || true
  echo "前端已停止"
}

case "$WHAT" in
  backend)  stop_backend ;;
  frontend) stop_frontend ;;
  all)      stop_backend; stop_frontend ;;
  *) echo "未知参数: $WHAT (可选: backend|frontend|all)" >&2; exit 1 ;;
esac
