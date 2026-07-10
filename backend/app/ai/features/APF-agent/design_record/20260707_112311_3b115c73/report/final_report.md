# 🧬 AFP 抗冻蛋白智能设计 — 最终报告

| 项目 | 内容 |
|------|------|
| **会话 ID** | `20260707_112311_3b115c73` |
| **生成时间** | 2026-07-07 11:34:29 |
| **应用场景** | general |
| **总设计轮次** | 0 |
| **设计目标** | 请设计一个抗冻蛋白。

输入序列: MSLLSIITIGLAGLGGLVNGQRDLSVELGVASNFAILAKAGISSVPDSAILGDIGVSPAA
ATYITGFGLTQDSSTTYATSPQVTGLIYAADYSTPTPNYLAAAVANAETAYNQAAGFVDP
DFLELGAGELRDQTLVPGLYKWTSSVSVPTDLTFEGNGDATWVFQIAGGLSLADGVAFTL |

---

## 1. 输入序列深度分析

### 1.1 序列鉴定

输入序列为 **261 aa** 的抗冻蛋白，经知识库匹配鉴定为 **Type III (β-sandwich, fish)**（置信度 70%）。
该类型 AFP 主要来源于冬鲽鱼（*Pseudopleuronectes americanus*），以富含丙氨酸（Ala）的 α-螺旋结构为特征。

**各类型匹配得分**:

- Type III (β-sandwich, fish): `██████████████░░░░░░` 0.70

- Insect hyperactive (β-helical): `██████████████░░░░░░` 0.70

- Bacterial IBP: `████████████░░░░░░░░` 0.60

- Plant AFP: `██████████░░░░░░░░░░` 0.50

- Type I (α-helical, fish): `███████░░░░░░░░░░░░░` 0.35

### 1.2 冰结合面 (IBS) 架构

**IBS 核心残基**: `T2`, `T13`, `T24`, `T35` （位置 2, 13, 24, 35）
**靶向冰面**: Pyramidal plane {20-21}
**Thr 间距**: 16.5 Å — 精确匹配金字塔面 `{20-21}` 的氧原子晶格间距
**IBS 平坦性要求**: RMSD < 1.0 Å —— 不可引入大体积/带电残基

**序列位置标注**:
```
序列: MSLLSIITIGLAGLGGLVNGQRDLSVELGVASNFAILAKAGISSVPDSAILGDIGVSPAAATYITGFGLTQDSSTTYATSPQVTGLIYAADYSTPTPNYLAAAVANAETAYNQAAGFVDPDFLELGAGELRDQTLVPGLYKWTSSVSVPTDLTFEGNGDATWVFQIAGGLSLADGVAFTLAGGANSTNIAFQVGDDVTVGKGAHFEGVLLAKRFVTLQTGSSLNGRVLSQTEVALQKATVNSPFVPAPEVVQKRSNARQWL
IBS:   ▲          ▲          ▲          ▲                                                                                                                                                                                                                                  
位标:     ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0    ·    0 
```

### 1.3 物理化学特征深度解读

| 指标 | 数值 | 解读 |
|------|:----:|------|
| **Ala 含量** | 13.0% | 偏低 |
| **Thr 含量** | 8.8% | IBS 核心残基，间距 16.5Å 匹配金字塔面 |
| **Cys 含量** | 0.0% | 无二硫键 — 缺乏刚性化支架，TH 活性受限于鱼源级别 (~0.5°C) |
| **GRAVY** | 0.262 | 适中 |
| **pI** | 4.27 | 酸性蛋白 — 在生理 pH 下带负电 |
| **净电荷 (pH7)** | -8 | 带电偏高 — 可能影响安全性 |
| **不稳定指数** | 38.7 | 🟢 稳定 (<40) — 适合长期储存 |

### 1.4 设计约束分析

**禁区（不可突变残基）**: 共 20 个位置
`1, 2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 18, 23, 24, 34, 35, 44, 96, 98`

禁区包括：
- **IBS 核心 Thr**: `T2, T13, T24, T35` — 间距 16.5Å 匹配冰晶格，任一突变均导致活性崩溃
- **盐桥残基**: D1, D5, K18, E22 — 维持 α-螺旋帽化结构
- **IBS 面保守残基**: 不可引入 F/W/Y（大体积）、D/E（负电荷）、K/R（正电荷+大体积）

**突变热点 (推荐可突变位点)**:

- **P12** (`A`) → Ala→Ser可提高溶解度 [潜力: 0.7]
- **P31** (`A`) → Ala→Ser可提高溶解度 [潜力: 0.7]
- **P38** (`A`) → Ala→Ser可提高溶解度 [潜力: 0.7]
- **P40** (`A`) → Ala→Ser可提高溶解度 [潜力: 0.7]
- **P49** (`A`) → Ala→Ser可提高溶解度 [潜力: 0.7]
- **P59** (`A`) → Ala→Ser可提高溶解度 [潜力: 0.7]
- **P60** (`A`) → Ala→Ser可提高溶解度 [潜力: 0.7]
- **P61** (`A`) → Ala→Ser可提高溶解度 [潜力: 0.7]

**设计潜力评分**: 0.737 / 1.0
> 🟢 高设计潜力 — 有多个可安全突变的位点

### 1.5 基线活性预测

| 指标 | 预测值 | 评价 |
|------|:------:|------|
| TH (热滞后) | 0.09 °C | 鱼源级别 (~0.5°C) |
| IRI IC₅₀ | 3.11 µM | 中等 |
| 表达评分 | 0.492 | 🟡 偏低 — 可能与高疏水性 (GRAVY={gravy:.3f}) 有关 |
| 稳定性 | 0.824 | 🟢 稳定 (II={ii:.1f}<40) |

### 1.6 相关设计原则（来自文献）

- **IBS Thr间距必须匹配靶向冰面**: Thr残基在IBS上的间距必须为4.5Å（棱面）、7.4Å（基面）或16.5Å（金字塔面），偏差>10%将显著降低活性 [Strong (experimental)]
- **IBS必须保持平坦（RMSD < 1 Å）**: 冰结合面的Cα原子波动不应超过1Å。引入大体积残基(Phe/Trp/Tyr)或带电残基(Lys/Arg/Asp/Glu)到IBS将破坏平面性并丧失活性 [Strong (experimental)]
- **几何互补性可独立驱动显著的IRI活性**: 即使没有完美的氢键匹配，仅凭IBS与冰面的几何形状互补就足以产生可测量的IRI活性。这对de novo设计尤其重要 [Moderate (MD + experiment)]
- **融合标签可显著改善AFP表达量**: MBP和GST标签可将AFP表达量提高2-10倍。TAT细胞穿透肽融合可实现细胞内冰保护。标签必须放置在非IBS端以避免干扰冰结合 [Strong (experimental)]
- **IBS残基类型影响冰结合强度**: 冰结合残基优先级：Glu(E) > Thr(T) > Asn(N) > Gln(Q) > Ser(S) > Ala(A) > Gly(G)。带电残基(D/K/R)应严格避免在IBS上出现 [Moderate (multiple experimental studies)]
- **盐桥对α-螺旋型AFP的折叠至关重要**: Type I AFP中的Lys-Asp/Glu盐桥提供了α-螺旋的帽化稳定。突变这些盐桥残基将降低Tm并间接损害TH活性 [Strong (experimental)]

---

## 2. 设计迭代全过程

> ⚠️ 本轮未执行突变设计。

---

## 4. 序列对比

| 项目 | 序列 |
|------|------|
| **原始序列** | `MSLLSIITIGLAGLGGLVNGQRDLSVELGVASNFAILAKAGISSVPDSAILGDIGVSPAAATYITGFGLTQDSSTTYATSPQVTGLIYAADYSTPTPNYLAAAVANAETAYNQAAGFVDPDFLELGAGELRDQTLVPGLYKWTSSVSVPTDLTFEGNGDATWVFQIAGGLSLADGVAFTLAGGANSTNIAFQVGDDVTVGKGAHFEGVLLAKRFVTLQTGSSLNGRVLSQTEVALQKATVNSPFVPAPEVVQKRSNARQWL` |
| **最终序列** | `MSLLSIITIGLAGLGGLVNGQRDLSVELGVASNFAILAKAGISSVPDSAILGDIGVSPAAATYITGFGLTQDSSTTYATSPQVTGLIYAADYSTPTPNYLAAAVANAETAYNQAAGFVDPDFLELGAGELRDQTLVPGLYKWTSSVSVPTDLTFEGNGDATWVFQIAGGLSLADGVAFTLAGGANSTNIAFQVGDDVTVGKGAHFEGVLLAKRFVTLQTGSSLNGRVLSQTEVALQKATVNSPFVPAPEVVQKRSNARQWL` |

---

## 5. 性能对比

| 指标 | 基线值 | 最终值 | 变化 | 评价 |
|------|:------:|:------:|:----:|------|
| **TH (°C)** | 0.090 | 0.090 | +0.0% | 🟡 不变 |
| **IRI IC₅₀ (µM)** | 3.110 | 3.110 | +0.0% | 🟡 不变 |
| **表达评分** | 0.492 | 0.492 | +0.0% | 🟡 不变 |
| **稳定性评分** | 0.824 | 0.824 | +0.0% | 🟡 不变 |

---

## 7. 关键发现与设计规则

### 7.1 从本轮设计中发现的规则

> 本轮无设计数据。

---

## 8. 可视化

> ⚠️ 可视化图表未生成（可能缺少 matplotlib）。

---

*报告由 AFP-Designer 自动生成 | 2026-07-07 11:34:29*
*会话 ID: `20260707_112311_3b115c73` | 总轮次: 0 | 应用场景: general*
