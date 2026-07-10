# 🧬 AFP批量序列分析功能使用指南

## 📋 功能概述

批量处理功能允许你**同时分析数十甚至数百条AFP蛋白序列**,AI模型会为每条序列生成专业的分析报告,并支持导出为CSV或JSON格式。

### ✨ 核心特性

- **🚀 高效并发**: 支持最多500条序列,可配置1-20个并发任务
- **📊 多格式输入**: 支持FASTA、CSV、纯文本三种格式
- **💾 结果导出**: 一键下载CSV或JSON格式的完整分析结果
- **⏱️ 实时进度**: 显示处理进度和预计完成时间
- **🔄 错误处理**: 自动跳过失败序列,继续处理其他序列
- **🎯 灵活配置**: 可选择不同AI模型和分析类型

---

## 🎯 使用方法

### 方法一:前端界面(推荐)

#### 1. 访问批量处理页面

打开浏览器访问 [http://localhost:5173/](http://localhost:5173/)

在聊天区域上方找到 **"批量处理"** 按钮,点击展开批量处理面板。

#### 2. 准备序列数据

支持以下三种格式:

**格式1: FASTA格式** (推荐)
```
>AFP_001
DTASDAAAAAALTAANAAAAAKLTADNAAAAAAATAR
>AFP_002
CEETNCPISACTESGACPTQAKTFSARNDYSERIDPRHLC
>AFP_003
AVLLPAGELGAATCTANPACETWCPVTT
```

**格式2: CSV格式**
```
AFP_001,DTASDAAAAAALTAANAAAAAKLTADNAAAAAAATAR
AFP_002,CEETNCPISACTESGACPTQAKTFSARNDYSERIDPRHLC
AFP_003,AVLLPAGELGAATCTANPACETWCPVTT
```

**格式3: 纯文本格式** (每行一条序列)
```
DTASDAAAAAALTAANAAAAAKLTADNAAAAAAATAR
CEETNCPISACTESGACPTQAKTFSARNDYSERIDPRHLC
AVLLPAGELGAATCTANPACETWCPVTT
```

#### 3. 配置参数

- **模型选择**: 选择用于分析的AI模型(默认:DeepSeek)
- **分析类型**: 
  - `快速分析`: 基础特征分析,速度快
  - `全面分析`: 详细专业报告,更准确(默认)
- **并发数**: 同时处理的序列数(1-20,默认5)

#### 4. 开始处理

1. 点击 **"加载示例"** 可快速测试
2. 粘贴你的序列到文本框
3. 点击 **"开始批量分析"** 按钮
4. 等待处理完成(进度条显示进度)

#### 5. 查看和导出结果

处理完成后:
- 预览前3条结果
- 点击 **"📊 导出CSV"** 下载CSV文件
- 点击 **"📄 导出JSON"** 下载JSON文件

---

### 方法二:API调用(开发者)

#### API端点

**批量处理接口:**
```
POST http://localhost:8000/api/v1/chat/batch/process
```

**请求体:**
```json
{
  "sequences": [
    {
      "sequence_id": "AFP_001",
      "sequence": "DTASDAAAAAALTAANAAAAAKLTADNAAAAAAATAR",
      "analysis_prompt": null
    },
    {
      "sequence_id": "AFP_002",
      "sequence": "CEETNCPISACTESGACPTQAKTFSARNDYSERIDPRHLC"
    }
  ],
  "model_key": "deepseek",
  "analysis_type": "comprehensive",
  "concurrent_limit": 5
}
```

**响应:**
```json
{
  "batch_id": "batch_abc123xyz",
  "status": "completed",
  "total_sequences": 2,
  "successful": 2,
  "failed": 0,
  "skipped": 0,
  "results": [
    {
      "sequence_id": "AFP_001",
      "sequence": "DTASDAAAAAALTAANAAAAAKLTADNAAAAAAATAR",
      "analysis": "详细的AI分析报告...",
      "success": true,
      "error_message": null,
      "processing_time_ms": 3500,
      "model_used": "deepseek-v4-pro"
    }
  ],
  "total_processing_time_ms": 7200,
  "created_at": "2026-07-09T17:30:00"
}
```

#### 导出接口

**CSV导出:**
```
GET http://localhost:8000/api/v1/chat/batch/{batch_id}/export?format=csv
```

**JSON导出:**
```
GET http://localhost:8000/api/v1/chat/batch/{batch_id}/export?format=json
```

---

## 💡 使用示例

### Python脚本调用

```python
import asyncio
import httpx

async def batch_analyze():
    sequences = [
        {"sequence_id": f"seq_{i}", "sequence": seq}
        for i, seq in enumerate(your_sequences, 1)
    ]
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            "http://localhost:8000/api/v1/chat/batch/process",
            json={
                "sequences": sequences,
                "model_key": "deepseek",
                "analysis_type": "quick",
                "concurrent_limit": 5
            }
        )
        
        result = response.json()
        print(f"成功: {result['successful']}, 失败: {result['failed']}")
        
        # 导出结果
        batch_id = result['batch_id']
        csv_resp = await client.get(
            f"http://localhost:8000/api/v1/chat/batch/{batch_id}/export?format=csv"
        )
        with open("results.csv", "wb") as f:
            f.write(csv_resp.content)

asyncio.run(batch_analyze())
```

### cURL测试

```bash
curl -X POST http://localhost:8000/api/v1/chat/batch/process \
  -H "Content-Type: application/json" \
  -d '{
    "sequences": [
      {"sequence_id": "test1", "sequence": "DTASDAAAAAALTAANAAAAAKLTADNAAAAAAATAR"}
    ],
    "model_key": "deepseek",
    "analysis_type": "quick",
    "concurrent_limit": 1
  }'
```

---

## 📊 性能参考

| 序列数量 | 并发数 | 分析类型 | 预计耗时 |
|---------|-------|---------|---------|
| 10      | 5     | 快速    | ~30秒   |
| 10      | 5     | 全面    | ~60秒   |
| 100     | 5     | 快速    | ~5分钟  |
| 100     | 10    | 快速    | ~3分钟  |
| 100     | 5     | 全面    | ~10分钟 |
| 500     | 10    | 快速    | ~25分钟 |

*注:实际时间取决于API响应速度和网络状况*

---

## 🔧 最佳实践

### 1. 大批量处理建议

- **分批处理**: 超过200条序列时,建议分批次处理
- **提高并发**: 根据服务器性能调整并发数(推荐5-10)
- **使用快速模式**: 初步筛选用"快速分析",重点序列用"全面分析"

### 2. 错误处理

- 失败的序列会在结果中标记为`success: false`
- 可查看`error_message`字段了解失败原因
- 可以重新提交失败的序列

### 3. 结果分析

导出的CSV包含以下列:
- `sequence_id`: 序列ID
- `sequence`: 原始序列
- `analysis`: AI分析报告
- `success`: 是否成功
- `error_message`: 错误信息(如有)
- `processing_time_ms`: 处理耗时
- `model_used`: 使用的模型

---

## 🧪 测试验证

项目根目录提供了测试脚本:

```bash
cd /Users/guoqunfei/Applications/PyCharm/Projects/EvoAgent-AFP
python test_batch_processing.py
```

该脚本会:
1. 生成100条测试序列
2. 发送到批量处理API
3. 显示处理结果统计
4. 导出CSV和JSON文件到`/tmp/`目录

---

## ❓ 常见问题

### Q: 最多可以处理多少条序列?
A: 单次请求最多500条。如需更多,请分批处理。

### Q: 为什么有些序列处理失败?
A: 可能原因包括:
- 序列格式不正确
- API调用超时
- 网络连接问题

### Q: 如何提高处理速度?
A: 
1. 增加并发数(concurrent_limit)
2. 使用"快速分析"模式
3. 选择响应更快的模型

### Q: 可以在后台运行吗?
A: 可以。API是异步的,提交后会立即返回batch_id,可通过状态接口查询进度。

### Q: 结果可以保存到哪里?
A: 支持导出为CSV或JSON,你可以保存到本地或上传到其他系统。

---

## 📞 技术支持

如遇到问题,请检查:
1. 后端服务是否正常运行(`http://localhost:8000/docs`)
2. 前端服务是否正常(`http://localhost:5173/`)
3. 查看浏览器控制台和后端日志

日志位置:
- 后端: `/tmp/backend.log`
- 前端: `/tmp/frontend.log`

---

**祝你使用愉快!** 🎉
