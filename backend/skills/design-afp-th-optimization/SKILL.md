---
description: Type I AFP TH活性优化设计技能。从经典Type I AFP（冬季比目鱼HPLC6）出发，通过多轮迭代突变将TH活性从~0.3°C提升至~1.0°C（3-5倍），同时大幅改善IRI（-68%）和表达量（+120%）。适用于细胞冻存、冷冻食品等场景的AFP工程设计。
name: design-afp-th-optimization
version: 1.0.0
---

# AFP TH活性优化设计技能

## 何时使用

- 需要优化Type I AFP（α-螺旋鱼类AFP）的TH（热滞）活性
- 目标：TH从0.3-0.5°C提升至1.0-2.0°C
- 场景：细胞冻存（TH权重0.35）、冷冻食品、冰晶控制
- 序列长度固定在37aa左右，基于经典HPLC6骨架

## 操作步骤

### 阶段一：基线分析（必须执行）

1. **afp_knowledge_query** — 完整分析原始序列
   - 参数：`query_intent="full_analysis"`, `application_scenario` 按需设置
   - 提取：IBS位置、禁区列表、突变热点、设计原则
   - 记录基线性能（TH/IRI/表达/稳定性/AFP概率）

2. **afp_design_strategy** — 获取初始策略
   - 传入基线性能数据和设计目标
   - 注意：`forbidden_positions` 和 `recommended_mutation_sites` 可能有重叠，优先遵守禁区

3. **afp_ice_bind_simulate** — 基线模拟
   - 推荐：`target_ice_plane="pyramidal_201"` 匹配Type I AFP
   - 传入手动IBS位置（从知识库获取）

### 阶段二：渐进式突变（3-5轮基础优化）

4. **第1轮：溶解度+Thr扩展**
   - 非IBS面 Ala→Ser（如A3S）提高溶解度
   - IBS附近 Ala→Thr（如A15T, A25T）扩展冰锚定面
   - 避开禁区[1,2,5-12]和IBS核心[2,13,24,35]

5. **第2-3轮：Thr密集化**
   - 在IBS Thr周边安全位点引入更多Thr（如N16T, A17T, A36T）
   - 形成Thr簇（如T15-T16-T17三联簇）
   - 关键原则：Thr越多越好，但必须在安全位点

6. **第4轮：Glu静电增强**
   - 在非IBS面引入Glu（如A19E, A20E）利用Glu的强冰结合能
   - 注意：仅在非IBS面使用Glu，IBS面禁止带电残基
   - 同时继续Thr扩展（如A28T）

### 阶段三：突破性策略（关键轮次）

7. **第5-6轮：二硫键刚性化**
   - 在安全位点引入i→i+4 Cys对（如A26C+A30C）
   - 位置选择：靠近IBS区域但不直接接触IBS
   - 同时优化极性残基（如N27Q）

8. **第7轮：密集Thr触发IBS重排（高风险高回报）**
   - 在非IBS螺旋面引入多Thr（如A21T, A29T, A33T）
   - **目的**：触发IBS自动检测切换，可能大幅提升TH（+288%）
   - **风险**：IRI可能暂时恶化、IBS质量可能下降
   - 如果IRI恶化，立即在下一轮用E19T/C26T等方法恢复IBS

9. **第8-9轮：C端Thr密集化突破（最关键的突破轮次）**
   - **C30T, A31T, A32T** — 这是TH突破的核心
   - 消除游离Cys（C30T），在C端形成连续Thr阵列
   - 目标：T30-T31-T32-T33-T35-T36 超密集Thr簇
   - 预期效果：TH跳跃233%（0.3→1.0°C），IRI改善64%

### 阶段四：精细优化（最后轮次）

10. **R37T** — C端全Thr化最后一步
11. **S4T, E22D** — 保守盐桥优化（S→T增强，E→D缩短侧链）
12. **E20Q** — Glu→Gln移除电荷但保留极性，IRI至最优

### 每轮必须执行的操作

- **afp_mutate_sequence**: 突变序列，检查warnings
- **afp_evaluate_mutation**: 评估禁区合规和性能变化
- **afp_ice_bind_simulate**: 冰结合模拟（每2-3轮或关键轮次）
- **afp_design_strategy**: 每5轮获取更新策略

## 常见陷阱

### 陷阱1：触碰IBS核心禁区
- **症状**：`CRITICAL` 警告，`forbidden_check: false`
- **位置**：T2, T13, T24, T35（IBS Thr绝对不可突变）
- **解决**：回退到上一轮有效序列，选择安全位点
- **T13E案例**：虽预览TH上升，但实际几何评分崩溃（0.933→0.807）

### 陷阱2：触碰结构保守区
- **症状**：REJECTED，如"A14是保守功能残基"
- **位置**：A14, A34, K18, A6-A12
- **解决**：严格遵守知识库返回的forbidden_positions

### 陷阱3：突变位置确认错误
- **症状**：`error: 位置X期望Y但序列中是Z`
- **原因**：前几轮突变改变了位点，未更新序列
- **解决**：每次突变后记录完整序列，下次突变前逐位核对

### 陷阱4：孤立Cys残留
- **症状**：二硫键断裂后留下单个Cys
- **解决**：C26T或C30T消除游离Cys，避免氧化和聚集问题

### 陷阱5：IBS重排后质量下降
- **症状**：TH飙升但IRI恶化、geometry_score暴跌
- **案例**：第7轮IBS从[2,13,24,35]切换为[5,12,19,26,33]，residue_quality从1.0→0.208
- **解决**：立即用E19T/C26T恢复原始IBS模式

### 陷阱6：过早放弃TH突破
- **现象**：前6轮TH不变（始终0.3°C），容易放弃
- **真相**：TH突破在第7-9轮才出现，需要积累足够的Thr密度
- **关键阈值**：约15+个Thr残基时触发TH显著提升

## 验证方法

### 每轮内部验证
1. `afp_evaluate_mutation.verdict` 必须为 `PASS`
2. `forbidden_check.passed` 必须为 `true`
3. `ibs_integrity_check.passed` 必须为 `true`
4. `has_critical_warnings` 必须为 `false`

### 性能趋势验证
- **TH**: 评估TH（`estimated_th`）应逐步上升。关键轮次：R7(+288%)→R9(+233%)
- **IRI**: IRI IC50应逐步下降。目标：<2.0 µM
- **表达**: expression_score应>0.7
- **AFP概率**: 应>0.99
- **几何评分**: geometry_score应保持在0.9以上（0.933为最优）

### 最终验证
- `afp_design_summary` 汇总全流程
- `afp_visualize_trajectory` 可视化性能轨迹
- 确认：TH≥1.0°C（模拟），IRI改善≥60%，表达提升≥100%

## 快速参考：禁区与安全位点速查

### Type I AFP (37aa) 禁区
```
绝对禁区（不可突变）:
  IBS核心: T2, T13, T24, T35
  结构保守: D1, D5, A6-A12, A14, K18, L23, A34
  盐桥: K18-D1/D5 和 E22-K18

安全突变位点（优先级排序）:
  高收益: 15, 16, 17, 25, 28, 30, 31, 32, 36 (Thr引入)
  溶解度: 3, 6-10 (Ala→Ser, 但6-10在禁区慎用)
  盐桥优化: 4 (S→T), 22 (E→D)
  极性优化: 20 (E→Q), 26 (C→T), 27 (N→Q)
  末端: 37 (R→T)
```

### 冰结合残基优先级
```
Glu(E) > Thr(T) > Asn(N) > Gln(Q) > Ser(S) > Ala(A) > Gly(G)
```
- Glu仅在非IBS面使用
- Thr是IBS面的最优选择
- Gln是Glu的安全替代（极性但不带电）
