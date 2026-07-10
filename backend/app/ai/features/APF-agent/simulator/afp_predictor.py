# simulator/afp_predictor.py
"""
简化AFP预测器（ICEPIC等效）
基于序列组成的机器学习替代——不需要GPU
"""

import math
from typing import Dict, List


class SimpleAFPPredictor:
    """
    简化AFP预测器（不需要GPU）

    基于ICEPIC论文（2025）的关键特征：
    - Ala含量（Type I AFP的强信号）
    - Thr含量（IBS标志）
    - Cys含量（昆虫AFP的刚性支架标志）
    - 重复基序检测
    - 序列长度
    """

    def __init__(self):
        pass

    def predict_afp_probability(self, sequence: str) -> float:
        """
        预测序列是AFP的概率（0-1）

        基于特征加权逻辑回归近似
        """
        seq = sequence.upper()
        length = max(len(seq), 1)

        features = self._extract_features(seq)

        # 简化逻辑回归（权重基于ICEPIC描述的特征重要性）
        logit = 0.0

        # Thr含量（最强特征）
        logit += features['thr_content'] * 8.0

        # Ala含量（Type I特征）
        logit += features['ala_content'] * 3.0

        # Cys含量（昆虫/细菌特征）
        logit += features['cys_content'] * 4.0

        # Asn+Gln（Type III特征）
        logit += (features['asn_content'] + features['gln_content']) * 2.0

        # 重复模式
        logit += features['repeat_score'] * 3.0

        # TXT模式
        logit += features['txt_pattern'] * 5.0

        # 序列长度适中
        if 30 <= len(seq) <= 400:
            logit += 1.0
        if 60 <= len(seq) <= 250:
            logit += 1.0

        # 负电荷惩罚（AFP通常近中性）
        charge = features['net_charge']
        logit -= abs(charge) * 0.5

        # 偏置
        logit -= 3.0

        # Sigmoid
        return round(1.0 / (1.0 + math.exp(-logit)), 4)

    def predict_expression_pastoris(self, sequence: str) -> float:
        """
        预测在毕赤酵母中的表达量（mg/L）

        基于ICEPIC的回归特征（R²=0.64）
        """
        seq = sequence.upper()
        length = max(len(seq), 1)

        gravy = self._compute_gravy(seq)
        ala = seq.count('A') / length
        cys = seq.count('C') / length

        # 简化回归
        base = 50.0  # mg/L 基线

        # 亲水性有利于分泌表达
        base -= gravy * 20

        # Ala含量适度
        if 0.15 < ala < 0.50:
            base += 20

        # 过高Cys降低产量
        if cys > 0.08:
            base *= 0.5

        # 长度惩罚
        if len(seq) > 300:
            base *= 0.6
        elif len(seq) < 20:
            base *= 0.4

        return max(1.0, round(base, 1))

    def predict_thermal_hysteresis(self, sequence: str,
                                    ibs_positions: List[int] = None) -> float:
        """
        预测热滞后活性（°C）

        基于ICEPIC的TH回归（R²≥0.79）
        """
        seq = sequence.upper()
        length = max(len(seq), 1)

        thr = seq.count('T') / length
        cys = seq.count('C') / length

        # 特征工程
        base = 0.0

        # Thr含量
        base += thr * 15.0

        # Cys刚性支架
        if cys > 0.04:
            base += 2.0

        # IBS残基数量
        if ibs_positions:
            n_ibs = len(ibs_positions)
            if n_ibs > 20:
                base += 3.0
            elif n_ibs > 8:
                base += 1.0

        # TXT模式
        if self._has_txt_pattern(seq):
            base += 1.5

        # 上限
        return min(7.0, max(0.0, round(base, 2)))

    def _extract_features(self, seq: str) -> Dict[str, float]:
        """提取简化特征集"""
        length = max(len(seq), 1)

        return {
            'thr_content': seq.count('T') / length,
            'ala_content': seq.count('A') / length,
            'cys_content': seq.count('C') / length,
            'asn_content': seq.count('N') / length,
            'gln_content': seq.count('Q') / length,
            'ser_content': seq.count('S') / length,
            'gly_content': seq.count('G') / length,
            'repeat_score': self._compute_repeat_score(seq),
            'txt_pattern': 1.0 if self._has_txt_pattern(seq) else 0.0,
            'net_charge': self._compute_net_charge(seq),
            'gravy': self._compute_gravy(seq),
        }

    def _compute_repeat_score(self, seq: str) -> float:
        """计算重复模式评分"""
        if len(seq) < 22:
            return 0.0

        # 检测11残基重复（Type I特征）
        score = 0.0
        for period in [3, 6, 11, 12]:
            matches = 0
            for i in range(len(seq) - period):
                if seq[i] == seq[i + period]:
                    matches += 1
            period_score = matches / max(len(seq) - period, 1)
            score = max(score, period_score)

        return min(1.0, score)

    def _has_txt_pattern(self, seq: str) -> bool:
        """检测TXT模式"""
        for i in range(len(seq) - 2):
            if seq[i] == 'T' and seq[i+2] == 'T':
                return True
        return False

    def _compute_gravy(self, seq: str) -> float:
        """计算GRAVY"""
        hydropathy = {
            'A': 1.8, 'C': 2.5, 'D': -3.5, 'E': -3.5, 'F': 2.8,
            'G': -0.4, 'H': -3.2, 'I': 4.5, 'K': -3.9, 'L': 3.8,
            'M': 1.9, 'N': -3.5, 'P': -1.6, 'Q': -3.5, 'R': -4.5,
            'S': -0.8, 'T': -0.7, 'V': 4.2, 'W': -0.9, 'Y': -1.3,
        }
        return sum(hydropathy.get(aa, 0) for aa in seq) / max(len(seq), 1)

    def _compute_net_charge(self, seq: str) -> float:
        """计算净电荷"""
        return seq.count('K') + seq.count('R') - seq.count('D') - seq.count('E')
