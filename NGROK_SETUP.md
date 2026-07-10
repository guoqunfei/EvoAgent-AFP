# Ngrok 内网穿透配置指南

## 📋 前置准备

### 1. 注册Ngrok账号

访问 [https://dashboard.ngrok.com/signup](https://dashboard.ngrok.com/signup) 注册免费账号

### 2. 获取Authtoken

登录后,在 [https://dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken) 页面复制你的authtoken

### 3. 配置Authtoken

```bash
ngrok config add-authtoken <YOUR_AUTHTOKEN>
```

例如:
```bash
ngrok config add-authtoken 2aBcD3eFgH4iJkLmN5oPqR6sTuV7wXyZ8
```

---

## 🚀 使用方式

### 方式一: 使用启动脚本(推荐)

```bash
cd /Users/guoqunfei/Applications/PyCharm/Projects/EvoAgent-AFP
./start_ngrok.sh
```

脚本会提示你选择要暴露的服务:
- **选项1**: 仅后端API (端口8000)
- **选项2**: 仅前端界面 (端口5173)  
- **选项3**: 同时暴露前后端

### 方式二: 直接命令

**暴露后端API:**
```bash
ngrok http 8000
```

**暴露前端界面:**
```bash
ngrok http 5173
```

**同时暴露两个服务:**
打开两个终端窗口:
```bash
# 终端1 - 后端API
ngrok http 8000

# 终端2 - 前端界面
ngrok http 5173
```

---

## 🌐 访问地址

启动后,ngrok会显示类似以下的输出:

```
Forwarding    https://abc123xyz.ngrok-free.app -> http://localhost:8000
```

你可以使用以下URL访问:
- **HTTPS**: `https://abc123xyz.ngrok-free.app`
- **HTTP**: `http://abc123xyz.ngrok-free.app`

---

## ⚙️ 高级配置

### 自定义域名(需要付费计划)

```bash
ngrok http --domain=myapp.example.com 8000
```

### 设置基本认证

```bash
ngrok http 8000 --basic-auth="username:password"
```

### 查看请求日志

访问本地Web界面: [http://localhost:4040](http://localhost:4040)

可以看到所有通过ngrok的请求详情,包括:
- 请求时间
- 请求方法(GET/POST等)
- 请求路径
- 响应状态码
- 请求和响应体

---

## 🔧 常见问题

### Q: ngrok免费版有什么限制?

A: 
- 每次重启会生成新的随机域名
- 连接空闲1小时后会自动断开
- 每月有流量限制(通常足够测试使用)
- 无法使用自定义域名

### Q: 如何保持连接不断开?

A: 
1. 定期发送心跳请求(如使用cron定时curl)
2. 升级到付费计划获得更长的超时时间

### Q: 后端API返回CORS错误?

A: 需要在FastAPI中配置CORS中间件允许ngrok域名:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或指定ngrok域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Q: 前端需要知道后端的新地址?

A: 是的,需要修改前端的API_BASE_URL环境变量或配置文件:

```typescript
// frontend/.env.local
VITE_API_BASE_URL=https://abc123xyz.ngrok-free.app/api/v1
```

然后重启前端开发服务器。

---

## 📝 最佳实践

1. **开发阶段**: 使用启动脚本快速切换前后端
2. **演示阶段**: 固定一个ngrok会话,不要频繁重启
3. **生产环境**: 建议使用正式服务器部署,而非ngrok
4. **安全考虑**: 不要在公开场合分享ngrok URL,避免未授权访问

---

## 🔗 相关链接

- [Ngrok官方文档](https://ngrok.com/docs)
- [Ngrok Dashboard](https://dashboard.ngrok.com)
- [Ngrok定价](https://ngrok.com/pricing)
