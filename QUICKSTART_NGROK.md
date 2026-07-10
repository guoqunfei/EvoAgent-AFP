# 🚀 Ngrok 内网穿透 - 快速开始

##  3分钟快速启动

### 步骤1: 首次配置 (仅需一次)

```bash
# 1. 注册 ngrok 账号
open https://dashboard.ngrok.com/signup

# 2. 登录后获取 authtoken
open https://dashboard.ngrok.com/get-started/your-authtoken

# 3. 复制token并配置(替换 <YOUR_TOKEN>)
ngrok config add-authtoken <YOUR_TOKEN>
```

### 步骤2: 启动本地服务

确保你的后端和前端正在运行:

```bash
# 终端1 - 后端API
cd backend && source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 终端2 - 前端界面  
cd frontend
npm run dev
```

### 步骤3: 启动 Ngrok

**方式A: 使用智能脚本(推荐)**
```bash
./start_ngrok.sh
```
然后选择要暴露的服务:
- `1` - 仅后端API
- `2` - 仅前端界面  
- `3` - 同时暴露前后端

**方式B: 直接命令**
```bash
# 暴露后端
ngrok http 8000

# 或暴露前端
ngrok http 5173
```

### 步骤4: 访问公网URL

启动后会显示类似:
```
Forwarding    https://abc123xyz.ngrok-free.app -> http://localhost:8000
```

✅ **你的应用现在可以从任何地方访问了!**

---

## 🔍 监控请求

访问 http://localhost:4040 查看实时请求日志

---

##  常见问题

**Q: URL会变吗?**  
A: 免费版每次重启会生成新URL,付费版可固定域名

**Q: 连接会断开吗?**  
A: 空闲1小时后自动断开,重新运行命令即可

**Q: CORS错误?**  
A: 已自动配置,无需额外设置

**Q: 前端无法连接后端?**  
修改 `frontend/.env.local`:
```
VITE_API_BASE_URL=https://你的ngrok域名.ngrok-free.app/api/v1
```

---

##  更多文档

详细配置请参考 [NGROK_SETUP.md](NGROK_SETUP.md)
