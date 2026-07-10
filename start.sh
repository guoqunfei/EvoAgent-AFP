#!/bin/bash

# ============================================
# EvoAgent-AFP 智能体启动脚本
# ============================================

echo "🚀 启动 EvoAgent-AFP 智能体..."
echo ""

# 检查Python虚拟环境
BACKEND_DIR="$(cd "$(dirname "$0")" && pwd)/backend"
FRONTEND_DIR="$(cd "$(dirname "$0")" && pwd)/frontend"

if [ ! -d "$BACKEND_DIR/.venv" ]; then
    echo "❌ 后端虚拟环境不存在,正在创建..."
    cd "$BACKEND_DIR" && python3.13 -m venv .venv
    echo "✅ 虚拟环境创建完成"
fi

# 安装/更新依赖
echo "📦 检查后端依赖..."
cd "$BACKEND_DIR"
.venv/bin/pip install --quiet -r requirements.txt

# 停止旧的服务
echo "🔇 停止旧的服务..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true
sleep 1

# 启动后端服务
echo "🔧 启动后端服务 (端口 8000)..."
cd "$BACKEND_DIR"
.venv/bin/uvicorn app.main:app --reload --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "   后端PID: $BACKEND_PID"

# 等待后端启动
echo "⏳ 等待后端启动..."
for i in {1..10}; do
    if curl -s http://localhost:8000/api/v1/chat/models > /dev/null 2>&1; then
        echo "✅ 后端服务就绪!"
        break
    fi
    sleep 1
done

# 验证后端
echo ""
echo "🧪 验证后端API..."
curl -s http://localhost:8000/api/v1/chat/models | python3 -m json.tool 2>/dev/null | grep -E '"id"|"model"' | head -14

# 启动前端服务
echo ""
echo "🎨 启动前端服务 (端口 5173)..."
cd "$FRONTEND_DIR"
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   前端PID: $FRONTEND_PID"

# 等待前端启动
echo "⏳ 等待前端启动..."
for i in {1..10}; do
    if curl -s http://localhost:5173/ > /dev/null 2>&1; then
        echo "✅ 前端服务就绪!"
        break
    fi
    sleep 1
done

echo ""
echo "============================================"
echo "🎉 EvoAgent-AFP 智能体启动完成!"
echo "============================================"
echo ""
echo "📍 访问地址:"
echo "   前端: http://localhost:5173/"
echo "   后端: http://localhost:8000/"
echo "   API文档: http://localhost:8000/docs"
echo ""
echo "📊 可用模型:"
curl -s http://localhost:8000/api/v1/chat/models | python3 -m json.tool 2>/dev/null | grep '"label"' | sed 's/.*": "\(.*\)".*/   • \1/'
echo ""
echo "🛑 停止服务:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo "   或者运行: ./stop.sh"
echo ""
echo "📝 日志文件:"
echo "   后端: /tmp/backend.log"
echo "   前端: /tmp/frontend.log"
echo ""
