"""
AFP突变评估工具 — 评估抗冻蛋白序列突变的可行性、风险和潜在收益
注册为: afp_evaluate_mutation
"""

from app.afp_agent.tools.registry import registry
from app.afp_agent.knowledge.knowledge_base import AFPKnowledgeBase

# 模块级知识库引用
_kb: AFPKnowledgeBase = None


def set_knowledge_base(kb: AFPKnowledgeBase):
    """注入知识库实例"""
    global _kb
    _kb = kb


# ---- 氨基酸属性表 ----

# 冰结合倾向评分 (正值有利，负值不利)
ICE_BINDING_AA = {
    'T': 1.0, 'N': 0.7, 'Q': 0.65, 'S': 0.5, 'A': 0.4,
    'V': 0.35, 'I': 0.35, 'L': 0.3, 'G': 0.2,
    'D': -0.5, 'E': -0.5, 'K': -0.6, 'R': -0.6,
    'F': -0.2, 'W': -0.3, 'Y': -0.1,
}

# 大体积残基 — 破坏冰结合面平坦性
BULKY_AA = {'F', 'W', 'Y', 'R', 'K'}

# H-键供体残基 — 冰结合关键
H_BOND_DONORS = {'T', 'N', 'Q', 'S', 'Y', 'H'}

# 带电荷残基（pH 7）
CHARGED_AA = {'D', 'E', 'K', 'R', 'H'}

# 疏水残基
HYDROPHOBIC_AA = {'A', 'V', 'I', 'L', 'M', 'F', 'W', 'Y', 'P'}


def evaluate_mutation_handler(args: dict) -> dict:
    """
    评估抗冻蛋白突变效果。

    参数:
        original_sequence: 原始氨基酸序列
        mutated_sequence: 突变后氨基酸序列
        mutations: 突变列表 [{"position": int, "from": str, "to": str}, ...]
        application_scenario: 应用场景
    """
    original = args.get("original_sequence", "").upper()
    mutated = args.get("mutated_sequence", "").upper()
    mutations = args.get("mutations", [])
    application_scenario = args.get("application_scenario", "general")

    if not original:
        return {"error": "请提供原始序列"}
    if not mutated and not mutations:
        return {"error": "请提供突变后序列或突变列表"}
    if not mutations:
        # 尝试从差异推导突变列表
        mutations = _derive_mutations(original, mutated)
    if not mutations:
        return {"error": "无法推导突变列表，请明确提供 mutations 参数"}

    # 确保 mutated 序列正确
    if not mutated:
        mutated = _apply_mutations(original, mutations)

    seq_len = len(original)

    # 获取知识库中的禁止突变区域
    forbidden_regions = _get_forbidden_regions(original)

    # 推测冰结合面位置（基于 T,N,Q 残基模式）
    ibs_positions = _detect_ibs(original)

    warnings = []
    rejections = []
    notes = []

    # ---- 逐项检查 ----

    for mut in mutations:
        pos = mut.get("position", -1)
        # position 可能是 0-indexed 或 1-indexed；这里假定 0-indexed（与 mutation_tool 一致）
        if pos < 0 or pos >= seq_len:
            rejections.append(f"位置 {pos} 超出序列范围 (0-{seq_len - 1})")
            continue

        from_aa = mut.get("from", original[pos] if pos < seq_len else "?").upper()
        to_aa = mut.get("to", "").upper()
        if to_aa not in "ACDEFGHIKLMNPQRSTVWY":
            rejections.append(f"无效的目标氨基酸: {to_aa}")
            continue

        pos_label = f"位置{pos}({from_aa}→{to_aa})"

        # 1. 检查是否命中禁止区域
        for region in forbidden_regions:
            start, end = region.get("start", -1), region.get("end", -1)
            if start <= pos <= end:
                reason = region.get("reason", "保守区域")
                warnings.append(f"❌ {pos_label} 位于禁止突变区域 [{start}-{end}]: {reason}")
                break

        # 2. 冰结合面大体积残基
        if pos in ibs_positions and to_aa in BULKY_AA:
            warnings.append(f"⚠️ {pos_label} 在冰结合面引入大体积残基 {to_aa}，破坏IBS平坦性")

        # 3. 冰结合面带电荷残基
        if pos in ibs_positions and to_aa in CHARGED_AA:
            if to_aa in ('D', 'E'):
                warnings.append(f"⚠️ {pos_label} 在IBS引入负电荷残基 {to_aa}，可能影响冰结合")
            else:
                rejections.append(f"🚫 {pos_label} 在IBS引入正电荷残基 {to_aa}，严重破坏冰结合")

        # 4. 移除关键 H-键供体
        if pos in ibs_positions and from_aa in H_BOND_DONORS and to_aa not in H_BOND_DONORS:
            warnings.append(f"⚠️ {pos_label} 移除关键H-键供体 {from_aa}")

        # 5. 二硫键破坏检查
        if from_aa == 'C':
            # 寻找配对的 Cys（简化：检查序列中 C 的总数是否偶数）
            c_count = original.count('C')
            if c_count >= 2 and c_count % 2 == 0:
                if original.count('C') > mutated.count('C'):
                    warnings.append(f"⚠️ {pos_label} 破坏潜在的Cys配对，影响蛋白骨架刚性")

        # 6. 引入有利残基
        if pos in ibs_positions and to_aa in ('T', 'N', 'Q'):
            notes.append(f"✅ {pos_label} 在IBS引入/保留H-键供体 {to_aa}")
        if to_aa == 'C' and original.count('C') + 1 >= 4 and (original.count('C') + 1) % 2 == 0:
            notes.append(f"💡 {pos_label} 引入Cys可能形成额外二硫键，增强骨架刚性")

    # ---- 整体理化性质评估 ----
    orig_charge = _net_charge(original)
    mut_charge = _net_charge(mutated)
    charge_delta = mut_charge - orig_charge
    if abs(charge_delta) > 2:
        warnings.append(f"⚠️ 净电荷变化较大 ({orig_charge:+.0f} → {mut_charge:+.0f})，可能影响溶解性")

    # 亲疏水区域检查
    orig_hydro = _hydrophobic_ratio(original)
    mut_hydro = _hydrophobic_ratio(mutated)
    if abs(mut_hydro - orig_hydro) > 0.1:
        notes.append(f"📝 疏水比例变化: {orig_hydro:.1%} → {mut_hydro:.1%}")

    # 冰结合评分变化
    orig_ibs_score = sum(ICE_BINDING_AA.get(original[p], 0) for p in ibs_positions if p < seq_len)
    mut_ibs_score = sum(ICE_BINDING_AA.get(mutated[p], 0) for p in ibs_positions if p < seq_len)
    ibs_delta = mut_ibs_score - orig_ibs_score
    if ibs_delta > 0.2:
        notes.append(f"📈 冰结合面评分提升: {orig_ibs_score:.2f} → {mut_ibs_score:.2f}")
    elif ibs_delta < -0.2:
        warnings.append(f"📉 冰结合面评分下降: {orig_ibs_score:.2f} → {mut_ibs_score:.2f}")

    # ---- 综合评判 ----
    if rejections:
        verdict = "REJECTED"
        verdict_reason = "存在严重突变问题，不建议进行"
    elif len([w for w in warnings if w.startswith("❌")]) > 0:
        verdict = "WARNING"
        verdict_reason = "突变命中禁止区域，风险较高"
    elif len(warnings) > 2:
        verdict = "WARNING"
        verdict_reason = "存在多项风险因素，需谨慎评估"
    elif len(warnings) > 0:
        verdict = "CAUTION"
        verdict_reason = "有轻微风险，但可能可接受"
    else:
        verdict = "PASS"
        verdict_reason = "突变初步评估通过，建议进一步实验验证"

    return {
        "original_sequence": original,
        "mutated_sequence": mutated,
        "sequence_length": seq_len,
        "mutation_count": len(mutations),
        "ibs_positions_detected": ibs_positions,
        "forbidden_regions": forbidden_regions,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "warnings": warnings,
        "rejections": rejections,
        "notes": notes,
        "charge_change": round(charge_delta, 1),
        "ibs_score_change": round(ibs_delta, 2),
        "application_scenario": application_scenario,
        "mutations": mutations,
    }


def _derive_mutations(original: str, mutated: str) -> list:
    """从两个序列的差异推导突变列表"""
    if len(original) != len(mutated):
        return []
    result = []
    for i, (o_aa, m_aa) in enumerate(zip(original, mutated)):
        if o_aa != m_aa:
            result.append({"position": i, "from": o_aa, "to": m_aa})
    return result


def _apply_mutations(original: str, mutations: list) -> str:
    """应用突变到序列"""
    seq = list(original)
    for mut in mutations:
        pos = mut.get("position", -1)
        to_aa = mut.get("to", "")
        if 0 <= pos < len(seq) and to_aa in "ACDEFGHIKLMNPQRSTVWY":
            seq[pos] = to_aa
    return "".join(seq)


def _detect_ibs(sequence: str) -> list:
    """检测可能的冰结合面位置（基于 T,N,Q 模式）"""
    positions = []
    for i, aa in enumerate(sequence):
        if aa in ('T', 'N', 'Q'):
            positions.append(i)
    # 如果太少，放宽条件
    if len(positions) < 3:
        positions = [i for i, aa in enumerate(sequence) if aa in ('T', 'N', 'Q', 'S', 'A')]
    return positions


def _get_forbidden_regions(sequence: str) -> list:
    """从知识库获取禁止突变区域"""
    if _kb is not None:
        try:
            analysis = _kb.analyze_sequence(sequence)
            return analysis.forbidden_regions
        except Exception:
            pass
    return []


def _net_charge(sequence: str) -> float:
    """计算净电荷 (pH 7)"""
    return (sequence.count('K') + sequence.count('R') + 0.5 * sequence.count('H')
            - sequence.count('D') - sequence.count('E'))


def _hydrophobic_ratio(sequence: str) -> float:
    """计算疏水残基比例"""
    return sum(1 for aa in sequence if aa in HYDROPHOBIC_AA) / len(sequence)


# 注册工具
registry.register(
    name="afp_evaluate_mutation",
    toolset="afp",
    schema={
        "type": "function",
        "function": {
            "name": "afp_evaluate_mutation",
            "description": (
                "评估抗冻蛋白序列突变的效果和风险。检查冰结合面完整性、"
                "二硫键破坏、溶解度变化、禁止区域命中情况，返回 PASS/CAUTION/WARNING/REJECTED 裁决。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "original_sequence": {
                        "type": "string",
                        "description": "原始抗冻蛋白氨基酸序列（单字母）",
                    },
                    "mutated_sequence": {
                        "type": "string",
                        "description": "突变后氨基酸序列（可选，不提供则从 mutations 推导）",
                    },
                    "mutations": {
                        "type": "array",
                        "description": "突变列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "position": {
                                    "type": "integer",
                                    "description": "突变位置（0-indexed）",
                                },
                                "from": {
                                    "type": "string",
                                    "description": "原始氨基酸",
                                },
                                "to": {
                                    "type": "string",
                                    "description": "目标氨基酸",
                                },
                            },
                            "required": ["position", "to"],
                        },
                    },
                    "application_scenario": {
                        "type": "string",
                        "enum": [
                            "ice_cream",
                            "frozen_dough",
                            "meat_preservation",
                            "cell_cryopreservation",
                            "organ_preservation",
                            "transgenic_crop",
                            "anti_ice_coating",
                            "general",
                        ],
                        "description": "应用场景",
                    },
                },
                "required": ["original_sequence"],
            },
        },
    },
    handler=lambda args, **kw: evaluate_mutation_handler(args),
    description="评估AFP突变的可行性、风险和收益",
    emoji="🔍",
)
