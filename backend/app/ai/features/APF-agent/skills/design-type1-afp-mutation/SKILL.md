---
description: Type I AFP (α-helical fish) 抗冻蛋白的迭代突变设计。适用于37aa富含Ala的Type I AFP序列，目标应用为细胞冻存、食品冷冻等。涵盖IBS面/非IBS面突变策略、禁区规避、TH/IRI/表达多目标优化。当用户提供Type
  I AFP序列并要求提升TH活性或综合性能时使用。
name: design-type1-afp-mutation
tags:
- AFP
- Type-I
- mutation-design
- protein-engineering
- cell-cryopreservation
version: 1.0.0
---
# Type I AFP 迭代突变设计技能

## 何时使用

- 用户提供疑似 Type I AFP 序列（富含Ala、37aa左右、含T2/T13/T24/T35特征Thr）
- 设计目标：提升TH活性、IRI活性、表达量或综合性能
- 应用场景：细胞冻存(cell_cryopreservation)、食品冷冻、冷冻面团等
- 需要多轮迭代优化（预期10-20轮）

## 操作步骤

### Phase 1: 知识库分析（1-2次调用）

1. **`afp_knowledge_query`** — 完整分析（`query_intent='full_analysis'`）
   - 确认AFP类型、置信度
   - 提取IBS残基位置（绝对禁区！）
   - 获取禁区列表（`forbidden_positions`）
   - 获取突变热点（`mutation_hotspots`）
   - 记录基线性能：TH、IRI、表达、稳定性

2. **`afp_design_strategy`** — 获取策略建议
   - 传入当前序列和基线性能
   - 注意：策略工具返回的 `forbidden_positions` 可能不完整，以知识库为准
   - 策略工具推荐的突变位点可能与禁区重叠——以知识库禁区为准！

### Phase 2: 安全起步（Round 1-3）

3. **第一轮：非IBS面 Ala→Ser**
   - 从 `mutation_hotspots` 中选择3个非IBS面Ala位点
   - 避开所有禁区位置
   - 目的：安全地提升溶解度和表达，不影响IBS
   - 预期：TH不变、IRI微改善、表达提升

4. **第二轮：IBS面 Ala→Asn（第一次活性尝试）**
   - 识别IBS面残基（α-螺旋中与T2/T13/T24/T35同面的残基，间距约3-4个位置）
   - 从IBS面Ala中选择不在禁区的位点（如A20、A31）
   - 避免禁区内的位点（如A6、A9等）
   - Ala→Asn：中性酰胺侧链，排名第三冰结合残基

5. **每轮必须双验证**：
   - `afp_evaluate_mutation` — 禁区检查 + 性能变化
   - `afp_ice_bind_simulate` — 冰结合模拟（靶向 `pyramidal_201`）

### Phase 3: 深度探索（Round 4-10）

6. **尝试IBS面增强策略（按优先级）**：
   - **Asn→Thr**（最优先！）：IBS面N→T，与核心Thr同类型，最可能提升TH
   - ~~Ala→Glu~~：虽然2025 JACS称Glu结合能高，但在Type I IBS面引入负电荷破坏平坦性 → 失败
   - ~~Asn→Gln~~：侧链多一个CH2，在IBS面干扰几何 → IRI回退

7. **尝试非IBS面增强**：
   - Ala→Gln（A15Q/A19Q）：提升极性但不干扰IBS ✓
   - Ala→Ser持续化：安全但过度Ser化导致Type I类型漂移

8. **应避免的策略**（已证伪）：
   - ❌ 二硫键工程（C15-C19/C29-C33）：表达下降，无TH增益
   - ❌ 电荷工程（A21R/A32R）：类型漂移为De novo
   - ❌ 盐桥微调（E22D）：类型漂移
   - ❌ 6-Thr IBS（T2/T13/T20/T24/T31/T35）：TH回退，过度拥挤

### Phase 4: 靶向测试（1轮）

9. **`afp_ice_bind_simulate`** — 测试不同冰面
   - Type I AFP天然靶向金字塔面 `pyramidal_201`
   - 基面 `basal` 测试：spacing_match_score 通常 <0.6 → 不适合
   - 棱面 `prism` 测试：spacing_match_score 通常为0 → 不适合

### Phase 5: 收敛与报告

10. **确定最佳序列**：通常在第10-15轮产生
    - 优先选择保持Type I分类的序列
    - TH提升即使微小（+25%）也是Type I框架内的显著成果

11. **`afp_design_summary`** — 生成最终报告
12. **`afp_visualize_trajectory`** — 生成轨迹图

## 常见陷阱

### 陷阱1：禁区判断矛盾
- **现象**：知识库 `forbidden_positions` 与策略 `forbidden_positions` 不一致；策略的 `recommended_mutation_sites` 可能与禁区重叠
- **解决**：**以 `afp_knowledge_query` 返回的禁区为准**。策略工具的禁区列表通常更短且不完整
- **验证**：突变后 `afp_evaluate_mutation` 会做禁区检查，REJECTED 则回退

### 陷阱2：TH难以提升
- **现象**：Type I 37aa框架下，TH从0.16°C起步，多轮非IBS面突变（Ala→Ser/Gln）TH纹丝不动
- **根因**：TH受限于4-Thr IBS架构（间距16.5Å匹配金字塔面），非IBS面突变不直接影响冰结合
- **突破方法**：**N20T**（IBS面Asn→Thr）是唯一成功的TH提升策略(+25%)
- **现实预期**：37aa单体框架可能无法达到0.5°C TH目标

### 陷阱3：IBS面引入Glu
- **现象**：N20E预期提升TH（Glu→4×结合能），实际IRI回退、AFP概率下降
- **根因**：Glu负电荷破坏IBS平坦性（RMSD > 1Å规则）
- **教训**：2025 JACS的Glu优势可能适用于其他AFP类型，但Type I的α-螺旋IBS面对电荷敏感

### 陷阱4：Gln侧链过长
- **现象**：N16Q/N27Q/N31Q导致IRI回退
- **根因**：Gln比Asn多一个CH2，侧链酰胺基位置偏移，H-bond几何失配
- **教训**：IBS面的H-bond供体长度需精确匹配冰晶格（~2.8Å），Gln的额外柔性带来熵损失

### 陷阱5：6-Thr IBS过度
- **现象**：N20T+N31T形成6-Thr IBS，TH从0.20回退到0.16
- **根因**：T13-T20间距7残基≈10.5Å，不匹配任何标准冰面间距（16.5Å/7.4Å/4.5Å）
- **教训**：5-Thr（T2/T13/T20/T24/T35）是37aa框架的最佳IBS配置

### 陷阱6：类型漂移
- **现象**：过多非IBS面突变（≥7个位点）导致AFP类型从Type I变为De novo designed
- **根因**：Ser/Gln含量过高稀释了Type I的Ala-rich特征（原始Ala=62%，降至<50%触发漂移）
- **解决**：保持Ala含量≥50%，总突变数控制在5-7个

## 验证方法

### 每轮验证清单
1. ✅ `afp_evaluate_mutation.verdict` ≠ REJECTED
2. ✅ `afp_evaluate_mutation.forbidden_check.passed` = true
3. ✅ `afp_evaluate_mutation.ibs_integrity_check.passed` = true
4. ✅ `afp_evaluate_mutation.mutated_analysis_summary.afp_type` = "Type I"（避免漂移）
5. ✅ `afp_ice_bind_simulate.geometry_score.spacing_match_score` ≥ 0.8（金字塔面）
6. ✅ 突变描述中无CRITICAL警告

### 最终验证
- TH预测相对变化 ≥ 0（至少不下降）
- IRI IC50相对原始改善 ≥ 10%
- 表达评分 ≥ 0.6
- AFP概率 ≥ 0.7
- Type I置信度保持 ≥ 0.8

## 关键设计规则（从17轮经验提炼）

| 规则 | 详情 |
|------|------|
| **IBS核心不可触** | T2/T13/T24/T35绝对禁区，突变直接REJECTED |
| **IBS面优先Thr** | Asn→Thr是唯一提升TH的策略；避免Glu/Gln/Lys/Arg |
| **非IBS面可自由Ser化** | Ala→Ser安全，但≤5个位点以防类型漂移 |
| **Gln仅用于非IBS面** | A15Q/A19Q提升IRI和表达，不可放在IBS面 |
| **二硫键策略无效** | Type I α-螺旋不适合二硫键刚性化 |
| **不要在C端2残基内突变** | A34→S REJECTED，A36可能是最后一个安全位点 |
| **5-Thr IBS最优** | 超过5个Thr反而降低TH |
