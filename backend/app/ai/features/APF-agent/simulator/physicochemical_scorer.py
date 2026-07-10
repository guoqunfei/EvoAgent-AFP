# simulator/physicochemical_scorer.py
"""
物理化学评分引擎
基于序列物理化学特征的功能预测 —— 毫秒级
"""

import math
from typing import Dict
from dataclasses import dataclass


@dataclass
class PhysicochemicalProfile:
    """物理化学特征"""
    sequence: str
    length: int
    molecular_weight: float          # Da
    gravy: float                      # 总平均疏水性
    net_charge_ph7: float
    isoelectric_point: float
    instability_index: float          # Guruprasad
    aliphatic_index: float
    aromatic_content: float
    pro_content: float
    gly_content: float
    cys_content: float
    hydrophobic_moment: float         # α-螺旋两亲性
    predicted_solubility: float       # 0-1
    predicted_thermal_stability: float # 0-1
    predicted_expression_score: float  # 0-1


class PhysicochemicalScorer:
    """
    基于序列物理化学特征的功能预测器

    特征：
    - 疏水力矩（α-螺旋两亲性评估）
    - 芳香残基含量
    - 净电荷/GRAVY/pI
    - Pro/Gly含量（骨架灵活性）
    - Cys含量（二硫键潜力）
    - 不稳定指数
    - 脂肪族指数
    """

    # 分子量（Da）
    AA_MW = {
        'A': 89.09, 'C': 121.15, 'D': 133.10, 'E': 147.13,
        'F': 165.19, 'G': 75.07, 'H': 155.16, 'I': 131.17,
        'K': 146.19, 'L': 131.17, 'M': 149.21, 'N': 132.12,
        'P': 115.13, 'Q': 146.15, 'R': 174.20, 'S': 105.09,
        'T': 119.12, 'V': 117.15, 'W': 204.23, 'Y': 181.19,
    }

    # 脂肪族指数参数
    ALIPHATIC_AAS = {'A': 1.0, 'V': 1.0, 'I': 1.0, 'L': 1.0}

    def compute_profile(self, sequence: str) -> PhysicochemicalProfile:
        """计算完整物理化学特征"""
        seq = sequence.upper().strip()
        length = len(seq)

        mw = self._compute_mw(seq)
        gravy = self._compute_gravy(seq)
        charge = self._compute_net_charge(seq)
        pi = self._compute_pI(seq)
        ii = self._compute_instability_index(seq)
        ai = self._compute_aliphatic_index(seq)
        aromatic = self._compute_aromatic_content(seq)
        pro = seq.count('P') / length if length else 0
        gly = seq.count('G') / length if length else 0
        cys = seq.count('C') / length if length else 0
        hm = self._compute_hydrophobic_moment(seq)

        # 预测评分
        solubility = self._predict_solubility(seq)
        thermal_stability = self._predict_thermal_stability(seq)
        expression = self._predict_expression(seq)

        return PhysicochemicalProfile(
            sequence=seq, length=length,
            molecular_weight=round(mw, 2),
            gravy=round(gravy, 3),
            net_charge_ph7=round(charge, 2),
            isoelectric_point=round(pi, 2),
            instability_index=round(ii, 2),
            aliphatic_index=round(ai, 2),
            aromatic_content=round(aromatic, 3),
            pro_content=round(pro, 3),
            gly_content=round(gly, 3),
            cys_content=round(cys, 3),
            hydrophobic_moment=round(hm, 3),
            predicted_solubility=round(solubility, 3),
            predicted_thermal_stability=round(thermal_stability, 3),
            predicted_expression_score=round(expression, 3),
        )

    def to_dict(self, profile: PhysicochemicalProfile) -> dict:
        """转为字典格式"""
        return {
            "sequence_length": profile.length,
            "molecular_weight_Da": profile.molecular_weight,
            "GRAVY": profile.gravy,
            "net_charge_pH7": profile.net_charge_ph7,
            "isoelectric_point": profile.isoelectric_point,
            "instability_index": profile.instability_index,
            "aliphatic_index": profile.aliphatic_index,
            "aromatic_content": profile.aromatic_content,
            "pro_content": profile.pro_content,
            "gly_content": profile.gly_content,
            "cys_content": profile.cys_content,
            "hydrophobic_moment": profile.hydrophobic_moment,
            "predicted_solubility": profile.predicted_solubility,
            "predicted_thermal_stability": profile.predicted_thermal_stability,
            "predicted_expression_score": profile.predicted_expression_score,
            "stability_assessment": self._assess_stability(profile.predicted_thermal_stability),
            "expression_assessment": self._assess_expression(profile.predicted_expression_score),
        }

    def _compute_mw(self, seq: str) -> float:
        return sum(self.AA_MW.get(aa, 0) for aa in seq) - 18.015 * (len(seq) - 1)

    def _compute_gravy(self, seq: str) -> float:
        """总平均疏水性"""
        hydropathy = {
            'A': 1.8, 'C': 2.5, 'D': -3.5, 'E': -3.5, 'F': 2.8,
            'G': -0.4, 'H': -3.2, 'I': 4.5, 'K': -3.9, 'L': 3.8,
            'M': 1.9, 'N': -3.5, 'P': -1.6, 'Q': -3.5, 'R': -4.5,
            'S': -0.8, 'T': -0.7, 'V': 4.2, 'W': -0.9, 'Y': -1.3,
        }
        return sum(hydropathy.get(aa, 0) for aa in seq) / max(len(seq), 1)

    def _compute_net_charge(self, seq: str) -> float:
        """pH7时的净电荷"""
        pos = seq.count('K') + seq.count('R')
        neg = seq.count('D') + seq.count('E')
        his = seq.count('H') * 0.5
        return pos - neg + his

    def _compute_pI(self, seq: str) -> float:
        """等电点（简化迭代法）"""
        def charge_at(pH):
            pos = (seq.count('K') / (1 + 10**(pH - 10.5)) +
                   seq.count('R') / (1 + 10**(pH - 12.5)) +
                   seq.count('H') / (1 + 10**(pH - 6.0)))
            neg = (seq.count('D') / (1 + 10**(3.9 - pH)) +
                   seq.count('E') / (1 + 10**(4.3 - pH)) +
                   seq.count('C') / (1 + 10**(8.3 - pH)) +
                   seq.count('Y') / (1 + 10**(10.1 - pH)))
            return pos - neg

        lo, hi = 0.0, 14.0
        for _ in range(30):
            mid = (lo + hi) / 2
            if charge_at(mid) > 0:
                lo = mid
            else:
                hi = mid
        return round(mid, 2)

    def _compute_instability_index(self, seq: str) -> float:
        """Guruprasad不稳定指数（简化版）"""
        if len(seq) < 2:
            return 40.0

        # 简化二肽权重（完整版有400个二肽值）
        dipeptide_weights = {
            'AA': 1.0, 'GG': 0.5, 'PP': 1.0, 'GP': 1.0, 'PG': 1.0,
            'AP': 1.0, 'SS': 0.5, 'TT': 0.5, 'NN': 0.5, 'QQ': 0.5,
            'DD': -0.5, 'EE': -0.5, 'KK': -0.5, 'RR': -0.5,
            'CC': 1.0, 'MM': 1.0, 'WW': 3.0, 'YY': 2.0, 'FF': 2.0,
        }
        total = 0.0
        for i in range(len(seq) - 1):
            dipep = seq[i:i+2]
            total += dipeptide_weights.get(dipep, 1.0)

        return (total / (len(seq) - 1)) * 10 + 30

    def _compute_aliphatic_index(self, seq: str) -> float:
        """脂肪族指数"""
        length = len(seq)
        if length == 0:
            return 0.0
        ala = seq.count('A') / length
        val = seq.count('V') / length
        ile = seq.count('I') / length
        leu = seq.count('L') / length
        return (ala + 2.9 * val + 3.9 * (ile + leu)) * 100

    def _compute_aromatic_content(self, seq: str) -> float:
        """芳香残基含量"""
        length = max(len(seq), 1)
        return (seq.count('F') + seq.count('W') + seq.count('Y')) / length

    def _compute_hydrophobic_moment(self, seq: str) -> float:
        """疏水力矩（α-螺旋两亲性，简化版）"""
        # 使用Eisenberg量表
        hydrophobicity = {
            'A': 0.62, 'C': 0.29, 'D': -0.90, 'E': -0.74, 'F': 1.19,
            'G': 0.48, 'H': -0.40, 'I': 1.38, 'K': -1.50, 'L': 1.06,
            'M': 0.64, 'N': -0.78, 'P': 0.12, 'Q': -0.85, 'R': -2.53,
            'S': -0.18, 'T': -0.05, 'V': 1.08, 'W': 0.81, 'Y': 0.26
        }
        # 简化：计算每3.6残基的疏水性波动
        period = 3.6
        length = len(seq)
        if length < 7:
            return 0.0

        moment = 0.0
        for i in range(length):
            angle = 2 * math.pi * i / period
            h = hydrophobicity.get(seq[i], 0)
            moment += h * math.cos(angle)

        return abs(moment) / max(length, 1)

    def _predict_solubility(self, seq: str) -> float:
        """预测可溶性"""
        gravy = self._compute_gravy(seq)
        charge = abs(self._compute_net_charge(seq))

        # 亲水性 + 带电荷 → 高可溶性
        score = 1.0 / (1.0 + math.exp(gravy * 1.5))
        # 电荷贡献
        score += min(charge / 10, 0.3)
        # 过长序列惩罚
        if len(seq) > 400:
            score -= 0.15

        return max(0.0, min(1.0, score))

    def _predict_thermal_stability(self, seq: str) -> float:
        """预测热稳定性"""
        ii = self._compute_instability_index(seq)
        score = max(0, 1 - ii / 100)

        # Cys二硫键
        cys = seq.count('C')
        if cys >= 4 and cys % 2 == 0:
            score += 0.25

        # Pro刚性化
        score += seq.count('P') / max(len(seq), 1) * 2

        # 芳香残基稳定化
        score += self._compute_aromatic_content(seq) * 0.5

        return max(0.0, min(1.0, score))

    def _predict_expression(self, seq: str) -> float:
        """预测表达可行性"""
        gravy = self._compute_gravy(seq)
        # 亲水性有利于可溶表达
        score = 1.0 / (1.0 + math.exp(gravy * 2))

        # Cys含量适中（太多导致错误二硫键）
        cys_pct = seq.count('C') / max(len(seq), 1)
        if cys_pct > 0.1:
            score -= 0.2

        # 长度适中
        length = len(seq)
        if 30 <= length <= 400:
            score += 0.1

        return max(0.0, min(1.0, score))

    def _assess_stability(self, score: float) -> str:
        if score > 0.7:
            return "高稳定性——适合长期储存和极端条件"
        elif score > 0.4:
            return "中等稳定性——常规条件下可行"
        else:
            return "低稳定性——可能需要工程化改造"

    def _assess_expression(self, score: float) -> str:
        if score > 0.7:
            return "高表达潜力——预计>50 mg/L (E. coli)"
        elif score > 0.4:
            return "中等表达潜力——预计10-50 mg/L"
        else:
            return "低表达潜力——可能需要融合标签或优化密码子"
