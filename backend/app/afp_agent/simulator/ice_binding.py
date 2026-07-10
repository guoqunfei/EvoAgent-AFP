"""
抗冻蛋白冰结合模拟器

三层简化模拟策略（全部 Mac CPU 可运行）：
Layer 1: 几何评分引擎 — 冰结合面互补性评估（毫秒级）
Layer 2: 物理化学评分引擎 — 序列特征→功能预测（毫秒级）
Layer 3: 简化经验模型 — TH/IRI 活性估计
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class IcePlane(Enum):
    BASAL = "basal"
    PRISM = "prism"
    PYRAMIDAL_201 = "pyramidal_201"
    PYRAMIDAL_110 = "pyramidal_110"


# Ice lattice constants
ICE_LATTICE = {
    IcePlane.BASAL: {"o_spacing": 7.35, "description": "Basal plane {0001}"},
    IcePlane.PRISM: {"o_spacing": 4.52, "description": "Prism plane {10-10}"},
    IcePlane.PYRAMIDAL_201: {"o_spacing": 16.5, "description": "Pyramidal plane {20-21}"},
    IcePlane.PYRAMIDAL_110: {"o_spacing": 7.85, "description": "Pyramidal plane {11-20}"},
}

# Amino acid ice-binding scores (empirical, based on experimental data)
AA_ICE_BINDING_SCORE = {
    'T': 1.00, 'N': 0.70, 'Q': 0.65, 'S': 0.50,
    'A': 0.40, 'V': 0.35, 'I': 0.35, 'L': 0.30, 'M': 0.25, 'G': 0.20,
    'P': 0.05, 'C': 0.10,
    'Y': -0.10, 'F': -0.20, 'W': -0.30, 'H': -0.15,
    'D': -0.50, 'E': -0.50, 'K': -0.60, 'R': -0.60,
}

# Bulky residues that disrupt IBS flatness
BULKY_RESIDUES = {'F', 'W', 'Y', 'R', 'K', 'E', 'Q', 'M'}
SMALL_RESIDUES = {'A', 'G', 'S', 'T', 'V'}

# Beta-sheet propensity (for structural context)
BETA_SHEET_PROPENSITY = {
    'A': 0.83, 'C': 1.19, 'D': 0.54, 'E': 0.37, 'F': 1.38,
    'G': 0.75, 'H': 0.87, 'I': 1.60, 'K': 0.74, 'L': 1.30,
    'M': 1.05, 'N': 0.89, 'P': 0.55, 'Q': 1.10, 'R': 0.93,
    'S': 0.75, 'T': 1.19, 'V': 1.70, 'W': 1.37, 'Y': 1.47,
}


@dataclass
class IceBindingResult:
    """冰结合模拟结果"""
    sequence: str
    sequence_length: int

    # Geometry scores
    overall_geometry_score: float
    spacing_match_score: float
    residue_quality_score: float
    flatness_prediction: float

    # Activity predictions
    estimated_th_activity: float  # °C
    estimated_iri_activity: float  # IC50 in µM (lower is better)

    # Physicochemical
    net_charge: float
    hydrophobicity: float
    beta_sheet_propensity: float
    cys_content: float  # for disulfide assessment
    thr_content: float

    # Assessment
    target_ice_plane: str
    activity_assessment: str
    design_quality: str

    def to_dict(self) -> dict:
        return {
            "sequence_length": self.sequence_length,
            "overall_geometry_score": round(self.overall_geometry_score, 3),
            "spacing_match_score": round(self.spacing_match_score, 3),
            "residue_quality_score": round(self.residue_quality_score, 3),
            "flatness_prediction": round(self.flatness_prediction, 3),
            "estimated_th_activity_C": round(self.estimated_th_activity, 2),
            "estimated_iri_activity_uM": round(self.estimated_iri_activity, 2),
            "net_charge": round(self.net_charge, 2),
            "hydrophobicity": round(self.hydrophobicity, 3),
            "beta_sheet_propensity": round(self.beta_sheet_propensity, 3),
            "cys_content_pct": round(self.cys_content * 100, 1),
            "thr_content_pct": round(self.thr_content * 100, 1),
            "target_ice_plane": self.target_ice_plane,
            "activity_assessment": self.activity_assessment,
            "design_quality": self.design_quality,
        }


@dataclass
class ComparisonResult:
    """模拟对比结果"""
    original: IceBindingResult
    mutated: IceBindingResult
    th_change_pct: float
    iri_change_pct: float
    geometry_change: float
    assessment: str
    recommendation: str


class AFPIceBindingSimulator:
    """
    抗冻蛋白冰结合模拟器

    基于几何评分+物理化学特征+经验模型的简化模拟引擎
    全部计算在 Mac CPU 上毫秒级完成，无需GPU
    """

    def simulate(self, sequence: str,
                 ibs_positions: Optional[List[int]] = None,
                 target_plane: IcePlane = IcePlane.PRISM) -> IceBindingResult:
        """
        对AFP序列进行冰结合模拟

        Args:
            sequence: 氨基酸序列
            ibs_positions: 已知/推测的冰结合面残基位置（1-indexed）
            target_plane: 靶向冰晶面
        """
        seq_len = len(sequence)

        # Auto-detect IBS positions if not provided
        if ibs_positions is None:
            ibs_positions = self._detect_ibs_positions(sequence, target_plane)

        # Layer 1: Geometry scoring
        spacing_score = self._calculate_spacing_match(ibs_positions, target_plane)
        residue_score = self._calculate_residue_quality(
            [sequence[p - 1] for p in ibs_positions if p <= seq_len]
        )
        flatness_score = self._predict_flatness(
            [sequence[p - 1] for p in ibs_positions if p <= seq_len]
        )

        overall_geo = 0.4 * spacing_score + 0.35 * residue_score + 0.25 * flatness_score

        # Layer 2: Physicochemical features
        net_charge = self._calculate_net_charge(sequence)
        hydrophobicity = self._calculate_hydrophobicity(sequence)
        beta_propensity = self._calculate_beta_propensity(sequence)
        cys_content = sequence.count('C') / seq_len
        thr_content = sequence.count('T') / seq_len

        # Layer 3: Activity estimation (empirical models)
        est_iri = self._estimate_iri_activity(overall_geo, len(ibs_positions))
        est_th = self._estimate_th_activity(
            overall_geo, len(ibs_positions),
            self._has_rigid_scaffold(sequence)
        )

        # Assessment
        activity = self._assess_activity(overall_geo, est_th, est_iri)
        quality = self._assess_design_quality(overall_geo, flatness_score, residue_score)

        return IceBindingResult(
            sequence=sequence,
            sequence_length=seq_len,
            overall_geometry_score=overall_geo,
            spacing_match_score=spacing_score,
            residue_quality_score=residue_score,
            flatness_prediction=flatness_score,
            estimated_th_activity=est_th,
            estimated_iri_activity=est_iri,
            net_charge=net_charge,
            hydrophobicity=hydrophobicity,
            beta_sheet_propensity=beta_propensity,
            cys_content=cys_content,
            thr_content=thr_content,
            target_ice_plane=target_plane.value,
            activity_assessment=activity,
            design_quality=quality,
        )

    def compare(self, original_seq: str, mutated_seq: str,
                ibs_positions: Optional[List[int]] = None) -> ComparisonResult:
        """对比原始序列和突变序列的冰结合性能"""
        orig = self.simulate(original_seq, ibs_positions)
        mut = self.simulate(mutated_seq, ibs_positions)

        # Calculate changes (IRI: lower is better, so negative change is good)
        th_change = self._pct_change(orig.estimated_th_activity, mut.estimated_th_activity)
        iri_change = self._pct_change(orig.estimated_iri_activity, mut.estimated_iri_activity)
        # For IRI, decrease is improvement, so we invert
        iri_improvement = -iri_change
        geo_change = mut.overall_geometry_score - orig.overall_geometry_score

        # Overall assessment
        improvements = []
        if th_change > 5:
            improvements.append(f"TH +{th_change:.0f}%")
        if iri_improvement > 5:
            improvements.append(f"IRI improved {iri_improvement:.0f}%")

        if improvements:
            assessment = f"Improved: {', '.join(improvements)}"
        elif th_change < -10 or iri_improvement < -10:
            assessment = "Performance decreased"
        else:
            assessment = "No significant change"

        return ComparisonResult(
            original=orig, mutated=mut,
            th_change_pct=round(th_change, 1),
            iri_change_pct=round(iri_change, 1),
            geometry_change=round(geo_change, 3),
            assessment=assessment,
            recommendation=self._generate_recommendation(th_change, iri_improvement),
        )

    def _detect_ibs_positions(self, sequence: str, plane: IcePlane) -> List[int]:
        """Auto-detect likely IBS positions based on Thr/Asn/Gln pattern"""
        positions = []
        target_aa = {'T', 'N', 'Q'}
        for i, aa in enumerate(sequence, 1):
            if aa in target_aa:
                positions.append(i)
        return positions if positions else list(range(1, min(len(sequence) + 1, 5)))

    def _calculate_spacing_match(self, positions: List[int], plane: IcePlane) -> float:
        """Calculate how well IBS residue spacing matches ice lattice oxygen spacing"""
        if len(positions) < 2:
            return 0.3

        target_spacing = ICE_LATTICE[plane]["o_spacing"]
        matches = 0
        total = 0

        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                dist = abs(positions[j] - positions[i]) * 3.5  # approximate: 1 residue ≈ 3.5Å
                for n in range(1, 6):
                    expected = n * target_spacing
                    if abs(dist - expected) / max(expected, 0.1) < 0.20:
                        matches += 1
                        break
                total += 1

        return matches / max(total, 1)

    def _calculate_residue_quality(self, ibs_residues: List[str]) -> float:
        """Calculate ice-binding residue quality score"""
        if not ibs_residues:
            return 0.0
        scores = [AA_ICE_BINDING_SCORE.get(aa, 0.0) for aa in ibs_residues]
        positive_count = sum(1 for s in scores if s > 0.2)
        avg_score = sum(scores) / len(scores)
        return 0.6 * max(avg_score, 0) + 0.4 * (positive_count / len(scores))

    def _predict_flatness(self, ibs_residues: List[str]) -> float:
        """Predict IBS flatness based on residue types"""
        if not ibs_residues:
            return 0.5
        bulky = sum(1 for aa in ibs_residues if aa in BULKY_RESIDUES)
        small = sum(1 for aa in ibs_residues if aa in SMALL_RESIDUES)
        flatness = 1.0 - (bulky / len(ibs_residues)) * 0.8
        flatness += (small / len(ibs_residues)) * 0.2
        return max(0.0, min(1.0, flatness))

    def _calculate_net_charge(self, sequence: str) -> float:
        """Calculate net charge at pH 7"""
        charge = 0
        charge += sequence.count('K') + sequence.count('R')  # +1
        charge += 0.5 * sequence.count('H')  # ~+0.5 at pH7
        charge -= sequence.count('D') + sequence.count('E')  # -1
        return charge

    def _calculate_hydrophobicity(self, sequence: str) -> float:
        """Calculate average hydrophobicity (Kyte-Doolittle scale simplified)"""
        kd = {'A': 1.8, 'C': 2.5, 'D': -3.5, 'E': -3.5, 'F': 2.8, 'G': -0.4,
              'H': -3.2, 'I': 4.5, 'K': -3.9, 'L': 3.8, 'M': 1.9, 'N': -3.5,
              'P': -1.6, 'Q': -3.5, 'R': -4.5, 'S': -0.8, 'T': -0.7,
              'V': 4.2, 'W': -0.9, 'Y': -1.3}
        return sum(kd.get(aa, 0) for aa in sequence) / len(sequence)

    def _calculate_beta_propensity(self, sequence: str) -> float:
        """Calculate average beta-sheet propensity"""
        return sum(BETA_SHEET_PROPENSITY.get(aa, 1.0) for aa in sequence) / len(sequence)

    def _has_rigid_scaffold(self, sequence: str) -> bool:
        """Check for disulfide-bond-rigidified scaffold"""
        return sequence.count('C') >= 4 and sequence.count('C') % 2 == 0

    def _estimate_iri_activity(self, geometry_score: float, n_ibs: int) -> float:
        """Estimate IRI activity (IC50 in µM) based on empirical model"""
        return max(0.1, 50.0 * math.exp(-3.5 * geometry_score) * math.exp(-0.05 * n_ibs))

    def _estimate_th_activity(self, geometry_score: float, n_ibs: int, rigid: bool) -> float:
        """Estimate TH activity (°C) based on empirical model"""
        if geometry_score < 0.5:
            return 0.0
        base = 0.1
        n_factor = 1.0 if n_ibs <= 6 else (3.0 if n_ibs <= 20 else 10.0)
        rigid_factor = 3.0 if rigid else 1.0
        return min(7.0, base * n_factor * rigid_factor)

    def _assess_activity(self, geo: float, th: float, iri: float) -> str:
        if geo > 0.8:
            return "Hyperactive-level (insect-grade AFP)"
        elif geo > 0.6:
            return "Moderate activity (fish AFP-grade)"
        elif geo > 0.4:
            return "Low but measurable IRI activity"
        else:
            return "Likely inactive — redesign IBS"

    def _assess_design_quality(self, geo: float, flatness: float, quality: float) -> str:
        avg = (geo + flatness + quality) / 3
        if avg > 0.7:
            return "Excellent design — well-formed ice-binding surface"
        elif avg > 0.5:
            return "Good design — some optimization possible"
        elif avg > 0.3:
            return "Fair — needs improvement in IBS geometry"
        else:
            return "Poor — fundamental IBS redesign needed"

    def _pct_change(self, original: float, mutated: float) -> float:
        if original == 0:
            return 100.0 if mutated > 0 else 0.0
        return ((mutated - original) / original) * 100

    def _generate_recommendation(self, th_change: float, iri_improvement: float) -> str:
        if th_change > 10 and iri_improvement > 10:
            return "Strong candidate — both TH and IRI improved. Recommend experimental validation."
        elif th_change > 10:
            return "TH improved significantly. Good for freeze-point depression applications."
        elif iri_improvement > 10:
            return "IRI improved significantly. Good for ice recrystallization control applications."
        elif th_change > -5 and iri_improvement > -5:
            return "Neutral change. Consider alternative mutation strategies."
        else:
            return "Performance decreased. Revert and try different mutations."
