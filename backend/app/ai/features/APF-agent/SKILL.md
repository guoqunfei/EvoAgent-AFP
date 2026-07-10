---
name: deploy-flask
description: 将Flask应用部署到云端生产环境的标准流程
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [flask, deployment, cloud]
    category: devops
---

## 何时使用
需要将Flask应用部署到生产环境时触发。适用于新应用首次部署或已有应用的更新部署。

## 操作步骤

**环境准备**
1. 确认服务器已安装Python 3.9+
2. 确认PostgreSQL数据库已就绪
3. 检查域名DNS解析是否正确

**代码部署**
4. git clone 或 rsync 同步代码到服务器
5. 创建虚拟环境并安装依赖：`pip install -r requirements.txt`
6. 配置环境变量：`cp .env.example .env` 并修改

**启动服务**
7. 数据库迁移：`flask db upgrade`
8. 使用gunicorn启动：`gunicorn -w 4 -b 0.0.0.0:8000 app:app`
9. 配置Nginx反向代理

**验证方法**
- 访问 `/health` 端点返回200
- 访问首页加载时间小于2秒
- 日志中无ERROR级别记录

## 常见陷阱

⚠️ **陷阱1**：数据库迁移时忘记指定FLASK_ENV环境变量，导致使用了错误的数据库配置
→ **解决**：部署脚本中明确设置 `export FLASK_ENV=production`

⚠️ **陷阱2**：gunicorn worker数量过多导致内存不足
→ **解决**：根据服务器内存大小设置worker数，一般选择 `2*CPU核心数+1`

## 成功验证标准

✅ 应用在生产环境运行超过24小时无重启
✅ curl测试所有核心API端点返回200