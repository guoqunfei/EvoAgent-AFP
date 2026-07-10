---
description: Type I AFP在TH突破后的IRI精细打磨策略。在TH+233%突破达成后，通过E19Q等微调将IRI推至70%+峰值。涵盖R10-R15阶段的所有成功/失败模式，包括禁区A34验证、C端Ser陷阱。与design-afp-thr-density-breakthrough配合使用。
name: afp-type1-finetune-iri-peak
version: 1.0.0
---

# AFP Type I IRI精细打磨策略（TH突破后）

## 何时使用

- **前置条件**：已通过 `design-afp-thr-density-breakthrough` 完成R1-R9，TH已达+233%突破（1.0°C）
- 序列状态：Type I骨架37aa，Thr≥20个，IBS核心T2/T13/T24/T35完整
- 目标：在TH保持1.0°C的前提下，将IRI从~69%推至70%+
- 场景：TH已满足需求，需要IRI最终微调

## 操作步骤

### 阶段一：确认基线（1个调用）

1. **afp_ice_bind_simulate**（target_ice_plane="pyramidal_201"）
   - 确认当前TH=1.0°C，IRI改善≥69%
   - 确认geometry_score=0.933（不变）
   - 记录当前19位残基（应为E或Q）

### 阶段二：E19精细打磨（R10-R12，3轮）

**R10 — E19D验证（预期失败但必须做）**
- 突变：E19D
- 预期结果：**IRI无变化**，TH无变化
- 目的：确认Glu侧链长度（-CH2-CH2-COO⁻）已最优，缩短为Asp（-CH2-COO⁻）破坏冰面匹配
- 判定：REJECTED，但这是有价值的负面数据

**R11 — E19Q峰值突破** ⭐ 最关键
- 突变：E19Q
- 原理：Glu→Gln移除负电荷（-COO⁻→-CONH₂），但保留极性酰胺侧链
- 预期：**IRI改善+4~5%，累计突破70%**
- 判定标准：IRI累计改善≥70%即为成功
- 实例：IRI 3.47→1.01µM（-70.9%）

**R12 — Q19N验证（预期失败）**
- 突变：Q19N（若R11后19位为Q）
- 预期结果：IRI无变化
- 原理：Asn侧链比Gln短一个碳，H-bond几何不再最优
- 判定：REJECTED

### 阶段三：C端验证（R13-R14，预期均失败）

**R13 — T36S**
- 突变：T36S
- 预期：**IRI恶化+2%**（1.01→1.03µM），TH微降
- 原理：C端密集Thr区域（T28-T37）不可引入Ser——Ser较短侧链破坏末端冰结合连续性

**R14 — T37S**
- 突变：T37S
- 预期：**IRI恶化+2%**（同R13）
- 规则确认：**C端Thr→Ser一律有害**

### 阶段四：组合验证（R15）

**R15 — Q19E+T21S组合**
- 突变：Q19E + T21S（回退至E19并尝试T21S）
- 预期：**IRI恶化+7%**（最差结果）
- 结论：E19Q单独为最优，任何组合改动均劣化

## 禁区速查表（本次验证）

```
IBS核心（绝对不可突变）:
  T2, T13, T24, T35

结构保守区（不可突变，含本次新验证）:
  D1, D5, A6-A12, L12, A14, L23, A34, T18
  特别警告: A34 — 本次R8尝试A34T触发CRITICAL警告

C端密集Thr区（T28-T37）:
  ❌ 不可引入Ser（T36S/T37S均恶化IRI）
  ❌ 不可引入Glu（技能历史：T29E恶化）
  ✅ 保持纯Thr阵列

19位最优选择顺序:
  Q > E >> D = N（D和N无改善）
```

## 常见陷阱

### 陷阱1：盲目乐观——Preview vs 实际
- **症状**：`afp_mutate_sequence` 的 preview 显示 TH 持续上升（0.93→0.93），但 simulate 中 TH 始终 0.1°C
- **原因**：preview 使用简化的知识库模型，simulate 使用几何+物理化学模型
- **解决**：以 `afp_evaluate_mutation` 和 `afp_ice_bind_simulate` 的 comparison 为准

### 陷阱2：禁区A34
- **症状**：`has_critical_warnings: true`，`severity: CRITICAL`
- **触发**：A34T 或任何 A34 突变
- **解决**：立即回退。A34 在原始 forbidden_positions 列表中，不可触碰

### 陷阱3：C端Ser化
- **症状**：T36S 或 T37S → IRI 恶化 2%
- **原因**：C端 T28-T37 区域的 Thr 阵列需要一致的侧链长度（-CH(OH)-CH3）来维持冰结合的协同性
- **规则**：C端密集Thr区保持纯Thr，不引入任何其他残基

### 陷阱4：组合突变劣化
- **症状**：E19Q 单独效果好（-70.9%），但 Q19E+T21S 组合反而恶化（-68.9%）
- **原因**：多个微调叠加产生非线性负面交互
- **规则**：精细打磨阶段每次只改1个位点，确认改善后再考虑下一个

## 验证方法

### R11成功标准
- `afp_evaluate_mutation` → verdict: PASS 或 CAUTION（非REJECTED）
- `afp_ice_bind_simulate` → comparison.iri_improvement_pct ≥ 70%
- TH 保持 1.0°C（comparison.th_change_pct = 0%）
- geometry_score = 0.933（不变）

### 最终验证
- AFP概率 ≥ 99.99%
- IRI IC50 ≤ 1.01 µM
- 表达评分 ≥ 0.63
- 稳定性评分 ≥ 0.62

## 设计规则总结

| 规则 | 证据强度 | 来源 |
|------|----------|------|
| E19Q 优于 E19（IRI +4.7%） | 强 | 本次R11 |
| E19D 完全无收益 | 强 | 本次R10 |
| Q19N 无改善 | 中 | 本次R12 |
| C端 T→S 始终恶化 IRI | 强 | 本次R13/R14 |
| A34 绝对不可突变 | 强 | 本次R8 CRITICAL |
| 组合微调劣于单独最优 | 中 | 本次R15 |
| 精细打磨阶段单点突变 | 强 | 本次R10-R15 |
