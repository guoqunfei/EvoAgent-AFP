---
description: 抗冻蛋白(AFP)智能突变设计完整工作流。适用于给定AFP序列需通过迭代突变优化TH活性、IRI活性、表达量或稳定性的场景。涵盖从序列分析→策略生成→突变→评估→模拟的闭环设计，内置禁区规避、Thr密度阈值突破、多目标权衡等核心策略。
name: design-afp-mutation
tags:
- afp
- protein-design
- mutation
- th-activity
- iri
- antifreeze-protein
version: 1.0.0
---
# AFP智能突变设计技能

## 何时使用

- 需要从给定AFP序列出发，通过迭代突变优化抗冻活性
- 设计目标包括：提高TH活性、降低IRI IC50、提升表达量、增强稳定性
- 已知或未知AFP类型，需要先分析后设计
- 需要遵循「禁区不碰、IBS保持、非IBS面优化」核心原则

## 操作步骤

### 阶段一：序列分析与策略生成（2步，不可跳过）

**Step 1: 知识库分析**
```
afp_knowledge_query(sequence, query_intent="full_analysis", application_scenario)
```
- 获取：AFP类型分类、IBS残基位置、已知基序、禁区列表、可突变位点
- 记录禁区位置，后续突变**绝对不要触碰**

**Step 2: 设计策略**
```
afp_design_strategy(current_sequence, performance_data, design_target, application_scenario)
```
- 获取分阶段推荐策略（渐进积累 → 突破 → 精细打磨）
- 记录推荐的突变方向和优先级

### 阶段二：渐进积累期（IRI逐步提升，TH不变）

**特征**: TH保持基线不变，IRI逐步改善。每轮突变后IRI提升5-20%。

**策略优先级**:
1. 非IBS面 Ala→Thr（最高优先级，每次2-3个）
2. 非IBS面 Ser→Thr（增强冰结合羟基密度）
3. 非IBS面 Asn→Thr（消除大体积极性残基）
4. 带电残基→Thr（先正后负：先消除Lys/Arg，再考虑Asp/Glu）

**每轮操作**:
```
afp_mutate_sequence(sequence, mutations, rationale)
→ afp_evaluate_mutation(...)
→ afp_ice_bind_simulate(...)
```

**进阶信号**: Thr数量达到15-17时，注意TH可能触发跳跃（+233%）。

### 阶段三：突破期（TH跳跃）

**特征**: 当Thr密度超过阈值（约15-17个），TH活性可能突然从0.1-0.3°C跳至1.0°C。

**关键操作**:
- 继续消除剩余非Thr残基（非IBS面）：Lys→Thr、Gln→Thr
- 每次突破后验证IBS完整性
- 突破后IRI改善速度会加快（每轮1-3%）

### 阶段四：精细打磨期（回退验证循环）

**特征**: 在最优序列附近微调，验证每一个非Thr位点的最优氨基酸。

**操作模式**: 试探→评估→回退
```
试探: Q→N (侧链缩短测试)
→ 若POOR: 立即回退 N→Q
试探: Q→E (电荷测试)  
→ 若POOR: 立即回退 E→Q
试探: T→S (甲基必要性测试)
→ 若POOR: 立即回退 S→T
```

**每个位点建议测试2-3种替代氨基酸**，确认当前残基确实最优。

### 阶段五：总结报告

```
afp_design_summary(original_sequence, final_sequence, design_target,
                   application_scenario, mutation_history,
                   original_performance, final_performance)
```

## 常见陷阱

### 陷阱1: 触碰IBS禁区（致命）
- **现象**: 突变T2/T13/T24/T35会导致活性崩溃（-80%以上）
- **预防**: Step 1获取禁区列表后，写入每轮rationale中提醒自己

### 陷阱2: 过早引入Glu（可能有益但需时机）
- **现象**: 在非IBS面中部引入Glu可翻倍表达量（R4: +98%），但在密集Thr区引入负电荷会恶化IRI
- **预防**: Glu适合在Thr密度<12时引入非IBS面中部；Thr密度>15后改用Gln

### 陷阱3: 侧链缩短无收益
- **现象**: Glu→Asp、Gln→Asn（侧链缩短一个亚甲基）通常无改善甚至恶化
- **原因**: 侧链长度直接影响冰面几何匹配
- **预防**: 优先测试同长度不同官能团（如Gln↔Glu），而非缩短侧链

### 陷阱4: 负电荷在密集Thr区有害
- **现象**: 当周围有4+个Thr时，Glu的负电荷与Thr羟基竞争氢键，恶化IRI
- **预防**: 密集Thr区（Thr间距<4残基）优先用Gln而非Glu

### 陷阱5: Thr→Ser微降活性
- **现象**: Thr→Ser（移除甲基仅留羟基）导致IRI微降~0.6%
- **原因**: Thr的甲基提供范德华接触，增强冰面几何互补
- **预防**: 不要在密集Thr区做Thr→Ser替代，除非有明确的结构理由

### 陷阱6: 忘记评估突变效果
- **现象**: 突变后直接下一轮，未评估→无法判断方向
- **预防**: 每轮严格 mutate → evaluate → simulate 三步走

## 验证方法

### 每轮验证清单
- [ ] `afp_evaluate_mutation` verdict 不是 REJECTED
- [ ] IBS完整性检查通过（无禁区触碰）
- [ ] IRI变化方向正确（下降=改善）
- [ ] 几何评分未下降（保持≥0.933）
- [ ] AFP概率保持≥0.99

### 关键里程碑验证
- Thr=10: IRI应改善30-40%
- Thr=15: 观察TH是否触发跳跃
- Thr=20+: IRI应改善60-70%，TH应≥0.8°C

### 最终验证
- TH ≥ 原始10倍（如0.1→1.0°C）
- IRI改善 ≥ 70%
- 表达评分 ≥ 0.6
- 稳定性无退化
- AFP概率 ≥ 0.999

## 设计规则速查

| 规则 | 强度 | 说明 |
|------|------|------|
| IBS核心(T2/T13/T24/T35)绝对不可变 | 🔴强 | 任何突变→活性崩溃 |
| Thr密度>15触发TH突破 | 🔴强 | 从0.1→1.0°C跳跃 |
| 非IBS面Ala→Thr始终安全 | 🟡中 | 可批量执行(2-3/轮) |
| 密集Thr区Gln优于Glu | 🟡中 | 负电荷恶化IRI |
| Thr甲基对活性不可或缺 | 🟡中 | Ser不能完全替代Thr |
| Glu在非IBS面中部提升表达 | 🟡中 | 表达+98%，但需时机 |
| Lys/Arg→Thr改善IRI | 🟢弱 | 消除正电荷有助于冰结合 |
| Asp/Glu→Thr改善IRI | 🟢弱 | 消除负电荷改善TH |
| 侧链缩短(Glu→Asp, Gln→Asn)无收益 | 🟡中 | 几何匹配依赖侧链长度 |

## 预期轮次

- 简单优化（5-8个突变）：6-8轮
- 中等优化（10-15个突变）：10-12轮
- 深度优化（15+个突变+验证）：13-15轮
