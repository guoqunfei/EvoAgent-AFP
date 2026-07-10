# knowledge/seq_analyzer.py
"""
AFP序列分析器
三级分析：基序级→结构域级→全长序列级
"""

import re
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from .motifs import AFPMotifLibrary, AFP_MOTIF_DATABASE, AFPType, IcePlane


# 氨基酸物理化学性质
AA_PROPERTIES = {
    'A': {'hydrophobicity': 1.8, 'volume': 88.6, 'charge': 0, 'category': 'hydrophobic'},
    'C': {'hydrophobicity': 2.5, 'volume': 108.5, 'charge': 0, 'category': 'special'},
    'D': {'hydrophobicity': -3.5, 'volume': 111.1, 'charge': -1, 'category': 'charged'},
    'E': {'hydrophobicity': -3.5, 'volume': 138.4, 'charge': -1, 'category': 'charged'},
    'F': {'hydrophobicity': 2.8, 'volume': 189.9, 'charge': 0, 'category': 'aromatic'},
    'G': {'hydrophobicity': -0.4, 'volume': 60.1, 'charge': 0, 'category': 'special'},
    'H': {'hydrophobicity': -3.2, 'volume': 153.2, 'charge': 0.5, 'category': 'charged'},
    'I': {'hydrophobicity': 4.5, 'volume': 166.7, 'charge': 0, 'category': 'hydrophobic'},
    'K': {'hydrophobicity': -3.9, 'volume': 168.6, 'charge': 1, 'category': 'charged'},
    'L': {'hydrophobicity': 3.8, 'volume': 166.7, 'charge': 0, 'category': 'hydrophobic'},
    'M': {'hydrophobicity': 1.9, 'volume': 162.9, 'charge': 0, 'category': 'hydrophobic'},
    'N': {'hydrophobicity': -3.5, 'volume': 114.1, 'charge': 0, 'category': 'polar'},
    'P': {'hydrophobicity': -1.6, 'volume': 112.7, 'charge': 0, 'category': 'special'},
    'Q': {'hydrophobicity': -3.5, 'volume': 143.8, 'charge': 0, 'category': 'polar'},
    'R': {'hydrophobicity': -4.5, 'volume': 173.4, 'charge': 1, 'category': 'charged'},
    'S': {'hydrophobicity': -0.8, 'volume': 89.0, 'charge': 0, 'category': 'polar'},
    'T': {'hydrophobicity': -0.7, 'volume': 116.1, 'charge': 0, 'category': 'polar'},
    'V': {'hydrophobicity': 4.2, 'volume': 140.0, 'charge': 0, 'category': 'hydrophobic'},
    'W': {'hydrophobicity': -0.9, 'volume': 227.8, 'charge': 0, 'category': 'aromatic'},
    'Y': {'hydrophobicity': -1.3, 'volume': 193.6, 'charge': 0, 'category': 'aromatic'},
}

# 冰结合评分 (经验值)
AA_ICE_BINDING_SCORE = {
    'T': 1.00, 'N': 0.70, 'Q': 0.65, 'S': 0.50,
    'A': 0.40, 'V': 0.35, 'I': 0.35, 'L': 0.30,
    'M': 0.25, 'G': 0.20, 'C': 0.10, 'P': 0.05,
    'Y': -0.10, 'F': -0.20, 'W': -0.30, 'H': -0.15,
    'D': -0.50, 'E': -0.50, 'K': -0.60, 'R': -0.60,
}


@dataclass
class AFPAnalysisResult:
    """AFP序列分析结果"""
    sequence: str
    length: int

    # 基序匹配
    motif_matches: List[Dict] = field(default_factory=list)

    # AFP类型预测
    afp_type_prediction: str = "Unknown"
    type_confidence: float = 0.0
    type_scores: Dict[str, float] = field(default_factory=dict)

    # IBS识别
    predicted_ibs_positions: List[int] = field(default_factory=list)
    predicted_ibs_residues: List[str] = field(default_factory=list)
    predicted_ice_plane: str = "Unknown"

    # 物理化学特征
    aa_composition: Dict[str, float] = field(default_factory=dict)
    thr_content: float = 0.0
    ala_content: float = 0.0
    cys_content: float = 0.0
    net_charge: float = 0.0
    gravy: float = 0.0          # 总平均疏水性
    hydrophobic_moment: float = 0.0
    isoelectric_point: float = 0.0
    instability_index: float = 0.0  # Guruprasad不稳定指数

    # 设计相关
    forbidden_positions: List[int] = field(default_factory=list)
    mutation_hotspots: List[Dict] = field(default_factory=list)
    design_potential_score: float = 0.0

    # 活性预测
    estimated_th: float = 0.0
    estimated_iri_ic50: float = 0.0
    estimated_expression_score: float = 0.0
    estimated_stability_score: float = 0.0


class AFPSeqAnalyzer:
    """
    抗冻蛋白序列分析器
    三级分析管道：基序扫描 → 类型分类 → 全长评估
    """

    def __init__(self):
        self.motif_library = AFPMotifLibrary()

    def analyze(self, sequence: str, query_intent: str = "full_analysis") -> AFPAnalysisResult:
        """
        对输入序列进行全面分析

        Args:
            sequence: 氨基酸序列（单字母代码）
            query_intent: 分析意图

        Returns:
            AFPAnalysisResult 包含完整分析结果
        """
        sequence = sequence.upper().strip()
        result = AFPAnalysisResult(sequence=sequence, length=len(sequence))

        # Level 1: 基序扫描
        result.motif_matches = self._scan_motifs(sequence)

        # Level 2: AFP类型预测
        type_result = self._predict_afp_type(sequence)
        result.afp_type_prediction = type_result[0]
        result.type_confidence = type_result[1]
        result.type_scores = type_result[2]

        # Level 3: 全长序列分析
        result.aa_composition = self._compute_composition(sequence)
        result.thr_content = result.aa_composition.get('T', 0)
        result.ala_content = result.aa_composition.get('A', 0)
        result.cys_content = result.aa_composition.get('C', 0)
        result.net_charge = self._compute_net_charge(sequence)
        result.gravy = self._compute_gravy(sequence)
        result.isoelectric_point = self._compute_pI(sequence)
        result.instability_index = self._compute_instability_index(sequence)

        # IBS识别
        ibs_result = self._identify_ibs(sequence, result.motif_matches)
        result.predicted_ibs_positions = ibs_result[0]
        result.predicted_ibs_residues = ibs_result[1]
        result.predicted_ice_plane = ibs_result[2]

        # 禁区识别
        result.forbidden_positions = self._identify_forbidden_positions(
            sequence, result.motif_matches
        )

        # 突变热点识别
        result.mutation_hotspots = self._identify_mutation_hotspots(
            sequence, result.predicted_ibs_positions
        )

        # 设计潜力评分
        result.design_potential_score = self._compute_design_potential(
            sequence, result
        )

        # 活性预测
        result.estimated_th = self._estimate_th(sequence, result)
        result.estimated_iri_ic50 = self._estimate_iri(sequence, result)
        result.estimated_expression_score = self._estimate_expression(sequence)
        result.estimated_stability_score = self._estimate_stability(sequence)

        return result

    # ========================
    # Level 1: 基序扫描
    # ========================
    def _scan_motifs(self, sequence: str) -> List[Dict]:
        """滑动窗口扫描已知IBS基序"""
        return self.motif_library.search_by_sequence(sequence)

    # ========================
    # Level 2: AFP类型预测
    # ========================
    def _predict_afp_type(self, sequence: str) -> Tuple[str, float, Dict[str, float]]:
        """
        基于序列特征预测AFP类型

        特征：
        - Thr含量（TYPE_I/INSECT/de novo的标志）
        - Ala含量（TYPE_I的标志）
        - Cys含量（INSECT/BACTERIAL的标志）
        - 序列长度
        - 模式匹配
        """
        length = len(sequence)
        scores = {}

        thr_pct = sequence.count('T') / max(length, 1)
        ala_pct = sequence.count('A') / max(length, 1)
        cys_pct = sequence.count('C') / max(length, 1)
        asn_pct = sequence.count('N') / max(length, 1)
        gln_pct = sequence.count('Q') / max(length, 1)
        gly_pct = sequence.count('G') / max(length, 1)

        # Type I 评分
        type1_score = 0.0
        if ala_pct > 0.25:
            type1_score += 0.3
        if ala_pct > 0.40:
            type1_score += 0.2
        if thr_pct > 0.05:
            type1_score += 0.2
        if 30 <= length <= 200:
            type1_score += 0.15
        if self._has_11mer_pattern(sequence):
            type1_score += 0.15
        scores["Type I (α-helical, fish)"] = min(type1_score, 1.0)

        # Type III 评分
        type3_score = 0.0
        if 60 <= length <= 80:
            type3_score += 0.3
        if asn_pct > 0.03 and gln_pct > 0.03 and thr_pct > 0.03:
            type3_score += 0.3
        if cys_pct < 0.03:
            type3_score += 0.2
        if 'N' in sequence and 'Q' in sequence and 'T' in sequence:
            type3_score += 0.2
        scores["Type III (β-sandwich, fish)"] = min(type3_score, 1.0)

        # 昆虫超活性 评分
        insect_score = 0.0
        if thr_pct > 0.08:
            insect_score += 0.25
        if cys_pct > 0.04:
            insect_score += 0.30
        if length > 70:
            insect_score += 0.15
        if self._has_txt_pattern(sequence):
            insect_score += 0.30
        scores["Insect hyperactive (β-helical)"] = min(insect_score, 1.0)

        # 细菌IBP 评分
        bacterial_score = 0.0
        if thr_pct > 0.03:
            bacterial_score += 0.2
        if cys_pct > 0.02:
            bacterial_score += 0.2
        if length > 100:
            bacterial_score += 0.2
        # Gly-rich可能指示非经典IBS
        if gly_pct > 0.10:
            bacterial_score += 0.2
        scores["Bacterial IBP"] = min(bacterial_score, 1.0)

        # De Novo 评分
        denovo_score = 0.0
        if thr_pct > 0.04 and ala_pct > 0.20:
            denovo_score += 0.3
        if self._has_regular_thr_spacing(sequence):
            denovo_score += 0.4
        if cys_pct < 0.02:
            denovo_score += 0.2
        scores["De novo designed"] = min(denovo_score, 1.0)

        # AFGP 评分
        afgp_score = 0.0
        if self._has_aat_repeat(sequence):
            afgp_score += 0.6
        if ala_pct > 0.30 and thr_pct > 0.15:
            afgp_score += 0.3
        scores["AFGP"] = min(afgp_score, 1.0)

        # 植物AFP
        plant_score = 0.0
        if asn_pct > 0.04 and thr_pct > 0.03:
            plant_score += 0.3
        if self._has_repeat_pattern(sequence, 12):
            plant_score += 0.3
        if cys_pct < 0.02:
            plant_score += 0.2
        scores["Plant AFP"] = min(plant_score, 1.0)

        # 最佳匹配
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]

        if best_score < 0.3:
            return ("Unknown/Unclassified", 0.0, scores)

        return (best_type, best_score, scores)

    def _has_11mer_pattern(self, seq: str) -> bool:
        """检测11残基重复模式（Type I特征）"""
        if len(seq) < 22:
            return False
        # 检查Thr间隔是否为11的倍数
        t_positions = [i for i, aa in enumerate(seq) if aa == 'T']
        if len(t_positions) < 2:
            return False
        for i in range(len(t_positions) - 1):
            diff = t_positions[i+1] - t_positions[i]
            if diff % 11 == 0:
                return True
        return False

    def _has_txt_pattern(self, seq: str) -> bool:
        """检测TXT模式（昆虫AFP特征）"""
        pattern = re.compile(r'T[^.]{1}T')
        return bool(pattern.search(seq))

    def _has_aat_repeat(self, seq: str) -> bool:
        """检测AAT重复（AFGP特征）"""
        return seq.count('AAT') >= 2 or seq.count('AAT') / max(len(seq), 1) > 0.05

    def _has_regular_thr_spacing(self, seq: str) -> bool:
        """检测Thr的规则间距"""
        t_positions = [i for i, aa in enumerate(seq) if aa == 'T']
        if len(t_positions) < 3:
            return False
        spacings = [t_positions[i+1] - t_positions[i] for i in range(len(t_positions)-1)]
        # 检查是否有>50%的间距相同
        from collections import Counter
        spacing_counts = Counter(spacings)
        most_common_count = spacing_counts.most_common(1)[0][1]
        return most_common_count >= len(spacings) * 0.5

    def _has_repeat_pattern(self, seq: str, period: int) -> bool:
        """检测重复模式"""
        if len(seq) < period * 2:
            return False
        # 简化：检查固定周期的相似性
        matches = 0
        for i in range(len(seq) - period):
            if seq[i] == seq[i + period]:
                matches += 1
        return matches / max(len(seq) - period, 1) > 0.25

    # ========================
    # Level 3: 全长评估
    # ========================
    def _compute_composition(self, sequence: str) -> Dict[str, float]:
        """计算氨基酸组成"""
        length = max(len(sequence), 1)
        return {aa: sequence.count(aa) / length for aa in 'ACDEFGHIKLMNPQRSTVWY'}

    def _compute_net_charge(self, sequence: str) -> float:
        """计算pH7时的净电荷"""
        charge = 0
        for aa in sequence:
            charge += AA_PROPERTIES.get(aa, {}).get('charge', 0)
        return charge

    def _compute_gravy(self, sequence: str) -> float:
        """计算总平均疏水性（GRAVY）"""
        if len(sequence) == 0:
            return 0.0
        total = sum(AA_PROPERTIES.get(aa, {}).get('hydrophobicity', 0) for aa in sequence)
        return total / len(sequence)

    def _compute_pI(self, sequence: str) -> float:
        """简化等电点计算"""
        # 使用简化的pKa值
        pKa = {
            'D': 3.9, 'E': 4.3, 'C': 8.3, 'Y': 10.1,
            'H': 6.0, 'K': 10.5, 'R': 12.5
        }
        # 二分搜索pI
        def net_charge_at_pH(pH):
            charge = 0
            for aa in sequence:
                if aa in pKa:
                    if aa in ['D', 'E', 'C', 'Y']:
                        charge += -1 / (1 + 10**(pKa[aa] - pH))
                    else:
                        charge += 1 / (1 + 10**(pH - pKa[aa]))
            charge += sequence.count('K') * 1 / (1 + 10**(pH - 10.5))
            charge += sequence.count('R') * 1 / (1 + 10**(pH - 12.5))
            charge += sequence.count('H') * 1 / (1 + 10**(pH - 6.0))
            charge -= sequence.count('D') * 1 / (1 + 10**(3.9 - pH))
            charge -= sequence.count('E') * 1 / (1 + 10**(4.3 - pH))
            return charge

        low, high = 0, 14
        for _ in range(20):
            mid = (low + high) / 2
            if net_charge_at_pH(mid) > 0:
                low = mid
            else:
                high = mid
        return round(mid, 2)

    def _compute_instability_index(self, sequence: str) -> float:
        """计算Guruprasad不稳定指数"""
        # 简化的不稳定指数计算
        dipeptide_values = {
            'AA': 1.0, 'AP': 1.0, 'AG': 0.5, 'AD': 0.5, 'AE': 0.5,
            'PP': 1.0, 'PG': 1.0, 'GG': 0.5, 'GP': 1.0,
            'SS': 0.5, 'TT': 0.5, 'NN': 0.5, 'QQ': 0.5,
        }
        if len(sequence) < 2:
            return 40.0

        total = 0.0
        for i in range(len(sequence) - 1):
            dipeptide = sequence[i:i+2]
            total += dipeptide_values.get(dipeptide, 1.0)
        return total / (len(sequence) - 1) * 40

    # ========================
    # IBS 识别
    # ========================
    def _identify_ibs(self, sequence: str, motif_matches: List[Dict]
                      ) -> Tuple[List[int], List[str], str]:
        """识别可能的冰结合面残基"""
        ibs_positions = []
        ibs_residues = []
        ice_plane = "Unknown"

        # 从基序匹配中获取IBS位置
        if motif_matches:
            best_match = motif_matches[0]
            ibs_positions = best_match.get("ibs_positions", [])
            ibs_residues = best_match.get("ibs_residues", [])
            ice_plane = best_match.get("target_ice_plane", "Unknown")

        # 如果没有基序匹配，基于序列特征推断
        if not ibs_positions:
            for i, aa in enumerate(sequence):
                if aa in ['T', 'N', 'Q', 'S']:
                    score = AA_ICE_BINDING_SCORE.get(aa, 0)
                    if score > 0.3:
                        ibs_positions.append(i + 1)
                        ibs_residues.append(f"{aa}{i+1}")

        # 推断冰面
        if ice_plane == "Unknown" and ibs_positions:
            ice_plane = self._infer_ice_plane(ibs_positions, sequence)

        # 过滤掉与序列长度不匹配的位置
        ibs_positions = [p for p in ibs_positions if p <= len(sequence)]

        return ibs_positions, ibs_residues, ice_plane

    def _infer_ice_plane(self, positions: List[int], sequence: str) -> str:
        """基于IBS残基间距推断靶向冰面"""
        if len(positions) < 2:
            return "Prism plane {10-10} (default)"

        spacings = []
        for i in range(len(positions) - 1):
            spacings.append((positions[i+1] - positions[i]) * 3.5)  # 近似1aa≈3.5Å

        avg_spacing = sum(spacings) / len(spacings)

        if avg_spacing < 6:
            return "Prism plane {10-10} (4.5Å spacing)"
        elif avg_spacing < 10:
            return "Basal plane {0001} (7.4Å spacing)"
        elif avg_spacing < 20:
            return "Pyramidal plane {20-21} (16.5Å spacing)"
        else:
            return "Pyramidal plane {11-20} (7.85Å spacing)"

    # ========================
    # 禁区与突变热点
    # ========================
    def _identify_forbidden_positions(self, sequence: str,
                                       motif_matches: List[Dict]) -> List[int]:
        """识别禁区（不可突变位置）"""
        forbidden = set()

        for match in motif_matches:
            # 从基序的forbidden_mutations解析位置
            for fm in match.get("forbidden_mutations", []):
                # 解析 "T2*" 格式
                import re as regex
                m = regex.match(r'([A-Z])(\d+)\*', fm)
                if m:
                    pos = int(m.group(2))
                    if pos <= len(sequence):
                        forbidden.add(pos)

        # 通用禁区规则
        # Cys参与二硫键配对
        cys_positions = [i+1 for i, aa in enumerate(sequence) if aa == 'C']
        if len(cys_positions) >= 4:
            for p in cys_positions:
                forbidden.add(p)  # 保守处理——所有Cys标记为禁区

        return sorted(list(forbidden))

    def _identify_mutation_hotspots(self, sequence: str,
                                      ibs_positions: List[int]) -> List[Dict]:
        """识别突变热点（可安全突变的非IBS残基）"""
        hotspots = []
        ibs_set = set(ibs_positions)

        for i, aa in enumerate(sequence):
            pos = i + 1
            if pos in ibs_set:
                continue  # 跳过IBS残基

            # 评估突变潜力
            score = 0
            suggestion = ""

            if aa in ['A']:
                score = 0.7
                suggestion = "Ala→Ser可提高溶解度"
            elif aa in ['G']:
                score = 0.5
                suggestion = "Gly→Ala可增强螺旋倾向"
            elif aa in ['S']:
                score = 0.6
                suggestion = "Ser→Thr可能增强冰结合"
            elif aa in ['K', 'R']:
                if pos not in ibs_set:
                    score = 0.4
                    suggestion = "带电残基→Ala/Ser可减少非特异性结合"

            if score > 0:
                hotspots.append({
                    "position": pos,
                    "current_aa": aa,
                    "mutation_potential": score,
                    "suggestion": suggestion,
                    "is_surface": True  # 近似——非IBS通常就是表面
                })

        return sorted(hotspots, key=lambda x: x["mutation_potential"], reverse=True)[:10]

    # ========================
    # 设计潜力评分
    # ========================
    def _compute_design_potential(self, sequence: str,
                                    result: AFPAnalysisResult) -> float:
        """计算设计潜力评分（0-1）"""
        score = 0.0

        # 1. 类型明确性
        score += result.type_confidence * 0.2

        # 2. IBS清晰度
        if len(result.predicted_ibs_positions) >= 2:
            score += 0.2
        if len(result.predicted_ibs_positions) >= 4:
            score += 0.1

        # 3. 冰结合残基质量
        ibs_quality = 0.0
        for pos in result.predicted_ibs_positions:
            if pos <= len(sequence):
                aa = sequence[pos-1]
                ibs_quality += AA_ICE_BINDING_SCORE.get(aa, 0)
        if result.predicted_ibs_positions:
            ibs_quality /= len(result.predicted_ibs_positions)
            score += max(0, ibs_quality) * 0.2

        # 4. Thr含量（越高越好，但不超过0.15）
        score += min(result.thr_content / 0.15, 1.0) * 0.15

        # 5. 非禁区残留多（可安全突变的残基比例高）
        safe_pct = 1 - len(result.forbidden_positions) / max(len(sequence), 1)
        score += safe_pct * 0.15

        return min(score, 1.0)

    # ========================
    # 活性预测
    # ========================
    def _estimate_th(self, sequence: str, result: AFPAnalysisResult) -> float:
        """粗略TH活性估计"""
        n_ibs = len(result.predicted_ibs_positions)
        thr_count = sequence.count('T')
        cys_count = sequence.count('C')

        base_th = 0.0

        # IBS残基数量因子
        if n_ibs <= 4:
            n_factor = 0.5  # 鱼源规模
        elif n_ibs <= 20:
            n_factor = 1.5
        else:
            n_factor = 3.0  # 昆虫超活性规模

        # 刚性支架因子
        rigid_factor = 2.0 if (cys_count >= 4 and cys_count % 2 == 0) else 1.0

        # Thr间距匹配度
        spacing_factor = 1.0
        if self._has_regular_thr_spacing(sequence):
            spacing_factor = 1.5

        base_th = 0.1 * n_factor * rigid_factor * spacing_factor
        base_th *= (thr_count / max(len(sequence), 1)) / 0.05  # 归一化

        return min(7.0, round(base_th, 2))

    def _estimate_iri(self, sequence: str, result: AFPAnalysisResult) -> float:
        """粗略IRI活性估计"""
        n_ibs = len(result.predicted_ibs_positions)

        # 基于de novo iTHR数据和野生型AFP数据的经验公式
        # IRI_Ci ≈ 50 * exp(-3.5 * geometry_score) * exp(-0.05 * n_ibs)
        geometry_score = result.design_potential_score

        iri = 50.0 * math.exp(-3.5 * geometry_score)
        iri *= math.exp(-0.05 * max(n_ibs, 1))

        return max(0.1, round(iri, 2))

    def _estimate_expression(self, sequence: str) -> float:
        """预估表达可溶性（0-1）"""
        gravy = self._compute_gravy(sequence)
        # 越亲水越可能可溶表达
        score = 1.0 / (1.0 + math.exp(gravy * 2))  # sigmoid

        # Ala含量高有助于表达
        ala_pct = sequence.count('A') / max(len(sequence), 1)
        score += ala_pct * 0.15

        # 过长/过短不利于表达
        length = len(sequence)
        if 30 <= length <= 300:
            score += 0.1
        elif length < 30:
            score -= 0.1

        return max(0.0, min(1.0, score))

    def _estimate_stability(self, sequence: str) -> float:
        """预估热稳定性（0-1）"""
        ii = self._compute_instability_index(sequence)
        # 不稳定指数<40表示稳定
        stability = max(0, 1 - ii / 100)

        # Cys二硫键加分
        cys_count = sequence.count('C')
        if cys_count >= 4 and cys_count % 2 == 0:
            stability += 0.25

        # Pro增加刚性
        stability += sequence.count('P') / max(len(sequence), 1) * 5

        return max(0.0, min(1.0, stability))

    def compare_sequences(self, original: AFPAnalysisResult,
                          mutated: AFPAnalysisResult) -> Dict:
        """对比两个序列的分析结果"""
        return {
            "th_change": {
                "original": original.estimated_th,
                "mutated": mutated.estimated_th,
                "change_pct": self._pct_change(original.estimated_th,
                                                mutated.estimated_th)
            },
            "iri_change": {
                "original": original.estimated_iri_ic50,
                "mutated": mutated.estimated_iri_ic50,
                "change_pct": self._pct_change(original.estimated_iri_ic50,
                                                mutated.estimated_iri_ic50)
            },
            "stability_change": {
                "original": original.estimated_stability_score,
                "mutated": mutated.estimated_stability_score,
            },
            "expression_change": {
                "original": original.estimated_expression_score,
                "mutated": mutated.estimated_expression_score,
            },
            "design_potential_change": {
                "original": original.design_potential_score,
                "mutated": mutated.design_potential_score,
            },
        }

    @staticmethod
    def _pct_change(old: float, new: float) -> float:
        """计算百分比变化"""
        if old == 0:
            return 100.0 if new > 0 else 0.0
        return round((new - old) / old * 100, 2)
