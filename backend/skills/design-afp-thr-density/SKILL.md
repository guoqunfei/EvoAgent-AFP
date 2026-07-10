---
description: 通过迭代Thr密集化策略优化AFP的TH活性和IRI活性。从知识库分析出发，经过设计策略→突变→评估→模拟的闭环迭代（通常15+轮），将非IBS非禁区残基逐步替换为Thr以最大化冰结合能力。适用于Type
  I AFP骨架的从头优化，特别是需要同时提升TH和IRI的场景。
name: design-afp-thr-density
version: 1.0.0
---
# AFP Thr密集化设计技能

## 何时使用

- 需要对Type I（α-helical fish）AFP骨架进行TH/IRI活性优化
- 目标序列长度约37aa，含11-残基重复基序（T-X10-T motif）
- 设计要求：在不破坏IBS完整性的前提下最大化Thr含量
- 应用场景：冷冻食品、细胞冻存、转基因作物等需要增强抗冻活性的场景

## 操作步骤

### Phase 1: 前期分析（2-3步）

1. **知识库查询** — `afp_knowledge_query(sequence, query_intent='full_analysis', application_scenario)`
   - 获取AFP类型分类、IBS位置、禁区列表、已知基序
   - 记录所有禁区残基（保守功能残基），后续绝不触碰

2. **设计策略获取** — `afp_design_strategy(current_sequence, performance_data, design_target, application_scenario)`
   - 获取初始突变方向推荐
   - 理解TH vs IRI vs 表达 vs 稳定性的多目标权衡

3. **基线模拟** — `afp_ice_bind_simulate(sequence, original_sequence, ibs_positions, target_ice_plane='auto')`
   - 建立性能基线（TH、IRI IC50、几何评分、表达/稳定性）
   - 确认IBS残基和最佳匹配冰面

### Phase 2: 迭代突变循环（核心，10-15轮）

每轮严格遵守以下模式：

4. **选择靶点** — 遵循优先级规则：
   - 优先级1：非IBS、非禁区的 Ala/Ser/Asn → Thr（最安全，收益最大）
   - 优先级2：非IBS、非禁区的 Lys/Arg/Gln → Thr（带电→极性，需验证）
   - 优先级3：非IBS、非禁区的 Asp/Glu → Thr（酸性→极性，谨慎）
   - **绝对禁止**：IBS残基（通常为T2, T13, T24, T35）、禁区残基

5. **执行突变** — `afp_mutate_sequence(original_sequence, mutations, rationale)`
   - 每轮1-3个突变，不超过3个（便于追踪因果）
   - 记录 rationale，说明选择理由

6. **评估突变** — `afp_evaluate_mutation(original_sequence, mutated_sequence, mutations, application_scenario)`
   - 检查 verdict：PASS 继续 / WARNING 审慎 / REJECTED 回退
   - 关注 IBS integrity、forbidden check、TH/IRI变化

7. **冰结合模拟** — `afp_ice_bind_simulate(sequence, original_sequence, ibs_positions)`
   - 对比几何评分、TH估算、IRI估算的变化
   - 若IRI改善>10%或TH>0.5°C，记录为有效突变

8. **决定下一步**：
   - 若仍有非Thr安全位点 → 继续Thr密集化
   - 若TH停滞 → 尝试中等极性残基（Gln/Asn）调谐
   - 若IRI停滞 → 尝试表面电荷调谐（Asp/Glu）
   - 若均优化完毕 → 进入总结阶段

### Phase 3: 收尾（2步）

9. **设计策略复核** — 再次调用 `afp_design_strategy` 确认无遗漏优化方向

10. **生成最终报告** — `afp_design_summary(original_sequence, final_sequence, design_target, application_scenario, mutation_history, original_performance, final_performance)`
    - 汇总所有突变路径
    - 对比初始与最终性能
    - 提炼关键设计原则

## 常见陷阱

### 陷阱1: 禁区误触
- **症状**: afp_mutate_sequence 返回 warning 或 afp_evaluate_mutation 返回 REJECTED
- **根因**: 选中了IBS残基或保守功能残基作为突变靶点
- **解决**: 从afp_knowledge_query结果中提取禁区列表，交叉检查每个突变靶点

### 陷阱2: 19位Glu陷阱（Type I特有）
- **症状**: 在非IBS面中部（如位置19）引入Glu/Asp时，IRI改善但TH停滞
- **根因**: 酸性残基的负电荷在pH7下排斥冰面羟基，抵消了极性增益
- **解决**: 优先Thr（最佳），其次Gln/Asn（中性极性），避免Glu/Asp。若已引入Glu→尝试Glu→Gln→Asn→Thr的渐进路线

### 陷阱3: 过度突变
- **症状**: 一轮突变>3个位点，TH/IRI变化方向不一致，难以归因
- **根因**: 多点突变产生非线性交互效应
- **解决**: 每轮严格限制1-3个突变，TH和IRI分别追踪

### 陷阱4: 忽略表达/稳定性
- **症状**: TH/IRI持续上升但表达评分骤降（<0.3）
- **根因**: 过多Thr引入导致疏水性失衡或聚集倾向
- **解决**: 每轮关注 expression_score 和 stability_score，若expression<0.3则回退并保留部分Ala

### 陷阱5: 过早停止迭代
- **症状**: 3-5轮后TH似乎不再改善，认为已收敛
- **根因**: Type I骨架的Thr密度阈值效应——需要达到~60% Thr才会触发TH跃升
- **解决**: 坚持密集化直到所有安全位点耗尽（通常需10-15轮），注意TH的非线性跃升往往在最后几轮发生

## 验证方法

### 每轮验证
- `afp_evaluate_mutation` 返回 **PASS**（非WARNING或REJECTED）
- `afp_ice_bind_simulate` 的 `overall_assessment` 不恶化
- IBS integrity 保持 **passed: true**
- forbidden_check 保持 **passed: true**

### 中期验证（5轮后）
- TH估算 ≥ 0.5°C（相比基线0.16°C）
- IRI IC50 ≤ 2.5 µM（相比基线3.47 µM）
- AFP概率 ≥ 95%
- 表达评分 ≥ 0.4

### 最终验证
- TH估算 ≥ 0.8°C（提升≥400%）
- IRI IC50 ≤ 1.5 µM（改善≥60%）
- Thr含量 ≥ 55%（20/37）
- AFP概率 ≥ 99%
- 所有IBS残基完整保留
- 无禁区违规

## 关键设计规则速查

| 规则 | 说明 |
|------|------|
| **IBS不可侵犯** | T2, T13, T24, T35（及等效位点）绝不突变 |
| **Thr优先** | 在安全位点，Thr > Gln/Asn > Ser > Ala > Glu/Asp |
| **密集化阈值** | Thr>55%触发TH非线性跃升，>60%触发IRI大幅改善 |
| **19位警示** | 非IBS面中部避免酸性残基，Thr或中性极性最优 |
| **多点限制** | 每轮≤3个突变，保持可追溯性 |
| **四维追踪** | 每轮同时关注TH、IRI、表达、稳定性四个维度 |
