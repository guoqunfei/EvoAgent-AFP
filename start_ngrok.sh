#!/bin/bash
echo "======================================"
echo "EvoAgent-AFP 外网访问启动脚本"
echo "======================================"
echo ""
echo "正在启动 ngrok..."
echo ""
ngrok start --all --config=ngrok.yml
