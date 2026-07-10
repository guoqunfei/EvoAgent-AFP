# knowledge/literature.py
"""
AFP 文献知识库
包含设计原则、突变效应数据库、应用场景权重
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class EvidenceStrength(Enum):
    STRONG_EXP = "Strong (experimental)"
    MODERATE_MD = "Moderate (MD simulation)"
    WEAK_INFERRED = "Weak (inferred)"


@dataclass
class MutationFinding:
    """突变发现记录"""
    source_protein: str
    mutation: str                  # 如 "G63S"
    position: int
    from_aa: str
    to_aa: str
    th_change_pct: float           # TH活性变化百分比
    iri_change_pct: float          # IRI活性变化百分比
    stability_change: str          # "Increased" / "Decreased" / "Unchanged"
    mechanism: str                 # 机理解释
    relevance_score: float         # 0-1，对设计的参考价值
    pmid: str


@dataclass
class DesignPrinciple:
    """设计原则"""
    principle_id: str
    category: str                  # "ice_binding" / "stability" / "expression" / "safety"
    title: str
    rule: str                      # 可操作的设计规则
    evidence_strength: str
    applicable_afp_types: List[str]
    counter_examples: List[str] = field(default_factory=list)
    pmid_list: List[str] = field(default_factory=list)


# ============================================
# 突变效应数据库
# ============================================
MUTATION_FINDINGS: List[MutationFinding] = [
    MutationFinding(
        source_protein="MaIBP_RIV (Marinomonas)",
        mutation="G63S", position=63, from_aa="G", to_aa="S",
        th_change_pct=40, iri_change_pct=15,
        stability_change="Unchanged",
        mechanism="Ser羟基恢复局部H-bond网络，增强冰结合",
        relevance_score=0.90,
        pmid="41197692"
    ),
    MutationFinding(
        source_protein="MaIBP_RIV (Marinomonas)",
        mutation="G63D", position=63, from_aa="G", to_aa="D",
        th_change_pct=-100, iri_change_pct=-100,
        stability_change="Unchanged",
        mechanism="Asp负电荷排斥冰面，完全丧失冰结合",
        relevance_score=0.95,
        pmid="41197692"
    ),
    MutationFinding(
        source_protein="MaIBP_RIV (Marinomonas)",
        mutation="G63E", position=63, from_aa="G", to_aa="E",
        th_change_pct=-95, iri_change_pct=-90,
        stability_change="Unchanged",
        mechanism="Glu负电荷排斥冰面",
        relevance_score=0.90,
        pmid="41197692"
    ),
    MutationFinding(
        source_protein="MaIBP_RIV (Marinomonas)",
        mutation="G63K", position=63, from_aa="G", to_aa="K",
        th_change_pct=-90, iri_change_pct=-85,
        stability_change="Unchanged",
        mechanism="Lys正电荷+大体积破坏IBS",
        relevance_score=0.85,
        pmid="41197692"
    ),
    MutationFinding(
        source_protein="雪蚤 AFP (sfAFP)",
        mutation="T16G/A19G/S22G", position=16, from_aa="T/A/S", to_aa="G/G/G",
        th_change_pct=128, iri_change_pct=20,
        stability_change="Unchanged",
        mechanism="三重Gly突变优化二聚化冰结合面",
        relevance_score=0.85,
        pmid="2025_rational_design_SfAFP"
    ),
    MutationFinding(
        source_protein="Type III QAE",
        mutation="Q44T/N14S/T18N", position=44, from_aa="Q/N/T", to_aa="T/S/N",
        th_change_pct=-100, iri_change_pct=-100,
        stability_change="Unchanged",
        mechanism="三重突变破坏冰结合面氢键网络——即使保持天然折叠",
        relevance_score=0.95,
        pmid="10346894"
    ),
    MutationFinding(
        source_protein="Type III QAE",
        mutation="A16L", position=16, from_aa="A", to_aa="L",
        th_change_pct=-30, iri_change_pct=-25,
        stability_change="Unchanged",
        mechanism="Leu大体积侧链破坏IBS平坦性",
        relevance_score=0.90,
        pmid="8639620"
    ),
    MutationFinding(
        source_protein="Type I HPLC6",
        mutation="T2S", position=2, from_aa="T", to_aa="S",
        th_change_pct=-80, iri_change_pct=-10,
        stability_change="Unchanged",
        mechanism="Ser羟基间距不匹配(4.5→4.0Å)，破坏冰晶格匹配",
        relevance_score=0.95,
        pmid="7638597"
    ),
    MutationFinding(
        source_protein="云杉蚜虫 AFP",
        mutation="非IBS环插入", position=0, from_aa="", to_aa="",
        th_change_pct=0, iri_change_pct=0,
        stability_change="Unchanged",
        mechanism="非IBS区域高度耐受插入——表达量+15%",
        relevance_score=0.80,
        pmid="14526017"
    ),
    MutationFinding(
        source_protein="BtAFP (明胶源)",
        mutation="α-螺旋截短", position=0, from_aa="", to_aa="",
        th_change_pct=0, iri_change_pct=21.75,
        stability_change="Increased",
        mechanism="去除非活性区域，浓缩活性基序",
        relevance_score=0.75,
        pmid="2024_Engineering_AVD"
    ),
    MutationFinding(
        source_protein="De novo a-iTHR-201",
        mutation="T→E (IBS空间敲除)", position=1, from_aa="T", to_aa="E",
        th_change_pct=0, iri_change_pct=-65,
        stability_change="Unchanged",
        mechanism="空间敲除Thr→Glu降低但不消除IRI——证明几何互补可独立驱动活性",
        relevance_score=0.90,
        pmid="2025_bioRxiv_de_novo_iTHR"
    ),
    MutationFinding(
        source_protein="De novo a-iTHR-201",
        mutation="A→E (IBS空间敲除)", position=8, from_aa="A", to_aa="E",
        th_change_pct=0, iri_change_pct=-60,
        stability_change="Unchanged",
        mechanism="Ala→Glu空间敲除同样降低但不消除IRI",
        relevance_score=0.88,
        pmid="2025_bioRxiv_de_novo_iTHR"
    ),
]


# ============================================
# 设计原则库
# ============================================
DESIGN_PRINCIPLES: Dict[str, DesignPrinciple] = {
    "DP-001": DesignPrinciple(
        principle_id="DP-001",
        category="ice_binding",
        title="IBS Thr间距必须匹配靶向冰面",
        rule="Thr残基在IBS上的间距必须为4.5Å（棱面）、7.4Å（基面）或16.5Å（金字塔面），偏差>10%将显著降低活性",
        evidence_strength="Strong (experimental)",
        applicable_afp_types=["Type I", "Type III", "Insect hyperactive", "De novo"],
        counter_examples=["MaIBP_RIV的Thr-free IBS通过Gly/Ser的局部构象灵活性实现冰结合"],
        pmid_list=["7638597", "10655467", "41197692"]
    ),
    "DP-002": DesignPrinciple(
        principle_id="DP-002",
        category="ice_binding",
        title="IBS必须保持平坦（RMSD < 1 Å）",
        rule="冰结合面的Cα原子波动不应超过1Å。引入大体积残基(Phe/Trp/Tyr)或带电残基(Lys/Arg/Asp/Glu)到IBS将破坏平面性并丧失活性",
        evidence_strength="Strong (experimental)",
        applicable_afp_types=["Type I", "Type II", "Type III", "Insect hyperactive", "Bacterial", "De novo"],
        counter_examples=["Type II AFP的IBS具有略微弯曲的表面"],
        pmid_list=["10346894", "8639620"]
    ),
    "DP-003": DesignPrinciple(
        principle_id="DP-003",
        category="stability",
        title="二硫键对超活性AFP的支架刚性化至关重要",
        rule="昆虫和细菌超活性AFP中，破坏任意>Cys二硫键将导致β-螺旋展开并完全丧失TH活性。但IRI活性可能部分保留",
        evidence_strength="Strong (experimental)",
        applicable_afp_types=["Insect hyperactive", "Bacterial"],
        counter_examples=["Type I/III AFP无二硫键但仍保持活性"],
        pmid_list=["14526017"]
    ),
    "DP-004": DesignPrinciple(
        principle_id="DP-004",
        category="ice_binding",
        title="几何互补性可独立驱动显著的IRI活性",
        rule="即使没有完美的氢键匹配，仅凭IBS与冰面的几何形状互补就足以产生可测量的IRI活性。这对de novo设计尤其重要",
        evidence_strength="Moderate (MD + experiment)",
        applicable_afp_types=["Type I", "De novo"],
        counter_examples=["TH活性需要额外的水合层匹配，仅几何互补不足以产生TH"],
        pmid_list=["2025_bioRxiv_de_novo_iTHR"]
    ),
    "DP-005": DesignPrinciple(
        principle_id="DP-005",
        category="expression",
        title="融合标签可显著改善AFP表达量",
        rule="MBP和GST标签可将AFP表达量提高2-10倍。TAT细胞穿透肽融合可实现细胞内冰保护。标签必须放置在非IBS端以避免干扰冰结合",
        evidence_strength="Strong (experimental)",
        applicable_afp_types=["Type I", "Type II", "Type III", "Insect hyperactive", "Bacterial", "De novo"],
        counter_examples=["部分标签可能干扰冰结合面——需放置在非IBS端"],
        pmid_list=["2025_rational_design_SfAFP"]
    ),
    "DP-006": DesignPrinciple(
        principle_id="DP-006",
        category="ice_binding",
        title="Glu(E)是比Thr(T)更强的冰结合残基",
        rule="JACS 2025研究：Glu(E)的结合能是Thr(T)的4倍以上。在de novo设计中，优先使用Glu作为冰结合残基，并精确控制间距匹配冰晶格",
        evidence_strength="Strong (experimental, 2025)",
        applicable_afp_types=["De novo"],
        counter_examples=["天然AFP几乎不依赖Glu——长期进化选择了Thr"],
        pmid_list=["40358480"]
    ),
    "DP-007": DesignPrinciple(
        principle_id="DP-007",
        category="ice_binding",
        title="IBS残基类型影响冰结合强度",
        rule="冰结合残基优先级：Glu(E) > Thr(T) > Asn(N) > Gln(Q) > Ser(S) > Ala(A) > Gly(G)。带电残基(D/K/R)应严格避免在IBS上出现",
        evidence_strength="Moderate (multiple experimental studies)",
        applicable_afp_types=["Type I", "Type II", "Type III", "Insect hyperactive", "De novo"],
        counter_examples=["MaIBP_RIV的Gly-only IBS通过构象灵活性实现功能"],
        pmid_list=["40358480", "41197692", "2025_bioRxiv_de_novo_iTHR"]
    ),
    "DP-008": DesignPrinciple(
        principle_id="DP-008",
        category="stability",
        title="盐桥对α-螺旋型AFP的折叠至关重要",
        rule="Type I AFP中的Lys-Asp/Glu盐桥提供了α-螺旋的帽化稳定。突变这些盐桥残基将降低Tm并间接损害TH活性",
        evidence_strength="Strong (experimental)",
        applicable_afp_types=["Type I"],
        counter_examples=["非α-螺旋型AFP不依赖盐桥稳定化"],
        pmid_list=["7638597", "10545318"]
    ),
    "DP-009": DesignPrinciple(
        principle_id="DP-009",
        category="ice_binding",
        title="非IBS面残基对活性影响极小",
        rule="de novo iTHR实验证明——非IBS面的Ala→Glu敲除仅降低IRI约3倍而非完全丧失。非IBS面可用于优化表达量/溶解度/稳定性而不影响冰结合",
        evidence_strength="Moderate (MD + experiment, 2025)",
        applicable_afp_types=["Type I", "Type III", "De novo"],
        counter_examples=["昆虫AFP的非IBS面修饰可能影响β-螺旋折叠"],
        pmid_list=["2025_bioRxiv_de_novo_iTHR"]
    ),
    "DP-010": DesignPrinciple(
        principle_id="DP-010",
        category="expression",
        title="Ala含量与α-螺旋AFP表达正相关",
        rule="Type I AFP中Ala含量>50%有助于α-螺旋稳定性和表达产量。在保持IBS Thr的前提下，可适度增加Ala含量以改善表达",
        evidence_strength="Moderate (sequence analysis)",
        applicable_afp_types=["Type I", "De novo"],
        counter_examples=["过高Ala含量(>65%)可能导致不可溶聚集"],
        pmid_list=["7638597"]
    ),
}


# ============================================
# 应用场景权重
# ============================================
APPLICATION_SCENARIOS = {
    "ice_cream": {
        "name": "冰淇淋/冷冻甜品",
        "th_weight": 0.15,
        "iri_weight": 0.50,
        "expression_weight": 0.25,
        "stability_weight": 0.05,
        "safety_weight": 0.05,
        "description": "IRI优先——抑制冰重结晶保持丝滑口感"
    },
    "frozen_dough": {
        "name": "冷冻面团",
        "th_weight": 0.10,
        "iri_weight": 0.45,
        "expression_weight": 0.20,
        "stability_weight": 0.15,
        "safety_weight": 0.10,
        "description": "IRI+稳定性优先——长保质期的冷冻面团"
    },
    "meat_preservation": {
        "name": "肉类冻存",
        "th_weight": 0.15,
        "iri_weight": 0.40,
        "expression_weight": 0.20,
        "stability_weight": 0.15,
        "safety_weight": 0.10,
        "description": "IRI优先——保护肌肉纤维完整性"
    },
    "cell_cryopreservation": {
        "name": "细胞冻存",
        "th_weight": 0.35,
        "iri_weight": 0.25,
        "expression_weight": 0.10,
        "stability_weight": 0.10,
        "safety_weight": 0.20,
        "description": "TH+安全性优先——降低冰点+减少DMSO用量"
    },
    "organ_preservation": {
        "name": "器官保存",
        "th_weight": 0.40,
        "iri_weight": 0.30,
        "expression_weight": 0.05,
        "stability_weight": 0.10,
        "safety_weight": 0.15,
        "description": "TH+IRI双高——延长器官离体存活时间"
    },
    "transgenic_crop": {
        "name": "抗冻转基因作物",
        "th_weight": 0.20,
        "iri_weight": 0.40,
        "expression_weight": 0.30,
        "stability_weight": 0.05,
        "safety_weight": 0.05,
        "description": "表达量+IRI优先——植物体内功能表达"
    },
    "anti_ice_coating": {
        "name": "防冰涂层",
        "th_weight": 0.30,
        "iri_weight": 0.20,
        "expression_weight": 0.15,
        "stability_weight": 0.30,
        "safety_weight": 0.05,
        "description": "TH+稳定性优先——长期耐用防冰表面"
    },
    "de_novo_optimization": {
        "name": "De Novo活性优化",
        "th_weight": 0.40,
        "iri_weight": 0.35,
        "expression_weight": 0.10,
        "stability_weight": 0.10,
        "safety_weight": 0.05,
        "description": "TH+IRI双优化——最大化抗冻活性"
    },
}


class AFPLiteratureKnowledge:
    """AFP文献知识库"""

    def __init__(self):
        self.findings = MUTATION_FINDINGS
        self.principles = DESIGN_PRINCIPLES
        self.scenarios = APPLICATION_SCENARIOS

    def get_mutations_by_protein(self, protein_name: str) -> List[MutationFinding]:
        """按蛋白名称查询突变"""
        return [f for f in self.findings if protein_name.lower() in f.source_protein.lower()]

    def get_mutations_by_residue(self, aa: str) -> List[MutationFinding]:
        """查询涉及特定残基的突变"""
        return [f for f in self.findings if f.from_aa == aa or f.to_aa == aa]

    def get_beneficial_mutations(self) -> List[MutationFinding]:
        """获取所有有益突变"""
        return [f for f in self.findings if f.th_change_pct > 0 or f.iri_change_pct > 0]

    def get_destructive_mutations(self) -> List[MutationFinding]:
        """获取所有破坏性突变"""
        return [f for f in self.findings if f.th_change_pct <= -80 or f.iri_change_pct <= -80]

    def get_principles_by_category(self, category: str) -> List[DesignPrinciple]:
        """按类别获取设计原则"""
        return [p for p in self.principles.values() if p.category == category]

    def get_all_principles(self) -> List[DesignPrinciple]:
        """获取所有设计原则"""
        return list(self.principles.values())

    def get_scenario_weights(self, scenario: str) -> Optional[Dict]:
        """获取应用场景权重"""
        return self.scenarios.get(scenario)

    def get_summary_for_llm(self) -> str:
        """生成给LLM的知识库摘要"""
        lines = ["## AFP文献知识库摘要\n"]

        lines.append("### 关键突变发现")
        for f in self.findings[:8]:
            lines.append(f"- **{f.source_protein}** {f.mutation}: "
                        f"TH {f.th_change_pct:+d}% / IRI {f.iri_change_pct:+d}% — {f.mechanism[:80]}")

        lines.append("\n### 核心设计原则")
        for pid, p in list(self.principles.items())[:8]:
            lines.append(f"- **{p.title}**: {p.rule[:100]}")

        lines.append("\n### 应用场景权重")
        for sid, s in self.scenarios.items():
            lines.append(f"- **{s['name']}**: TH={s['th_weight']} IRI={s['iri_weight']} "
                        f"表达={s['expression_weight']} 稳定性={s['stability_weight']}")

        return "\n".join(lines)

    def find_relevant_knowledge(self, query: str) -> str:
        """基于查询字符串搜索相关知识"""
        query_lower = query.lower()
        relevant = []

        # 搜索设计原则
        for pid, p in self.principles.items():
            if (query_lower in p.title.lower() or
                query_lower in p.rule.lower() or
                query_lower in p.category.lower()):
                relevant.append(f"**{p.title}** [{p.evidence_strength}]: {p.rule}")

        # 搜索突变发现
        for f in self.findings:
            if (query_lower in f.source_protein.lower() or
                query_lower in f.mutation.lower() or
                query_lower in f.mechanism.lower()):
                relevant.append(f"**{f.source_protein} {f.mutation}**: "
                              f"TH {f.th_change_pct:+d}%, IRI {f.iri_change_pct:+d}% — {f.mechanism}")

        return "\n".join(relevant[:10]) if relevant else "未找到与查询直接相关的知识条目。"
