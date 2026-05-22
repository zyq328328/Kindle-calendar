#!/bin/bash
# SIGSTOP/SIGCONT 包装脚本
# 停止 Xorg+awesome -> 运行 touch_sender.py -> 恢复 Xorg+awesome

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/touch_sender.py"

echo "[run_touch] Starting touch sender"

# 检查设备
if [ ! -e /dev/input/event1 ]; then
    echo "[run_touch] ERROR: /dev/input/event1 not found"
    exit 1
fi

# 检查 python3
if ! command -v python3 &>/dev/null; then
    echo "[run_touch] ERROR: python3 not found"
    exit 1
fi

# 检查 requests 库
python3 -c "import requests" 2>/dev/null || {
    echo "[run_touch] WARNING: requests module not found, try pip3 install requests"
}

# 运行发送器
python3 "$PYTHON_SCRIPT"
exit_code=$?

echo "[run_touch] Finished with exit code $exit_code"
exit $exit_code
