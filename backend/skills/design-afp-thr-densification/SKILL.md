---
description: 抗冻蛋白(AFP)渐进式Thr密集化设计流程。适用于Type I AFP序列的TH活性优化，通过逐步Thr替换实现TH突破。核心策略：积累期(Thr密度提升)→触发期(跨越临界阈值)→微调期(精细化)。15轮完整设计经验固化。
name: design-afp-thr-densification
tags:
- afp
- protein-design
- thr-densification
- mutation
- ice-binding
version: 1.0.0
---
# AFP渐进式Thr密集化设计技能

## 何时使用

- 需要对Type I α-helical AFP进行TH活性优化的场景
- 原始序列Thr含量低（<15%），需要大幅提升冰结合能力
- 应用场景: ice_cream, frozen_dough, meat_preservation, cell_cryopreservation, general
- 设计目标包含"提高TH活性"、"降低IRI IC50"的多轮迭代设计

## 核心原理：密度阈值模型

**Thr密度存在临界阈值**——前N轮积累IRI改善但TH不动，一旦跨过阈值（~55-60% Thr含量），TH和IRI同时跳跃。

```
积累期(Thr 10%→50%): IRI渐进提升，TH不变
触发点(~55-60% Thr): TH +200%+ 跳跃
打磨期: 微调最大化IRI
```

## 操作步骤

### Phase 0: 知识库分析（必做）

```
1. afp_knowledge_query(sequence, query_intent="full_analysis", application_scenario)
   → 获取: AFP类型、IBS残基位置、forbidden_positions、mutation_hotspots
   
2. afp_sequence_analyze(sequence, application_scenario)
   → 获取: 物化特征、Thr/Ala含量、活性预测基线
   
3. afp_design_strategy(current_sequence, performance_data, design_target, application_scenario)
   → 获取: 推荐突变方向和禁区规避建议
```

### Phase 1: 积累期 — 渐进Thr化（前8轮）

**优先级排序**：
1. **C端Ala→Thr**（远离IBS核心，安全性最高）
2. **非IBS面Ala→Thr**（A6-A12区域，但A6-A12多为禁区）
3. **N端帽化**（位置3-4，建立T2-T3-T4三联簇）
4. **消除负电荷**（D→T，移除IBS面附近Asp排斥）
5. **Glu静电增强**（IBS近邻引入E，利用2025 JACS机制）

**具体做法**：
```
每轮2-3个Ala→Thr替换：
- 优先选远离IBS核心(T2/T13/T24/T35) 4Å以外的Ala
- 避开知识库标记的forbidden_positions
- 在IBS面引入Glu(A→E)可通过静电增强IRI +14%（R4验证）
- 消除序列中所有Asp(D→T)，移除负电荷干扰

监控: TH预览值可能始终不变(0.16→0.16)，这是正常的积累期特征
```

### Phase 2: 触发期 — 跨越密度阈值（R9左右）

**触发条件**: Thr含量达到~55-60%（约20+个Thr在37aa序列中）

**关键突变**: K22T（或等同位置）——该位置在IBS近邻，移除大体积带电残基、增加Thr密度，是触发TH跳跃的关键一击。

```
afp_mutate_sequence(mutations=[{"position":22,"from_aa":"K","to_aa":"T"}])
→ 预期: TH预览从0.16→0.97 (+506%)，IRI改善从+63%→+66%
```

**判断触发成功的标志**：
- TH预览值首次出现正变化
- 评估报告显示"EXCELLENT: 突变全面改善了AFP性能"
- 冰结合模拟TH_C从0.1-0.3跳跃至0.5+

### Phase 3: 打磨期 — 微调最大化（R10-R15）

触发后继续填补剩余安全位点，然后尝试微调：

```
1. 填补剩余Ala→Thr（安全位点用完为止）
2. Glu→Gln微调（如果引入过Glu，可尝试Q替换看IRI变化）
3. Gln→Thr微调（纯Thr vs Gln对比测试）
4. Thr→Ser保守替换（非IBS核心，单点测试）
5. 禁区边界保守替换（D→E等，预期触发CRITICAL→立即回退）
```

**微调回退原则**：每轮对比IRI改善%，优先保留高IRI配置。

## 禁区速查表（不可触碰！）

| 禁区类型 | 示例位点 | 突变后果 |
|----------|----------|----------|
| IBS核心 | T2, T13, T24, T35 | 活性崩溃(-80%+) |
| 盐桥网络 | D1, D5 | CRITICAL警告 |
| 结构保守区 | A6-A12, A14, A18 | CRITICAL警告 |
| 疏水核心 | L12, L23 | 结构失稳 |
| C端锚定 | A34 | CRITICAL警告 |

**铁律**: 即使知识库mutation_hotspots推荐，禁区也绝对不可触碰。
反例: A6是mutation_hotspots推荐但属于禁区，A11S触发CRITICAL证实。

## 常见陷阱

### 陷阱1: 积累期过早放弃
- **症状**: 前8轮TH无变化，怀疑策略错误
- **根因**: Thr密度未达临界阈值（~55-60%）
- **解决**: 坚持渐进Thr化，监控IRI改善作为进展指标
- **证据**: R9 K22T触发TH+233%，前8轮TH均为0%但IRI持续提升

### 陷阱2: 禁区触碰
- **症状**: `has_critical_warnings: true`，CRITICAL严重级别
- **根因**: 突变落入forbidden_positions
- **解决**: 立即回退（反向突变），即使评估显示PASS也不保留
- **案例**: D5E(R14)触发CRITICAL→立即回退

### 陷阱3: Glu→Gln过早微调
- **症状**: R12 E19Q导致IRI从70.89%降至69.45%
- **根因**: Gln不如Thr有效，而Glu在IBS面通过静电增强起作用
- **解决**: 先尝试Glu→Thr而非Glu→Gln
- **教训**: 纯Thr > Gln > Glu（在非IBS面位置）

### 陷阱4: Thr→Ser降解
- **症状**: T15S导致IRI从71.18%降至70.61%
- **根因**: Ser羟基比Thr短~1.5Å，冰晶格匹配精度下降
- **解决**: 回退至Thr，确认Thr在冰结合中不可替代

### 陷阱5: 多突变跳跃过大
- **症状**: 单轮5个突变导致不可预测的交互效应
- **解决**: 单轮≤3个突变，每个突变独立可追踪

## 验证方法

### 每轮验证
```
1. afp_evaluate_mutation → verdict必须为PASS
2. afp_ice_bind_simulate → 确认IRI改善%递增
3. 检查warnings数组 → 有CRITICAL立即回退
4. 检查forbidden_check.passed → 必须为true
```

### 触发点验证
```
当TH预览值首次变化时:
- afp_ice_bind_simulate确认TH_C跳跃
- 计算Thr密度: Thr数/序列长度 ≥ 55%
- 确认IRI改善%同步跳跃（+2-5%额外提升）
```

### 最终验证
```
afp_design_summary(所有15轮数据):
- 确认AFP概率≥99%
- TH改善≥200%
- IRI改善≥70%
- 表达评分≥0.55
- 稳定性评分≥0.60
```

## 成功案例参考

**输入**: `DTASDAAAAAALTAANAAAAAKLTADNAAAAAAATAR` (37aa, Thr=4)
**输出**: `DTTTDAAAAAALTATTTATTTTLTTTTTTTTTTATTT` (37aa, Thr=24)
**结果**: TH +506%, IRI +71.18%, AFP概率 99.99%

关键突变路径:
- R1-R8: 积累期 (IRI +9.5%→+63.4%)
- R9: K22T触发TH +233%
- R10-R15: 微调至IRI峰值+71.18%
