# EvoAgent-AFP: Self-Evolving Agent-Driven Antifreeze Protein Design Platform

<div align="center">

**一个基于AI智能体的抗冻蛋白精准设计平台**

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.4+-brightgreen.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 📖 项目简介

EvoAgent-AFP 是一个创新的抗冻蛋白(Antifreeze Protein, AFP)设计平台,利用自进化AI智能体技术实现蛋白质序列的精准设计和优化。该平台整合了多个先进的AI模型和生物信息学工具,为研究人员提供从序列分析、突变设计到结构预测的全流程解决方案。

### ✨ 核心特性

- **🤖 智能体驱动**: 基于LangChain的多智能体系统,支持自主决策和迭代优化
- **🧬 多模型支持**: 集成7个主流AI模型(Kimi、DeepSeek、GPT、Qwen、GLM、MiniMax等)
- **🔬 专业知识库**: 内置抗冻蛋白领域知识库,支持RAG检索增强生成
- **🎯 精准设计**: 基于物理化学特性的序列评估和优化策略
- **📊 批量处理**: 支持大规模序列的并行分析和对比
- **🌐 可视化界面**: 现代化的Web界面,支持实时交互和结果展示
- **💾 会话管理**: 完整的对话历史和设计轨迹追踪

---

## 🏗️ 技术架构

### 后端技术栈
- **框架**: FastAPI (Python 3.13+)
- **AI引擎**: LangChain + OpenAI API
- **向量数据库**: FAISS
- **数据存储**: SQLite
- **异步处理**: asyncio + uvicorn

### 前端技术栈
- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **状态管理**: Pinia
- **UI组件**: 自定义组件库
- **Markdown渲染**: marked

### 核心模块
```
backend/
├── app/
│   ├── ai/              # AI智能体核心
│   │   └── features/APF-agent/
│   │       ├── skills/  # 技能模块(设计策略)
│   │       ├── tools/   # 工具模块(评估、模拟等)
│   │       └── simulator/ # 物化特性模拟器
│   ├── api/             # RESTful API端点
│   ├── services/        # 业务逻辑层
│   ├── models/          # 数据模型
│   └── db/              # 数据库层
frontend/
├── src/
│   ├── components/      # Vue组件
│   ├── stores/          # Pinia状态管理
│   └── composables/     # 组合式API
```

---

## 🚀 快速开始

### 前置要求

- **Python**: 3.13+ (推荐通过Homebrew安装)
- **Node.js**: 18+ 
- **npm**: 9+
- **Git**: 2.0+

### 本地安装部署

#### 1. 克隆仓库

```bash
git clone https://github.com/guoqunfei/EvoAgent-AFP.git
cd EvoAgent-AFP
```

#### 2. 后端环境配置

```bash
# 进入后端目录
cd backend

# 创建虚拟环境 (使用Python 3.13)
python3.13 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 注意: faiss-cpu需要使用预编译wheel包
pip install faiss-cpu --only-binary faiss-cpu
```

#### 3. 前端环境配置

```bash
# 进入前端目录
cd ../frontend

# 安装依赖
npm install
```

#### 4. 配置环境变量

在`backend/`目录下创建`.env`文件:

```env
# OpenAI兼容API配置
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.moonshot.cn/v1

# 可选: 其他模型配置
DEEPSEEK_API_KEY=your_deepseek_key
QWEN_API_KEY=your_qwen_key
```

#### 5. 启动服务

**启动后端** (终端1):
```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**启动前端** (终端2):
```bash
cd frontend
npm run dev
```

#### 6. 访问应用

- **前端界面**: http://localhost:5173
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

---

## 🌐 内网穿透访问 (Ngrok)

### 快速启动 Ngrok

**方式一: 使用启动脚本(推荐)**
```bash
./start_ngrok.sh
```

**方式二: 直接命令**
```bash
# 暴露后端API
ngrok http 8000

# 暴露前端界面
ngrok http 5173
```

### 首次使用配置

1. **注册账号**: 访问 [https://dashboard.ngrok.com/signup](https://dashboard.ngrok.com/signup)
2. **获取Authtoken**: 登录后在 [Dashboard](https://dashboard.ngrok.com/get-started/your-authtoken) 复制token
3. **配置Token**:
   ```bash
   ngrok config add-authtoken <YOUR_AUTHTOKEN>
   ```

### 访问地址

启动后,ngrok会显示类似以下的URL:
```
Forwarding    https://abc123xyz.ngrok-free.app -> http://localhost:8000
```

- **公开访问URL**: `https://abc123xyz.ngrok-free.app`
- **请求监控**: http://localhost:4040 (查看实时请求日志)

### 注意事项

️ **CORS已自动配置**: 后端已允许所有来源访问,无需额外配置

⚠️ **前端API地址**: 如需从外网访问,需修改前端环境变量:
```typescript
// frontend/.env.local
VITE_API_BASE_URL=https://你的ngrok域名.ngrok-free.app/api/v1
```

📖 **详细文档**: 查看 [NGROK_SETUP.md](NGROK_SETUP.md)

---

## 📡 API接口说明

### 主要端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/afp/chat/stream` | POST | 流式聊天接口 |
| `/api/v1/afp/knowledge/query` | POST | 知识库查询 |
| `/api/v1/afp/tools/mutate` | POST | 序列突变设计 |
| `/api/v1/afp/tools/evaluate` | POST | 序列评估 |
| `/api/v1/afp/tools/simulate` | POST | ICE结合模拟 |
| `/api/v1/afp/design` | POST | 完整设计流程 |
| `/api/v1/chat/compare-models` | POST | 多模型对比分析 |
| `/api/v1/chat/batch/process` | POST | 批量处理 |

### 示例: 调用聊天接口

```bash
curl -X POST "http://localhost:8000/api/v1/afp/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "设计一个I型抗冻蛋白",
    "model": "kimi",
    "session_id": "test-session"
  }'
```

---

## 🎯 使用指南

### 功能模块

#### 1. 智能对话设计
- 支持自然语言交互
- 自动识别设计意图
- 提供专业的设计建议

#### 2. 序列分析与优化
- 物化特性计算(分子量、电荷、疏水性等)
- Thr密度分析
- IRI峰值预测

#### 3. 批量处理
- 支持CSV/Excel格式导入
- 并行处理多个序列
- 导出详细分析报告

#### 4. 多模型对比
- 同时调用7个AI模型
- 对比不同模型的設計策略
- 选择最优方案

#### 5. 知识检索
- 基于FAISS的向量检索
- RAG增强生成
- 领域专业知识支持

---

## 📊 项目结构

```
EvoAgent-AFP/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── ai/                # AI智能体
│   │   ├── api/               # API路由
│   │   ├── core/              # 核心配置
│   │   ├── services/          # 业务逻辑
│   │   └── main.py            # 应用入口
│   ├── requirements.txt       # Python依赖
│   └── skills/                # 技能定义
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── components/        # Vue组件
│   │   ├── stores/            # 状态管理
│   │   └── App.vue            # 根组件
│   ├── package.json           # Node依赖
│   └── vite.config.ts         # Vite配置
├── .gitignore                  # Git忽略文件
├── README.md                   # 项目说明
└── start.sh                    # 一键启动脚本
```

---

## 🔧 开发指南

### 添加新的AI模型

1. 在`backend/app/core/config.py`中添加模型配置
2. 在`backend/app/ai/features/APF-agent/`中实现模型适配器
3. 更新前端模型选择器

### 创建新的Skill

1. 在`backend/skills/`下创建新目录
2. 编写`SKILL.md`定义技能规范
3. 在工具注册表中注册新技能

### 扩展API端点

1. 在`backend/app/api/v1/endpoints/`中创建新模块
2. 定义Pydantic请求/响应模型
3. 在router.py中注册路由

---

## 🧪 测试

```bash
# 运行后端测试
cd backend
pytest tests/

# 运行前端测试
cd frontend
npm run test
```

---

## 📝 常见问题

### Q: faiss-cpu安装失败?
A: 使用预编译wheel包: `pip install faiss-cpu --only-binary faiss-cpu`

### Q: 前端端口被占用?
A: Vite会自动尝试下一个可用端口,或手动指定: `npm run dev -- --port 5174`

### Q: API返回401错误?
A: 检查`.env`文件中的API密钥是否正确配置

### Q: Python版本不兼容?
A: 本项目需要Python 3.13+,请使用Homebrew安装: `brew install python@3.13`

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 👥 贡献指南

欢迎提交Issue和Pull Request!

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📧 联系方式

- **项目主页**: https://github.com/guoqunfei/EvoAgent-AFP
- **问题反馈**: https://github.com/guoqunfei/EvoAgent-AFP/issues

---

<div align="center">

**Made with ❤️ for Antifreeze Protein Research**

</div>
