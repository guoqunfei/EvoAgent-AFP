---
description: Type I AFP (α-helical fish) 多轮迭代优化设计。适用于细胞冻存等TH+IRI双目标场景。包含完整的 afp_knowledge_query
  → afp_design_strategy → 迭代(mutate→evaluate→simulate) → afp_design_summary 管道，以及Thr密度阈值、IBS平面偏移、Glu工程禁区等关键设计规则。
name: design-afp-type1-optimization
version: 1.0.0
---
# Type I AFP 多轮迭代优化设计

## 何时使用

当你需要对 **Type I AFP（α-螺旋，鱼源抗冻蛋白）** 进行多轮迭代优化设计时使用此技能。典型触发场景：
- 用户提供 Type I AFP 序列并要求优化 TH/IRI/表达
- 应用场景为细胞冻存、冷冻面团、肉类保鲜等
- 需要平衡 TH活性、IRI活性、表达量和稳定性 的多目标优化
- 序列特征：富含 Ala（>50%）、IBS Thr 间距 16.5Å、靶向金字塔冰面 {20-21}

## 操作步骤

### 阶段 1：初始分析（必做）

```
Step 1: afp_knowledge_query(sequence, query_intent='full_analysis', application_scenario)
    → 获取 AFP 类型、IBS 残基、禁区列表、突变热点、理化特征

Step 2: afp_design_strategy(current_sequence, performance_data, design_target, application_scenario, design_history=[])
    → 获取初始设计策略和推荐突变位点
```

### 阶段 2：迭代设计循环（核心）

每轮迭代执行以下三步：

```
Step 3: afp_mutate_sequence(original_sequence, mutations, rationale)
    → 执行突变，检查 warning 和 has_critical_warnings
    → 每次突变 1-3 个位点，避免 5 个以上同时突变

Step 4: afp_evaluate_mutation(original_sequence, mutated_sequence, mutations, application_scenario)
    → 关注 verdict（PASS/REJECT）、forbidden_check、ibs_integrity_check
    → 记录 th_change_pct、iri_change_pct、afp_probability_change

Step 5: afp_ice_bind_simulate(sequence, original_sequence, target_ice_plane='auto')
    → 关注 ibs_positions_used 是否保持 [2,13,24,35]（Type I 标准）
    → 关注 target_ice_plane 是否保持 Pyramidal {20-21}
    → 关注 overall_geometry_score（目标 ≥ 0.85）
    → 关注 spacing_match_score（目标 ≥ 0.80）
```

### 阶段 3：策略调整与方向选择

每 3-5 轮后调用：

```
Step 6: afp_design_strategy(current_sequence, performance_data, design_target, 
          application_scenario, design_history)
    → 基于历史数据获取更新策略
    → 注意 next_step_suggestion
```

### 阶段 4：最终汇总

```
Step 7: afp_design_summary(original_sequence, final_sequence, design_target, 
          application_scenario, mutation_history, original_performance, final_performance)
```

## 核心设计规则（从15轮实战中提取）

### 安全突变（高成功率）

| 突变类型 | 示例 | 预期效果 | 风险 |
|----------|------|----------|------|
| 非IBS面 Ala→Ser | A15S, A17S, A19S | 表达↑，IRI↑ | 极低 |
| Asn→Thr 升级 | N16T, N27T | IRI↑，afp_prob↑ | 低 |
| IBS邻近 Thr扩展 | A25T, A36T | IRI大幅↑ | 中 |
| i,i+4 二硫键 | A26C+A30C | 刚性化，IRI↑ | 中 |
| Gln H键引入 | A3Q | 安全极性增强 | 低 |
| 电荷保留突变 | R37K | 中性或微正 | 极低 |

### 危险突变（应避免）

| 突变类型 | 示例 | 后果 | 机制 |
|----------|------|------|------|
| IBS核心Thr突变 | T2*, T13*, T24*, T35* | 活性崩溃-80% | 破坏冰晶格匹配 |
| 非IBS面 Glu引入 | S4E, T25E | afp_prob↓33% | 负电荷干扰 |
| Thr密度 >27% | 10+ Thr / 37aa | IBS偏移 {20-21}→{11-20} | 模型重识别 |
| 大体积IBS面残基 | Phe/Trp/Tyr引入IBS | 破坏平坦性 | RMSD>1Å |
| 禁区突变 | [1,2,5-14,18,23,24,34,35] | 功能丧失 | 保守残基破坏 |

### Thr密度阈值定律（新发现）

- Type I AFP (37aa) 在 ~27% Thr含量（10/37）存在临界点
- 超过此阈值：IBS识别从 [2,13,24,35] 偏移至 [5,12,19,26,33]
- 冰面从 {20-21} 切换到 {11-20}，几何评分从 0.93→0.65
- **解决方案**：T25S（降级一个非核心Thr为Ser）可恢复IBS识别
- 此规律可能推广至其他 Type I 变体

### 突变优先级排序

1. **第一优先**：非IBS面 Ala→Ser（安全，多维度改善）
2. **第二优先**：Asn→Thr 升级（提升冰结合残基质量）
3. **第三优先**：IBS邻近 Thr扩展（IRI大幅改善）
4. **第四优先**：二硫键引入（刚性化，需找 i,i+4 合适位点）
5. **第五优先**：Gln H键网络（比Glu安全）
6. **避免**：Glu工程、Thr过密、禁区突变

## 常见陷阱

### 陷阱 1：IBS 平面偏移
**症状**：ibs_positions_used 从 [2,13,24,35] 变为 [5,12,19,26,33]，target_ice_plane 变为 {11-20}
**原因**：Thr密度过高、过多极性残基引入
**解决**：回退最近 1-3 个突变，或使用 T25S 降级

### 陷阱 2：afp_probability 暴跌
**症状**：afp_prob 从 0.99 跌至 0.66 以下
**原因**：Glu（负电荷）引入非IBS面；净电荷变化过大
**解决**：回退 Glu 突变，改用 Gln 或保持 Ala

### 陷阱 3：单点突变触发连锁偏移
**症状**：IRI看似改善但 IBS 面已切换
**原因**：在 Thr密度临界点附近，任何额外极性残基都可能触发
**解决**：每轮都检查 ibs_positions_used，不只看 IRI 改善

### 陷阱 4：过度优化单维度
**症状**：IRI 持续改善但 TH 不动
**原因**：Type I AFP 的 TH 主要由 IBS 核心 Thr 决定，非IBS突变对TH影响有限
**解决**：接受 TH 提升主要通过 estimated_th 体现；IRI 和 expression 是多轮优化的主要收益

## 验证方法

### 每轮必查清单

```
□ forbidden_check.passed == true
□ ibs_integrity_check.passed == true
□ ibs_positions_used == [2, 13, 24, 35]（Type I 标准）
□ target_ice_plane == "Pyramidal plane {20-21}"
□ overall_geometry_score >= 0.85
□ spacing_match_score >= 0.80
□ afp_probability >= 0.85（理想 ≥ 0.95）
□ verdict 为 PASS 或 GOOD
```

### 最终序列验收标准

```
□ afp_probability >= 0.99
□ IRI IC50 改善 ≥ 40%
□ Expression 提升 ≥ 50%
□ IBS 保持原始识别
□ 净电荷在 -2 到 +1 之间（细胞冻存安全性）
□ 无 Cys 奇数量（二硫键必须偶数）
```

### 迭代终止条件

- 连续 3 轮 IRI 无显著改善（<2%）
- IBS 连续 2 轮偏移且回退无效
- 达到设计目标（IRI<1.5µM 或 TH>0.5°C）
- 完成 15-20 轮（边际收益递减）
