# simulator/simulator.py
"""
AFP 模拟器集成接口
统一的序列→性能预测管道
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from .geometry_scorer import (
    IceBindingGeometryScorer, GeometryScore, IcePlane,
    score_sequence_quick
)
from .physicochemical_scorer import PhysicochemicalScorer, PhysicochemicalProfile
from .afp_predictor import SimpleAFPPredictor


@dataclass
class SimulationResult:
    """综合模拟结果"""
    sequence: str
    sequence_length: int

    # 几何评分
    geometry_score: Optional[GeometryScore] = None

    # AFP概率
    afp_probability: float = 0.0

    # 活性预测
    estimated_th: float = 0.0           # °C
    estimated_iri_ic50: float = 0.0     # µM

    # 表达和稳定性
    stability_score: float = 0.0
    expression_score: float = 0.0
    yeast_yield_mg_L: float = 0.0

    # 物理化学
    physchem_profile: Optional[Dict] = None

    # 对比结果（如果有原始序列）
    comparison: Optional[Dict] = None

    def to_dict(self) -> dict:
        return {
            "sequence": self.sequence,
            "sequence_length": self.sequence_length,
            "afp_probability": self.afp_probability,
            "estimated_TH_C": self.estimated_th,
            "estimated_IRI_IC50_uM": self.estimated_iri_ic50,
            "stability_score": self.stability_score,
            "expression_score": self.expression_score,
            "yeast_yield_mg_L": self.yeast_yield_mg_L,
            "geometry_score": self.geometry_score.to_dict() if self.geometry_score else None,
            "physchem_profile": self.physchem_profile,
            "comparison": self.comparison,
            "overall_assessment": self._overall_assessment()
        }

    def _overall_assessment(self) -> str:
        if self.afp_probability > 0.8:
            if self.estimated_th > 2.0:
                return "EXCELLENT: 高概率AFP，超活性潜力"
            elif self.estimated_th > 0.5:
                return "GOOD: 高概率AFP，中等活性"
            else:
                return "FAIR: 高概率AFP但活性偏低——可能适合IRI应用"
        elif self.afp_probability > 0.5:
            return "MODERATE: 可能为AFP，需进一步优化"
        elif self.afp_probability > 0.2:
            return "LOW: 低AFP概率——需要显著序列改造"
        else:
            return "POOR: 不太可能是AFP——建议更换设计骨架"


class AFPSimulator:
    """AFP 模拟器集成接口"""

    def __init__(self):
        self.geo_scorer = IceBindingGeometryScorer()
        self.physchem_scorer = PhysicochemicalScorer()
        self.afp_predictor = SimpleAFPPredictor()

    def simulate(self,
                 sequence: str,
                 ibs_positions: Optional[List[int]] = None,
                 target_plane: IcePlane = IcePlane.PRISM,
                 original_sequence: Optional[str] = None,
                 original_ibs_positions: Optional[List[int]] = None,
                 ) -> SimulationResult:
        """
        综合模拟接口

        Args:
            sequence: AFP序列
            ibs_positions: 已知/预测的IBS残基位置
            target_plane: 靶向冰面
            original_sequence: 原始序列（用于对比）
            original_ibs_positions: 原始序列的IBS位置

        Returns:
            SimulationResult 包含所有预测结果
        """
        seq = sequence.upper().strip()

        # 自动推断IBS
        if ibs_positions is None:
            ibs_positions = self._auto_detect_ibs(seq)

        # Layer 1: 几何评分
        geo_score = self.geo_scorer.score_ice_binding(seq, ibs_positions, target_plane)

        # Layer 2: 物理化学评分
        profile = self.physchem_scorer.compute_profile(seq)
        profile_dict = self.physchem_scorer.to_dict(profile)

        # 简化ML预测
        afp_prob = self.afp_predictor.predict_afp_probability(seq)
        yeast_yield = self.afp_predictor.predict_expression_pastoris(seq)

        result = SimulationResult(
            sequence=seq,
            sequence_length=len(seq),
            geometry_score=geo_score,
            afp_probability=afp_prob,
            estimated_th=geo_score.estimated_th_activity,
            estimated_iri_ic50=geo_score.estimated_iri_activity,
            stability_score=profile.predicted_thermal_stability,
            expression_score=profile.predicted_expression_score,
            yeast_yield_mg_L=yeast_yield,
            physchem_profile=profile_dict,
        )

        # 如果有原始序列，生成对比
        if original_sequence:
            result.comparison = self.compare(original_sequence, sequence,
                                              original_ibs_positions, ibs_positions,
                                              target_plane)

        return result

    def compare(self,
                original_seq: str,
                mutated_seq: str,
                orig_ibs: Optional[List[int]] = None,
                mut_ibs: Optional[List[int]] = None,
                target_plane: IcePlane = IcePlane.PRISM
                ) -> Dict:
        """对比原始和突变序列的性能变化"""
        orig_result = self.simulate(original_seq, orig_ibs, target_plane)
        mut_result = self.simulate(mutated_seq, mut_ibs, target_plane)

        th_change = self._pct_change(orig_result.estimated_th, mut_result.estimated_th)
        iri_change = self._pct_change(orig_result.estimated_iri_ic50,
                                       mut_result.estimated_iri_ic50)

        # IRI变化是反向的（越低越好）
        iri_improvement = -iri_change

        return {
            "original": {
                "th_C": orig_result.estimated_th,
                "iri_IC50_uM": orig_result.estimated_iri_ic50,
                "afp_probability": orig_result.afp_probability,
                "stability": orig_result.stability_score,
                "expression": orig_result.expression_score,
            },
            "mutated": {
                "th_C": mut_result.estimated_th,
                "iri_IC50_uM": mut_result.estimated_iri_ic50,
                "afp_probability": mut_result.afp_probability,
                "stability": mut_result.stability_score,
                "expression": mut_result.expression_score,
            },
            "changes": {
                "th_change_pct": th_change,
                "iri_change_pct": iri_change,
                "iri_improvement_pct": iri_improvement,  # 正值=IRI改善
                "afp_probability_change": round(mut_result.afp_probability -
                                                orig_result.afp_probability, 4),
                "stability_change": round(mut_result.stability_score -
                                         orig_result.stability_score, 3),
                "expression_change": round(mut_result.expression_score -
                                          orig_result.expression_score, 3),
            },
            "verdict": self._comparison_verdict(orig_result, mut_result),
        }

    def _auto_detect_ibs(self, sequence: str) -> List[int]:
        """自动检测可能的IBS残基"""
        positions = []
        for i, aa in enumerate(sequence):
            if aa in ['T', 'N', 'Q', 'S']:
                positions.append(i + 1)
        if len(positions) < 2:
            # 回退：取所有位置
            positions = list(range(1, len(sequence) + 1))
        return positions

    @staticmethod
    def _pct_change(old: float, new: float) -> float:
        if old == 0:
            return 100.0 if new > 0 else 0.0
        return round((new - old) / old * 100, 2)

    def _comparison_verdict(self, orig: SimulationResult,
                            mut: SimulationResult) -> str:
        """突变对比判定"""
        th_better = mut.estimated_th > orig.estimated_th
        iri_better = mut.estimated_iri_ic50 < orig.estimated_iri_ic50
        stability_better = mut.stability_score > orig.stability_score

        improvements = sum([th_better, iri_better, stability_better])

        if improvements >= 3:
            return "EXCELLENT: 突变全面改善了AFP性能"
        elif improvements >= 2:
            return "GOOD: 突变在多个维度改善了性能"
        elif improvements >= 1:
            return "MIXED: 突变在某些方面改善但在其他方面可能没有提升"
        else:
            return "POOR: 突变未带来预期的性能改善——建议重新考虑策略"
