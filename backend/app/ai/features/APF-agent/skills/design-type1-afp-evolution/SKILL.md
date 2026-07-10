---
description: Type I AFP（α-螺旋鱼源）多轮进化优化技能。适用于已知序列的Type I AFP进行TH/IRI/表达多目标优化，遵循禁区规避→非IBS面亲水化→二硫键刚性化→S→T全覆盖的四阶段优化路线。特别适合细胞冻存场景（TH+安全性优先）。
name: design-type1-afp-evolution
version: 1.0.0
---
# Type I AFP 多轮进化优化

## 何时使用

当你需要对一条 **Type I AFP（α-螺旋，鱼源）** 序列进行多轮突变优化时使用此技能。典型场景：
- 给定一条 Type I AFP 序列，需要提升 TH 活性、IRI 活性或表达量
- 应用场景为细胞冻存（TH权重0.35 + 安全性权重0.2）
- 需要按阶段推进：先分析，再亲水化，再结构刚性化，最后精细化

## 操作步骤

### 阶段 0：知识库分析（必须第一步）

1. 调用 `afp_knowledge_query`，参数 `query_intent='full_analysis'`
2. 从结果中提取：
   - **IBS 核心残基**（通常是 T2/T13/T24/T35，靶向金字塔面 {20-21}）
   - **禁区列表**（`forbidden_positions`）——**绝对不可突变的位置**
   - **突变热点**（`mutation_hotspots`）——建议的可突变位置
   - **当前性能估算**（TH/IRI/表达/稳定性）

### 阶段 1：非IBS面亲水化（1-4轮）

**目标**：提升表达量和IRI，为后续结构改造打基础

3. 选取非IBS面且**不在禁区**的 Ala 位置，执行 `afp_mutate_sequence`：
   - 第一轮：3个 Ala→Ser（如 A15S/A17S/A19S）
   - 第二轮：扩展至C端 Ala→Ser（如 A25S/A28S/A30S）
   - 每轮调用 `afp_evaluate_mutation` 评估
4. 当表达评分达到 0.7+ 后，尝试引入 Asn：
   - Ala→Asn（如 A20N/A29N/A33N）增强冰结合H-bond
5. 可选：引入 Gln（Ala→Gln）扩展H-bond网络
   - 但注意 Gln 侧链较大，IRI 改善有限

### 阶段 2：结构刚性化（5-7轮）——TH 突破关键

**目标**：打破 TH 瓶颈

6. **引入二硫键**：找 i→i+4 的残基对（α-螺旋同侧），将两个 Ser 改为 Cys
   - 验证：`afp_mutate_sequence` 不应触发 CRITICAL 警告
   - 示例：S15C/S19C
   - 预期效果：TH 大幅提升（summary层），但 IRI 可能暂时恶化
7. 在二硫键基础上**修复 IRI**：
   - 将过大的 Gln 回退为 Ser（Q→S），减小侧链体积
   - C端继续 Ser 化（A→S）
8. **去电荷优化**：E→Q（如 E22Q）
   - Glu 负电荷可能干扰冰面，改为中性 Gln
   - 预期：AFP 概率大幅回升（+10-20%）

### 阶段 3：S→T 全覆盖（8-13轮）——精细打磨

**目标**：最大化 AFP 概率和 IRI

9. 逐个将非IBS面的 Ser 改为 Thr：
   - 先从 N端开始（S4T）
   - 然后中间区域（S17T/S25T/S28T）
   - 最后 C端（S30T/S31T/S32T）
   - 最后剩余 Ser（S21T）
10. **关键突破点**：N16Q + R37Q（Asn→Gln 扩展侧链 + C端去正电荷）
    - 可触发 TH 模拟层面的大幅提升

### 阶段 4：收尾与报告（14-15轮）

11. 避免在 IBS 邻近位置做 N→Q（如 N27Q/N33Q 会导致 IRI 恶化）
12. 避免触碰禁区位置（L23、A14 等邻近 IBS 的位置）
13. 最后一轮完成后调用：
    - `afp_ice_bind_simulate` 确认最终性能
    - `afp_visualize_trajectory` 生成轨迹图
    - `afp_design_summary` 生成完整报告

## 常见陷阱

### 禁区陷阱
- **L23**：邻近 IBS T24，任何突变（包括保守的 L→I）都会触发 CRITICAL
- **A14**：在 T13(IBS) 和 C15(二硫键) 之间，不可突变
- **IBS 核心 Thr（T2/T13/T24/T35）**：绝对不可突变，任何改变导致活性崩溃

### 评估一致性陷阱
- `afp_evaluate_mutation` 的 `simulation_comparison` 和 `mutated_analysis_summary` 可能给出不同的 TH 估计
- 关注 **变化趋势** 而非绝对值
- `simulation_comparison.changes.verdict` 是最终判定依据

### 过度亲水化陷阱
- Ala→Ser 过多（>6处）后边际收益递减
- Gln（Q）大量引入后 IRI 可能恶化，需要回退

### N→Q 陷阱
- N→Q 在 C端 IBS 邻近位置（N27、N33）导致 IRI 恶化
- 但 N16→Q（螺旋中部非IBS面）是安全的且可能有益

## 验证方法

### 每轮验证
1. `afp_evaluate_mutation` 返回 `verdict` 不是 REJECTED
2. `forbidden_check.passed == true`
3. `ibs_integrity_check.passed == true`
4. IRI 改善或至少不恶化超过 10%

### 阶段性验证
1. **阶段1完成**：表达评分 ≥ 0.7
2. **阶段2完成**：TH summary 层有明显提升（+50%以上），AFP 概率 ≥ 0.75
3. **阶段3完成**：AFP 概率 ≥ 0.99，IRI 累积改善 ≥ 50%

### 最终验证
1. `afp_ice_bind_simulate` 几何评分 ≥ 0.9
2. `comparison_with_original.verdict` 为 EXCELLENT 或 GOOD
3. TH 提升 ≥ 100%，IRI 改善 ≥ 50%
4. 序列长度不变（37 aa），IBS 核心 Thr 完整保留

## 成功案例参考

原始序列：`DTASDAAAAAALTAANAKAAAELTAANAAAAAAATAR`
最终序列：`DTATDAAAAAALTACQTKCNTQLTTSNTNTTTNATSQ`

| 指标 | 原始 | 最终 | 变化 |
|:---|:---|:---|:---|
| TH | 0.3°C | 1.0°C | +233% |
| IRI IC50 | 3.47 µM | 1.22 µM | -64.8% |
| 表达 | 0.358 | 0.810 | +126% |
| AFP概率 | 0.909 | 0.9993 | +10% |
