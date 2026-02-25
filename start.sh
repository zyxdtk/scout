#!/bin/bash

# =================================================================
# Scout 项目管理脚本 (支持 start/stop/restart)
# =================================================================

# 确保在项目根目录下运行
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$BASE_DIR"

PORT=9333
LOG_DIR="$BASE_DIR/logs"
LOG_FILE="$LOG_DIR/scout.log"
mkdir -p "$LOG_DIR"

function get_pid() {
    echo $(lsof -t -i:$PORT)
}

function stop() {
    PID=$(get_pid)
    if [ ! -z "$PID" ]; then
        echo "🛑 正在停止进程 $PID..."
        kill $PID
        # 等待进程退出
        for i in {1..5}; do
            if [ -z "$(get_pid)" ]; then
                echo "✅ 服务已成功停止。"
                return 0
            fi
            sleep 1
        done
        echo "⚠️  进程未正常退出，正在强制杀掉 (SIGKILL)..."
        kill -9 $PID
        echo "✅ 服务已强制停止。"
    else
        echo "ℹ️  没有发现正在运行的服务。"
    fi
}

function start() {
    PID=$(get_pid)
    if [ ! -z "$PID" ]; then
        echo "⚠️  检测到 Scout 已经有一个实例在运行 (PID: $PID)。"
        read -p "请选择操作: [s]停止 (Stop) [r]重启 (Restart) [c]取消 (Cancel) [默认 r]: " choice
        choice=${choice:-r} # 默认重启

        case "$choice" in
            s|S)
                stop
                return 0
                ;;
            r|R)
                echo "🔃 正在执行重启过程..."
                stop
                # 继续执行下面的启动代码
                ;;
            *)
                echo "已取消操作。"
                return 0
                ;;
        esac
    fi

    echo "🚀 正在启动 Scout..."
    
    # 检查虚拟环境
    if [ ! -d ".venv" ]; then
        echo "❌ 未检测到 .venv 环境，请先安装依赖。"
        exit 1
    fi

    export PYTHONPATH="$BASE_DIR"
    
    # 在启动前检查数据一致性
    echo "🔍 正在检查数据库与磁盘文件的一致性..."
    uv run python scripts/sync_db.py --check
    if [ $? -ne 0 ]; then
        echo "⚠️  检测到数据库存在孤立记录（物理文件已删除）。"
        read -p "是否现在执行修复同步 (Rebuild DB state)? [y/N]: " sync_choice
        if [[ "$sync_choice" =~ ^[yY]$ ]]; then
            uv run python scripts/sync_db.py
        else
            echo "⏩ 已跳过同步，直接启动服务。"
        fi
    fi
    
    # 后台启动
    nohup uv run uvicorn src.main_web:app --host 0.0.0.0 --port $PORT > "$LOG_FILE" 2>&1 &
    
    # 检查是否成功启动
    sleep 2
    NEW_PID=$(get_pid)
    if [ ! -z "$NEW_PID" ]; then
        echo "✅ Scout 已启动 (PID: $NEW_PID)"
        echo "🌐 地址: http://127.0.0.1:$PORT"
        echo "📝 日志: tail -f $LOG_FILE"
    else
        echo "❌ 启动失败，请检查 $LOG_FILE"
    fi
}

# 默认执行 start (包含交互逻辑)
ACTION=${1:-start}

case "$ACTION" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        echo "🔃 正在重启服务..."
        stop
        start
        ;;
    status)
        PID=$(get_pid)
        if [ ! -z "$PID" ]; then
            echo "🟢 Scout 正在运行 (PID: $PID)"
        else
            echo "🔴 Scout 已停止"
        fi
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status}"
        exit 1
esac

