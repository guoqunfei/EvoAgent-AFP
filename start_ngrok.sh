#!/bin/bash

# EvoAgent-AFP Ngrok启动脚本
# 用于将本地服务暴露到公网

echo "=========================================="
echo "EvoAgent-AFP - Ngrok内网穿透启动"
echo "=========================================="
echo ""

# 检查ngrok是否安装
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok未安装，请先运行: brew install ngrok"
    exit 1
fi

# 显示当前运行的服务
echo "📋 当前运行的服务:"
lsof -i :8000 | grep LISTEN > /dev/null 2>&1
BACKEND_RUNNING=$?
lsof -i :5173 | grep LISTEN > /dev/null 2>&1
FRONTEND_RUNNING=$?

if [ $BACKEND_RUNNING -eq 0 ]; then
    echo "  ✅ 后端服务 (端口 8000)"
else
    echo "  ❌ 后端服务未运行 (需要端口 8000)"
fi

if [ $FRONTEND_RUNNING -eq 0 ]; then
    echo "  ✅ 前端服务 (端口 5173)"
else
    echo "  ️  前端服务未运行 (可选,端口 5173)"
fi

echo ""

# 选择要暴露的服务
echo "请选择要暴露的服务:"
echo "  1) 仅后端API (端口 8000)"
echo "  2) 仅前端界面 (端口 5173)"
echo "  3) 同时暴露前后端"
echo ""
read -p "请输入选项 [1/2/3]: " choice

case $choice in
    1)
        echo ""
        echo "🚀 正在启动ngrok暴露后端API..."
        echo "   访问地址将在下方显示"
        echo ""
        ngrok http 8000
        ;;
    2)
        echo ""
        echo "🚀 正在启动ngrok暴露前端界面..."
        echo "   访问地址将在下方显示"
        echo ""
        ngrok http 5173
        ;;
    3)
        echo ""
        echo "🚀 正在启动两个ngrok隧道..."
        echo "   请打开另一个终端运行: ngrok http 5173"
        echo ""
        echo "后端API隧道:"
        ngrok http 8000
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac
