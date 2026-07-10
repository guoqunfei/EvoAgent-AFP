# simulator/geometry_scorer.py
"""
冰结合几何评分引擎
评估AFP序列与冰晶格的几何互补性 —— 毫秒级
"""

import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class IcePlane(Enum):
    BASAL = "Basal plane {0001}"
    PRISM = "Prism plane {10-10}"
    PYRAMIDAL_201 = "Pyramidal plane {20-21}"
    PYRAMIDAL_110 = "Pyramidal plane {11-20}"


# 冰晶格常数
ICE_LATTICE = {
    IcePlane.BASAL: {
        "o_spacing": 7.35,        # 氧原子间距 (Å)
        "o_pattern": "hexagonal",
        "unit_cell_a": 4.52,
        "unit_cell_c": 7.35,
        "description": "基面{0001}——昆虫超活性AFP的主要靶面"
    },
    IcePlane.PRISM: {
        "o_spacing": 4.52,
        "o_pattern": "rectangular",
        "unit_cell_a": 4.52,
        "unit_cell_c": 7.35,
        "description": "棱面{10-10}——Type III AFP的主要靶面"
    },
    IcePlane.PYRAMIDAL_201: {
        "o_spacing": 16.5,
        "o_pattern": "staggered",
        "unit_cell_a": 4.52,
        "unit_cell_c": 7.35,
        "description": "金字塔面{20-21}——Type I AFP的主要靶面"
    },
    IcePlane.PYRAMIDAL_110: {
        "o_spacing": 7.85,
        "o_pattern": "rectangular",
        "unit_cell_a": 4.52,
        "unit_cell_c": 7.35,
        "description": "金字塔面{11-20}"
    }
}

# 氨基酸对冰结合的贡献评分（经验值）
AA_ICE_BINDING_SCORE = {
    'T': 1.00,   # Thr: 完美羟基+甲基组合
    'N': 0.70,   # Asn: 酰胺侧链H-bond
    'Q': 0.65,   # Gln: 较长侧链
    'S': 0.50,   # Ser: 羟基但间距较Thr短
    'A': 0.40,   # Ala: 甲基疏水互补
    'V': 0.35,   # Val: 中等疏水
    'I': 0.35,   # Ile: 疏水
    'L': 0.30,   # Leu: 疏水
    'M': 0.25,   # Met: 弱疏水
    'G': 0.20,   # Gly: 无侧链，构象灵活性
    'P': 0.05,   # Pro: 限制骨架
    'C': 0.10,   # Cys: 二硫键
    'Y': -0.10,  # Tyr: 大体积
    'F': -0.20,  # Phe: 大体积芳香环
    'W': -0.30,  # Trp: 最大侧链
    'H': -0.15,  # His: pH依赖
    'D': -0.50,  # Asp: 负电荷
    'E': -0.50,  # Glu: 负电荷（但2025 JACS发现Glu结合能是Thr的4倍！）
    'K': -0.60,  # Lys: 正电荷+大体积
    'R': -0.60,  # Arg: 正电荷+大体积
}

# 注：2025年JACS研究发现Glu(E)的结合能是Thr的4倍，因此de novo设计时E评分调整
AA_ICE_BINDING_SCORE_DE_NOVO = {
    **AA_ICE_BINDING_SCORE,
    'E': 0.80,  # de novo设计中Glu是超级冰结合残基
}


@dataclass
class GeometryScore:
    """几何评分结果"""
    spacing_match_score: float        # 间距匹配评分 (0-1)
    residue_quality_score: float      # 残基类型质量评分 (0-1)
    flatness_prediction: float        # 预测IBS平坦性 (0-1)
    overall_geometry_score: float     # 综合几何评分 (0-1)
    estimated_iri_activity: float     # 预测IRI IC₅₀ (µM)
    estimated_th_activity: float      # 预测TH (°C)
    target_ice_plane: str

    def to_dict(self) -> dict:
        return {
            "spacing_match_score": self.spacing_match_score,
            "residue_quality_score": self.residue_quality_score,
            "flatness_prediction": self.flatness_prediction,
            "overall_geometry_score": self.overall_geometry_score,
            "estimated_iri_activity_uM": self.estimated_iri_activity,
            "estimated_th_activity_C": self.estimated_th_activity,
            "target_ice_plane": self.target_ice_plane,
            "activity_assessment": self._assess_activity()
        }

    def _assess_activity(self) -> str:
        if self.overall_geometry_score > 0.8:
            return "超活性级别潜力（昆虫级别）—— 预期TH 3-7°C"
        elif self.overall_geometry_score > 0.6:
            return "中等活性（鱼源AFP级别）—— 预期TH 0.5-1.5°C"
        elif self.overall_geometry_score > 0.4:
            return "低但可测量的IRI活性—— 适合食品冷冻应用"
        else:
            return "可能无活性—— 建议重新设计IBS"


class IceBindingGeometryScorer:
    """
    冰结合几何评分引擎

    核心原理：
    1. 基于已知/预测的IBS残基位置
    2. 计算残基间距与冰晶格氧原子间距的匹配度
    3. 评估IBS残基侧链类型对冰结合的贡献
    4. 综合评分 → 冰结合潜力预测

    计算复杂度: O(n²) for n ≤ 100 residues → 毫秒级
    """

    def __init__(self, is_de_novo: bool = False):
        self.is_de_novo = is_de_novo
        self.aa_scores = AA_ICE_BINDING_SCORE_DE_NOVO if is_de_novo else AA_ICE_BINDING_SCORE

    def score_ice_binding(
        self,
        sequence: str,
        ibs_positions: List[int],
        target_plane: IcePlane = IcePlane.PRISM
    ) -> GeometryScore:
        """
        计算序列的冰结合几何评分

        Args:
            sequence: AFP氨基酸序列
            ibs_positions: 推测的冰结合面残基位置（1-based）
            target_plane: 靶向冰晶面
        """
        # 过滤有效位置
        valid_positions = [p for p in ibs_positions if 1 <= p <= len(sequence)]
        if not valid_positions:
            return GeometryScore(0.2, 0.2, 0.5, 0.3, 20.0, 0.0, target_plane.value)

        # 提取IBS残基
        ibs_residues = [sequence[p-1] for p in valid_positions]

        # 1. 间距匹配评分
        lattice_spacing = ICE_LATTICE[target_plane]["o_spacing"]
        spacing_score = self._calculate_spacing_match(valid_positions, lattice_spacing)

        # 2. 残基质量评分
        residue_score = self._calculate_residue_quality(ibs_residues)

        # 3. 平坦性预测
        flatness_score = self._predict_flatness(ibs_residues)

        # 4. 综合几何评分
        overall = 0.4 * spacing_score + 0.35 * residue_score + 0.25 * flatness_score

        # 5. IRI活性估计
        est_iri = self._estimate_iri_activity(overall, len(valid_positions))

        # 6. TH活性估计
        est_th = self._estimate_th_activity(overall, len(valid_positions),
                                             self._has_rigid_scaffold(sequence))

        return GeometryScore(
            spacing_match_score=round(spacing_score, 3),
            residue_quality_score=round(residue_score, 3),
            flatness_prediction=round(flatness_score, 3),
            overall_geometry_score=round(overall, 3),
            estimated_iri_activity=round(est_iri, 2),
            estimated_th_activity=round(est_th, 2),
            target_ice_plane=target_plane.value
        )

    def score_all_planes(self, sequence: str, ibs_positions: List[int]) -> Dict[IcePlane, GeometryScore]:
        """对所有冰面进行评分，找出最佳靶面"""
        scores = {}
        for plane in IcePlane:
            scores[plane] = self.score_ice_binding(sequence, ibs_positions, plane)
        return scores

    def find_best_plane(self, sequence: str, ibs_positions: List[int]) -> Tuple[IcePlane, GeometryScore]:
        """找到最佳匹配冰面"""
        scores = self.score_all_planes(sequence, ibs_positions)
        best = max(scores.items(), key=lambda x: x[1].overall_geometry_score)
        return best

    def _calculate_spacing_match(self, positions: List[int], target_spacing: float) -> float:
        """计算IBS残基间距与冰晶格的匹配度"""
        if len(positions) < 2:
            return 0.3

        matches = 0
        total_pairs = 0

        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                # 近似: 1残基≈3.5Å
                dist = abs(positions[j] - positions[i]) * 3.5
                # 检查是否接近冰晶格间距的整数倍（容差25%）
                for n in range(1, 6):
                    expected = n * target_spacing
                    if abs(dist - expected) / expected < 0.25:
                        matches += 1
                        break
                total_pairs += 1

        return matches / max(total_pairs, 1)

    def _calculate_residue_quality(self, ibs_residues: List[str]) -> float:
        """基于IBS残基类型计算质量评分"""
        if not ibs_residues:
            return 0.0

        scores = [self.aa_scores.get(aa, 0.0) for aa in ibs_residues]
        positive_count = sum(1 for s in scores if s > 0.2)
        avg_score = sum(scores) / len(scores)

        return 0.6 * max(avg_score, 0.0) + 0.4 * (positive_count / len(scores))

    def _predict_flatness(self, ibs_residues: List[str]) -> float:
        """基于残基类型预测IBS平坦性"""
        if not ibs_residues:
            return 0.5

        bulky_residues = {'F', 'W', 'Y', 'R', 'K', 'E', 'Q', 'M'}
        small_residues = {'A', 'G', 'S', 'T', 'V'}

        bulky_count = sum(1 for aa in ibs_residues if aa in bulky_residues)
        small_count = sum(1 for aa in ibs_residues if aa in small_residues)

        flatness = 1.0 - (bulky_count / len(ibs_residues)) * 0.8
        flatness += (small_count / len(ibs_residues)) * 0.2

        return max(0.0, min(1.0, flatness))

    def _has_rigid_scaffold(self, sequence: str) -> bool:
        """检测刚性化结构特征"""
        cys_count = sequence.count('C')
        return cys_count >= 4 and cys_count % 2 == 0

    def _estimate_iri_activity(self, geometry_score: float, n_ibs_residues: int) -> float:
        """
        IRI活性估计（经验模型）

        基于2025年de novo iTHR数据：
        - a-iTHR-201: geometry≈0.55, n_ibs=4, IRI Cᵢ=0.97 µM
        - wfAFP HPLC6: geometry≈0.65, n_ibs=4, IRI Cᵢ=4.6 µM
        - TmAFP: geometry≈0.95, n_ibs=48, IRI Cᵢ=0.5 µM
        """
        base = 50.0 * math.exp(-3.5 * geometry_score)
        n_factor = math.exp(-0.05 * n_ibs_residues)
        return max(0.1, base * n_factor)

    def _estimate_th_activity(self, geometry_score: float, n_ibs_residues: int,
                               rigid_scaffold: bool) -> float:
        """TH活性估计（经验模型）"""
        if geometry_score < 0.5:
            return 0.0

        base_th = 0.1

        if n_ibs_residues <= 6:
            n_factor = 1.0
        elif n_ibs_residues <= 20:
            n_factor = 3.0
        else:
            n_factor = 10.0

        rigid_factor = 3.0 if rigid_scaffold else 1.0

        return min(7.0, base_th * n_factor * rigid_factor)


def score_sequence_quick(sequence: str, ibs_positions: Optional[List[int]] = None) -> dict:
    """
    快速评分接口 —— 自动推断IBS并评分所有冰面
    用于工具调用中快速获取几何评分
    """
    from knowledge.seq_analyzer import AFPSeqAnalyzer

    scorer = IceBindingGeometryScorer()

    # 如果没有提供IBS，自动推断
    if ibs_positions is None:
        analyzer = AFPSeqAnalyzer()
        analysis = analyzer.analyze(sequence, "ibs_only")
        ibs_positions = analysis.predicted_ibs_positions

    if not ibs_positions:
        # 基于Thr位置推断
        ibs_positions = [i+1 for i, aa in enumerate(sequence) if aa in 'TNQS']

    if not ibs_positions:
        return {"error": "无法识别IBS残基"}

    # 对所有冰面评分
    all_scores = {}
    best_plane = None
    best_score = None

    for plane in IcePlane:
        gs = scorer.score_ice_binding(sequence, ibs_positions, plane)
        score_dict = gs.to_dict()
        all_scores[plane.value] = score_dict
        if best_score is None or gs.overall_geometry_score > best_score.overall_geometry_score:
            best_score = gs
            best_plane = plane

    return {
        "sequence_length": len(sequence),
        "ibs_positions_used": ibs_positions,
        "all_plane_scores": all_scores,
        "best_plane": best_plane.value if best_plane else "Unknown",
        "best_score": best_score.to_dict() if best_score else None,
    }
