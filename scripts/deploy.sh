#!/bin/bash
# Deploy updated Kindle Calendar files to device

KINDLE_IP="192.168.10.72"
KINDLE_PATH="/mnt/us/calendar"
LOCAL_PATH="./kindle"

echo "Kindle Calendar 部署脚本"
echo "======================"
echo "目标设备: $KINDLE_IP"
echo ""

# Sync files
echo "正在同步文件..."
rsync -avz --exclude '*.pyc' --exclude '__pycache__' \
    -e "ssh -o StrictHostKeyChecking=no" \
    "$LOCAL_PATH/" "root@$KINDLE_IP:$KINDLE_PATH/"

echo ""
echo "同步完成!"
echo ""
echo "在 Kindle 上执行以下命令启动:"
echo "  cd /mnt/us/calendar"
echo "  python3 main.py"