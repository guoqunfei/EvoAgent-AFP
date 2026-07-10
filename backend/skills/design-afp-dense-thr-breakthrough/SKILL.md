---
description: Type I / De novo AFP 密集Thr化TH突破策略。当AFP初始TH较低(≤0.2°C)且需要大幅提升TH活性(目标+300-500%)时使用。核心策略是在非IBS面安全位点大规模Ala→Thr替换，通过密集Thr阵列增强冰结合几何互补性。适用于37aa
  Type I骨架的从头TH优化。
name: design-afp-dense-thr-breakthrough
version: 1.0.0
---

# AFP 密集Thr化 TH突破策略

## 何时使用

- 初始AFP TH活性低（≤0.2°C），需要大幅提升（目标+300-500%）
- 序列为Type I / De novo α-螺旋AFP骨架（~37aa）
- IBS核心（T2/T13/T24/T35）已完整，不需要破坏
- 应用场景：细胞冻存、器官保存等对TH有严苛要求的场景
- 已通过afp_knowledge_query确认禁区分布

## 操作步骤

### 阶段零：基线分析（必须！）

```
1. afp_knowledge_query(sequence, query_intent='full_analysis')
   → 获取: IBS核心位置、禁区列表、突变热点、当前TH/IRI估算

2. afp_design_strategy(current_sequence, performance_data, design_target)
   → 获取: 推荐突变位点、禁区确认、策略优先级

3. 记录基线性能:
   - TH基线值
   - IRI基线值
   - 表达/稳定性评分
   - Thr数量及百分比
```

**关键输出**：禁区列表 + IBS核心位置 + 安全突变位点

### 阶段一：渐进式Thr引入（R1-R3，温和探索）

不要一开始就大规模突变！先用1-2个Thr测试系统响应。

```
R1: 单个非IBS面Ala→Thr（如A15T）
    - 位置选择：远离IBS面（螺旋旋转≥100°）
    - 预期：TH小幅提升(+20-30%)，IRI改善(+5-10%)
    - 验证：afp_evaluate_mutation → afp_ice_bind_simulate

R2: 双Thr引入（如A19T+A21T）
    - 位置选择：C端非IBS面，间距合适
    - 预期：IRI显著改善(+25-35%)，TH可能不变
    - 这是正常现象——非IBS面Thr先改善IRI

R3: 如果R1-R2 TH无变化，不要继续保守策略
    → 直接跳到阶段二密集Thr化！
```

**常见R1-R3失败模式**（如果出现以下情况，立即跳阶段二）：
- IBS边缘Glu(E)→无TH提升
- IBS边缘Asn(N)→无TH提升
- 盐桥恢复(K22E)→无TH提升
- 禁区突变(A18K)→REJECTED

### 阶段二：密集Thr化突破（R7-R9，核心！）

这是TH突破的关键阶段。一次5个位点的密集Thr替换。

```
R7: N端+中部密集Thr化（5突变）
    位点: A3→T, S4→T, N16→T, A17→T, A20→T
    目标: 形成N端T2-T3-T4三联簇 + 中部密集阵列
    预期: TH跳跃 +100-200%！这是突破点！
    验证: TH预测值应有显著跃升（如0.19→0.49）

R8: C端前段密集Thr化（5突变）
    位点: A25→T, D26→T, N27→T, A28→T, A29→T
    目标: 形成T24-T29六连Thr阵列
    预期: TH继续提升 +30-50%

R9: C端后段密集Thr化（5突变）
    位点: A30→T, A31→T, A32→T, A33→T, A36→T
    目标: Thr数量达到20+（>54%）
    预期: TH接近1.0°C
```

**密集Thr化位点选择原则**：
1. 必须在非禁区（避开forbidden_positions）
2. 必须在非IBS核心（T2/T13/T24/T35不可动）
3. 优先形成连续Thr簇（如三联簇、六连阵列）
4. N端T2-T3-T4三联簇优先级最高

### 阶段三：阵列完整性优化（R10-R12）

```
R10: K22→T（如果K22存在）
     - 移除C端正电荷，完成密集Thr阵列
     - 预期: TH +4-5%, IRI +2-3%
     - 规则: C端密集Thr区禁止带电残基

R11: 可选 T19→E 测试
     - Glu结合能=Thr×4（2025 JACS）
     - 通常IRI微降(-5%)，表达提升(+5%)
     - 仅当表达是瓶颈时考虑

R12: R37→T（如果C端是R/K）
     - C端全Thr化
     - 预期: TH +4-5%, IRI +1-2%
     - 这是最终最优序列
```

### 阶段四：破坏性验证（R13-R15）

```
R13: T19→Q 测试
     - 验证T19是否最优
     - 通常IRI微降(-0.3%)，确认T19最优

R14: T3→S 破坏测试 ⚠️
     - 验证N端T2-T3-T4三联簇必要性
     - 预期: IRI -0.5~2.3%
     - 规则: 三联簇不可破坏！

R15: S3→T 回退确认
     - 恢复到R12最优序列
```

## 禁区速查表（37aa Type I骨架）

```
IBS核心（绝对不可突变）:
  T2, T13, T24, T35

结构保守区（forbidden_positions，不可突变）:
  D1, D5, A6-A12, L12, A14, A18, L23, A34

N端三联簇（不可破坏，已验证）:
  T2-T3-T4（T3S→IRI-0.57%）

安全突变位点（非禁区 + 非IBS核心）:
  A3, S4, A15, N16, A17, A19, A20, A21, K22,
  A25, D26, N27, A28, A29, A30, A31, A32, A33, A36, R37

E19微调区（备选，非必需）:
  T: IRI最优（推荐）
  Q: 表达优先
  E: 不推荐（牺牲IRI）
```

## 常见陷阱

### 陷阱1：渐进式Thr无效后仍坚持保守策略
- **现象**: R1-R3 TH无变化，继续尝试更多单/双突变
- **真相**: 非IBS面单点Thr主要改善IRI，TH需要密集阵列才能突破
- **解决**: R3后如果TH无变化，立即跳转密集Thr化（阶段二）

### 陷阱2：在IBS边缘引入Glu/Asn
- **现象**: A25E、A3N等看似合理的边缘突变
- **真相**: 这些位点离冰面太远，无法产生有效冰结合
- **解决**: Glu/Asn应直接在IBS面上使用（但IBS核心在禁区）

### 陷阱3：尝试恢复野生型盐桥
- **现象**: A18K（禁区）、K22E看似恢复天然结构
- **真相**: A18在禁区，K22E无TH效果
- **规则**: 密集Thr阵列 > 盐桥恢复

### 陷阱4：过早停止优化
- **现象**: R9 TH达到0.89°C后认为完成
- **真相**: R10(K22T)+R12(R37T)可额外提升~9% TH和~3% IRI
- **解决**: 至少完成到R12

### 陷阱5：T19→E的IRI诱惑
- **现象**: E19表达提升5%看似吸引人
- **真相**: IRI下降5%的代价超过表达收益（TH优先场景）
- **规则**: TH/IRI优先场景保持T19

## 验证方法

### 每轮检查
1. `forbidden_check.passed === true` — 未触碰禁区
2. `ibs_integrity_check.passed === true` — IBS核心T2/T13/T24/T35完整
3. 序列长度 = 37aa
4. N端T2-T3-T4三联簇完整（R7后）
5. 无CRITICAL警告

### 阶段里程碑
- **R7后**: TH预测值至少翻倍（如0.19→0.49）
- **R9后**: TH预测值 ≥ 0.85°C
- **R12后**: TH预测值 ≥ 0.95°C，IRI改善 ≥ 70%
- **R14 (T3S)**: IRI下降→确认三联簇必要性
- **R15**: 恢复到R12最优水平

### 最终验证
```
afp_design_summary(
  original_sequence, final_sequence,
  design_target, application_scenario,
  mutation_history, original_performance, final_performance
)
→ 确认: TH变化>+300%, IRI改善>65%, PASS轮次>50%
```

## 预期性能轨迹

```
基线:  TH=0.16°C, IRI=1.82µM, Thr=4/37(10.8%)
R1-2:  TH=0.16-0.19, IRI改善7-34%（渐进）
R7:    TH=0.49 (+206%), IRI改善49%（突破！）
R8:    TH=0.69 (+331%), IRI改善59%
R9:    TH=0.89 (+456%), IRI改善68%
R10:   TH=0.93 (+481%), IRI改善70%
R12:   TH=0.97 (+506%), IRI改善71%（最优）
```

## 最终推荐序列模板

```
DTTTDAAAAAALTATTTATTTTLTTTTTTTTTTATTT
```

关键特征：N端T2-T3-T4三联簇、IBS核心完整、C端14连Thr阵列、22/37 Thr (59.5%)
