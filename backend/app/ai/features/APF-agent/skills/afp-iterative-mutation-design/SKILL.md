---
description: 抗冻蛋白(AFP)迭代突变设计完整工作流。适用于从野生型AFP序列出发，通过多轮理性突变优化TH活性、IRI活性、表达量和稳定性的场景。覆盖知识库查询→设计策略→突变执行→多维评估→冰结合模拟的闭环流程，包含安全突变策略、禁区规避规则、关键突破模式和常见失败模式。
name: afp-iterative-mutation-design
version: 1.0.0
---
# AFP 迭代突变设计技能

## 何时使用

当你需要：
- 从一条AFP序列出发，通过多轮突变优化其性能
- 目标包括：提高TH活性、降低IRI IC50、改善表达量、增强稳定性
- 应用场景：细胞冻存、冰淇淋、冷冻面团、器官保存、转基因作物等
- 需要在每一轮做出理性决策并评估突变影响

**典型触发**：用户提供AFP序列+应用场景+设计目标（如"提高TH活性3倍"）

---

## 操作步骤

### 第一阶段：初始分析（3步）

**Step 1: 知识库查询**
```
afp_knowledge_query(sequence, query_intent="full_analysis", application_scenario)
```
- 获取：AFP类型分类、IBS残基定位、已知基序、禁区列表、可突变位点建议
- 输出中的 `forbidden_positions` 是整个设计过程中**绝对不可突变**的位点

**Step 2: 序列分析**
```
afp_sequence_analyze(sequence, application_scenario)
```
- 获取基线性能：TH、IRI、表达评分、稳定性评分、AFP概率
- 记录为 `original_performance`

**Step 3: 初始设计策略**
```
afp_design_strategy(current_sequence, performance_data, design_target, application_scenario)
```
- 获取第一轮推荐方向
- 特别注意：`avoid_strategies`（禁止策略）和 `recommended_directions`（推荐方向）

---

### 第二阶段：迭代突变循环（每轮3步）

**每轮标准流程：**

**Step A: 执行突变**
```
afp_mutate_sequence(original_sequence, mutations, rationale)
```
- 每次1-5个突变位点
- **必须在rationale中说明为什么选择这些位点和方向**
- 检查返回的 `has_critical_warnings`：如果为true，说明触碰了禁区，**立即放弃本轮**
- 记录 `mutated_sequence` 和 `mutation_description`

**Step B: 多维评估**
```
afp_evaluate_mutation(original_sequence, mutated_sequence, mutations, application_scenario)
```
- 判定：PASS（通过）/ CAUTION（警告）/ REJECTED（拒绝）
- REJECTED：**必须回退**，本轮突变不可接受
- CAUTION：可以接受但需关注，建议下一轮针对性优化
- PASS：完全通过，继续推进

**Step C: 冰结合模拟（每2-3轮或CAUTION时必做）**
```
afp_ice_bind_simulate(sequence, original_sequence, target_ice_plane="auto")
```
- 获取更精确的TH/IRI预测、冰面匹配评分
- 对比 `comparison_with_original` 确认改善幅度
- 如果 `activity_assessment` 显示"无活性"或"低活性"，需重新审视方向

---

### 第三阶段：策略调整与收尾

**每3-5轮执行一次设计策略更新**：
```
afp_design_strategy(current_sequence, updated_performance, design_target, application_scenario, design_history)
```

**达到目标或轮次上限后**：
```
afp_design_summary(original_sequence, final_sequence, design_target, application_scenario, mutation_history, original_performance, final_performance)
```

---

## 核心设计规则（从15轮实战提炼）

### ✅ 安全策略（优先采用）

| 策略 | 描述 | 预期效果 | 风险 |
|:-----|:-----|:-----|:-----|
| 非IBS面 Ala→Ser | 将非IBS面的Ala替换为Ser | 表达+15-20%/轮，IRI温和改善 | 极低 |
| 非IBS面 Ala→Asn | 在非IBS面引入Asn形成H-bond网络 | IRI大幅改善(-20-30%)，可能触发TH跳跃 | 低 |
| IBS T+3位置引入Thr | 在已有IBS Thr的+3间距位置引入Thr | TH +20-30% | 中 |
| C端亲水化 | C端非IBS残基→Ser/Thr | 表达改善 | 极低 |

### ❌ 禁止策略（绝对避免）

| 策略 | 原因 | 已证实的后果 |
|:-----|:-----|:-----|
| IBS核心Thr突变 | T2/T13/T24/T35是冰结合面核心 | TH崩溃-80%以上 |
| IBS面引入带电残基 | 电荷排斥冰晶面 | IRI恶化+7%，TH倒退-20% |
| IBS面引入大体积残基 | 破坏冰面几何互补性 | 平面性破坏，活性下降 |
| 非对称位置引入Thr | 不在T+3/T+6间距的Thr破坏规则间距 | TH倒退-20% |
| D1/D5/K18/E22突变 | 结构稳定性关键盐桥/氢键 | 折叠破坏风险 |

### 🔑 两大关键突破模式

**突破模式1：IBS邻位Thr引入（N16T模式）**
- 在IBS Thr（如T13）的+3间距位置引入Thr
- 形成对称的Thr阵列（T13 → T13+T16）
- 效果：TH +25%，IRI持续改善

**突破模式2：非IBS面Asn网络（A26N模式）**
- 在非IBS面引入Asn，与周围Ser/Thr形成氢键网络
- 刚性化螺旋骨架，间接增强IBS面冰结合
- 效果：TH跳跃+233%（0.3→1.0°C），此为最大单轮突破

---

## 常见陷阱

### 陷阱1：IBS面Thr→Glu的诱惑
- **错误思维**："Glu也有OH，可以替代Thr"（参考2025 JACS文献）
- **实际结果**：Glu的羧酸根负电荷排斥冰面，IRI恶化+7%
- **教训**：文献中的特殊案例（特定β-螺旋框架）不可直接推广到α-螺旋TmAFP

### 陷阱2：对称位置盲目引入Thr
- **错误思维**："既然T16成功了，T21/T27也可以"
- **实际结果**：N21T和Q27T都导致TH倒退-20%
- **原因**：T21距离T24仅-3（不对称），T27距离T24仅+3但处于非标准间距
- **教训**：Thr引入必须严格遵守T+3/T+6间距规则，且需与已有Thr对齐

### 陷阱3：一轮突变过多
- 每次最多5个位点
- 如果一轮包含>3个位点且出现CAUTION，难以定位问题突变
- **建议**：关键探索阶段每轮1-2个位点，安全优化阶段可3-5个

### 陷阱4：忽略禁区之外的"灰色区域"
- I22、E22附近3Å范围内的残基虽不在禁区列表，但突变可能间接破坏盐桥
- **建议**：K18和E22周围±3位置谨慎操作

### 陷阱5（系统）：预览值与模拟值不一致
- `afp_mutate_sequence` 的预览TH/IRI是粗略估计
- 实际以 `afp_evaluate_mutation` 和 `afp_ice_bind_simulate` 为准
- 预览TH上升但模拟TH下降的情况出现过（如S20T）

---

## 验证方法

### 每轮验证清单
- [ ] `afp_mutate_sequence` 返回 `has_critical_warnings: false`
- [ ] `afp_evaluate_mutation` 判定不是 `REJECTED`
- [ ] `forbidden_check.passed: true`
- [ ] `ibs_integrity_check.passed: true`
- [ ] TH不下降（允许持平或上升）
- [ ] IRI不恶化（IC50下降或持平）
- [ ] 表达评分不显著下降（允许-0.05以内波动）

### 阶段性验证（每5轮）
- [ ] `afp_ice_bind_simulate` 确认冰面匹配评分>0.7
- [ ] `activity_assessment` 至少为"中等活性"
- [ ] 与原始序列对比，`verdict` 为 GOOD 或 EXCELLENT
- [ ] AFP概率持续上升或保持>0.95

### 最终验证
- [ ] TH达到目标值
- [ ] IRI不差于原始
- [ ] 表达评分>0.7（可生产）
- [ ] 禁区零触碰（0个forbidden mutation）
- [ ] 所有REJECTED轮次已回退

---

## 设计节奏建议

| 阶段 | 轮次 | 策略重点 | 每轮位点数 |
|:-----|:-----|:-----|:-----|
| 探索期 | 1-3 | 非IBS面安全突变，建立表达基础 | 3-5 |
| 突破期 | 4-8 | 尝试IBS邻位Thr引入，寻找TH突破 | 1-2 |
| 精修期 | 9-12 | 基于突破方向深化，清理剩余Ala | 2-3 |
| 收尾期 | 13-15 | 微调边界，最大化IRI和AFP概率 | 1-2 |

**总轮次建议**：10-15轮，低于10轮通常不足以达到显著TH改善。
