import re

# 读取 vite.config.ts
with open('frontend/vite.config.ts', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 target 为环境变量或保持 localhost
new_content = content.replace(
    "target: 'http://127.0.0.1:8000'",
    "target: process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000'"
)

with open('frontend/vite.config.ts', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ Vite 配置已更新")
