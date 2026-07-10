"""
轻量级蛋白质结构预测器

基于 Chou-Fasman 倾向性 + AFP 特异性启发式规则，
在毫秒级完成二级结构预测，无需 GPU。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
import math


# ============================================================
# Chou-Fasman 二级结构倾向性参数 (经典)
# ============================================================
# P(a) = alpha-helix propensity
# P(b) = beta-sheet propensity
# P(t) = beta-turn propensity

CF_HELIX_PROPENSITY = {
    'A': 1.42, 'C': 0.70, 'D': 1.01, 'E': 1.51, 'F': 1.13,
    'G': 0.57, 'H': 1.00, 'I': 1.08, 'K': 1.16, 'L': 1.21,
    'M': 1.45, 'N': 0.67, 'P': 0.57, 'Q': 1.11, 'R': 0.98,
    'S': 0.77, 'T': 0.83, 'V': 1.06, 'W': 1.08, 'Y': 0.69,
}

CF_SHEET_PROPENSITY = {
    'A': 0.83, 'C': 1.19, 'D': 0.54, 'E': 0.37, 'F': 1.38,
    'G': 0.75, 'H': 0.87, 'I': 1.60, 'K': 0.74, 'L': 1.30,
    'M': 1.05, 'N': 0.89, 'P': 0.55, 'Q': 1.10, 'R': 0.93,
    'S': 0.75, 'T': 1.19, 'V': 1.70, 'W': 1.37, 'Y': 1.47,
}

CF_TURN_PROPENSITY = {
    'A': 0.66, 'C': 1.19, 'D': 1.46, 'E': 0.74, 'F': 0.60,
    'G': 1.56, 'H': 0.95, 'I': 0.47, 'K': 1.01, 'L': 0.59,
    'M': 0.60, 'N': 1.56, 'P': 1.52, 'Q': 0.98, 'R': 0.95,
    'S': 1.43, 'T': 0.96, 'V': 0.50, 'W': 0.96, 'Y': 1.14,
}

# Chou-Fasman positional turn preferences (f(i), f(i+1), f(i+2), f(i+3))
CF_TURN_POSITIONAL = {
    # f(i): position 1 preference
    'f_i':   {'D': 0.147, 'N': 0.161, 'S': 0.120, 'P': 0.102, 'G': 0.102, 'T': 0.086, 'H': 0.068},
    # f(i+1): position 2 preference
    'f_i1':  {'P': 0.301, 'S': 0.139, 'T': 0.125, 'K': 0.103, 'D': 0.105, 'N': 0.081, 'G': 0.081},
    # f(i+2): position 3 preference
    'f_i2':  {'D': 0.190, 'N': 0.179, 'G': 0.190, 'S': 0.125, 'T': 0.107, 'K': 0.072},
    # f(i+3): position 4 preference
    'f_i3':  {'G': 0.126, 'W': 0.095, 'C': 0.068, 'S': 0.106, 'N': 0.091, 'K': 0.065},
}

# Helix capping preferences
N_CAP_PREFERENCE = {'S': 1.45, 'T': 1.35, 'N': 1.40, 'D': 1.55, 'G': 1.10, 'P': 0.90}
C_CAP_PREFERENCE = {'G': 1.80, 'N': 1.20, 'S': 1.20, 'K': 0.80, 'R': 0.80}

# Ice-binding surface indicator residues
IBS_INDICATOR_RESIDUES = {'T', 'N', 'Q', 'S', 'A'}
IBS_STRONG_RESIDUES = {'T', 'N'}
IBS_FORBIDDEN_RESIDUES = {'D', 'E', 'K', 'R', 'F', 'W', 'Y'}

# Known AFP fold signatures
AFP_FOLD_SIGNATURES = {
    'type_i_helix': {
        'name': 'Type I AFP (Amphipathic α-helix)',
        'ala_threshold': 0.45,      # Ala > 45%
        'thr_spacing': [11, 11, 11],  # 11-residue repeat
        'min_length': 30,
    },
    'type_ii_lectin': {
        'name': 'Type II AFP (C-type Lectin)',
        'cys_threshold': 5,         # 5 disulfide bonds
        'size_range': (120, 160),
    },
    'type_iii_sandwich': {
        'name': 'Type III AFP (β-Sandwich)',
        'size_range': (60, 70),
        'key_motif': ['N', 'T', 'Q'],  # N14-T18-Q44 cluster
    },
    'insect_hyperactive': {
        'name': 'Insect Hyperactive AFP (β-Helix)',
        'txt_motif': True,
        'cys_content': 0.04,
    },
}


@dataclass
class ResidueAnnotation:
    """Per-residue structural annotation"""
    position: int
    amino_acid: str
    ss_type: str           # 'H'=helix, 'E'=sheet, 'T'=turn, 'C'=coil
    ss_confidence: float   # 0-1
    ibs_candidate: bool    # potential ice-binding surface residue
    ibs_confidence: float  # 0-1
    solvent_accessibility: str  # 'buried', 'exposed', 'surface'


@dataclass
class StructurePrediction:
    """Complete structure prediction result"""
    sequence: str
    sequence_length: int

    # Secondary structure
    residues: List[ResidueAnnotation] = field(default_factory=list)
    ss_composition: Dict[str, float] = field(default_factory=dict)  # H%/E%/T%/C%
    ss_consensus: str = ""  # full-length SS string (e.g., "HHHHHHTTCCEEEEE...")

    # Fold prediction
    predicted_fold: str = ""
    fold_confidence: float = 0.0
    matching_afp_type: Optional[str] = None

    # Ice-binding surface
    ibs_positions: List[int] = field(default_factory=list)
    ibs_flatness_score: float = 0.0
    ibs_thr_spacing: List[float] = field(default_factory=list)

    # Physicochemical
    ala_content: float = 0.0
    thr_content: float = 0.0
    cys_content: float = 0.0
    net_charge: float = 0.0
    hydrophobicity: float = 0.0  # GRAVY

    # Summary
    structural_highlights: List[str] = field(default_factory=list)
    design_notes: List[str] = field(default_factory=list)


class LightweightStructurePredictor:
    """
    轻量级蛋白质结构预测器

    算法：Chou-Fasman 二级结构预测 + AFP 特异性结构推断
    性能：毫秒级 / 任意长度序列，纯 CPU
    """

    # Chou-Fasman thresholds
    HELIX_WINDOW = 6      # nucleation window
    SHEET_WINDOW = 5
    HELIX_EXTEND = 4      # extension residues
    SHEET_EXTEND = 4
    PA_HELIX_CUTOFF = 1.03
    PB_SHEET_CUTOFF = 1.05
    PT_AVG_CUTOFF = 1.00
    PT_POSITIONAL_THRESHOLD = 0.075

    def predict(self, sequence: str) -> StructurePrediction:
        """主预测入口"""
        seq = sequence.upper().strip()
        if not seq:
            raise ValueError("Empty sequence")

        result = StructurePrediction(
            sequence=seq,
            sequence_length=len(seq),
        )

        # Step 1: Chou-Fasman secondary structure
        ss_raw = self._chou_fasman_predict(seq)
        ss_smoothed = self._smooth_boundaries(ss_raw, seq)

        # Step 2: Per-residue annotation
        result.residues = self._annotate_residues(seq, ss_smoothed)
        result.ss_consensus = ''.join(r.ss_type for r in result.residues)

        # Step 3: SS composition
        result.ss_composition = self._compute_ss_composition(result.residues)

        # Step 4: Fold identification
        fold_info = self._identify_fold(seq, result.residues)
        result.predicted_fold = fold_info['name']
        result.fold_confidence = fold_info['confidence']
        result.matching_afp_type = fold_info.get('afp_type')

        # Step 5: Ice-binding surface prediction
        ibs_info = self._predict_ice_binding_surface(seq, result.residues)
        result.ibs_positions = ibs_info['positions']
        result.ibs_flatness_score = ibs_info['flatness']
        result.ibs_thr_spacing = ibs_info['thr_distances']

        # Step 6: Physicochemical properties
        result.ala_content = seq.count('A') / len(seq)
        result.thr_content = seq.count('T') / len(seq)
        result.cys_content = seq.count('C') / len(seq)
        result.net_charge = self._compute_net_charge(seq)
        result.hydrophobicity = self._compute_gravy(seq)

        # Step 7: Highlights and design notes
        result.structural_highlights = self._generate_highlights(seq, result)
        result.design_notes = self._generate_design_notes(seq, result)

        return result

    # ================================================================
    # Chou-Fasman algorithm
    # ================================================================

    def _chou_fasman_predict(self, seq: str) -> List[str]:
        """Chou-Fasman secondary structure prediction"""
        n = len(seq)
        raw_ss = ['C'] * n  # default: coil

        # Compute per-residue propensities
        pa = [CF_HELIX_PROPENSITY.get(aa, 1.0) for aa in seq]
        pb = [CF_SHEET_PROPENSITY.get(aa, 1.0) for aa in seq]
        pt = [CF_TURN_PROPENSITY.get(aa, 1.0) for aa in seq]

        # --- Turn prediction (highest priority) ---
        for i in range(n - 3):
            # Positional turn probability
            pos_score = (
                CF_TURN_POSITIONAL['f_i'].get(seq[i], 0) +
                CF_TURN_POSITIONAL['f_i1'].get(seq[i + 1], 0) +
                CF_TURN_POSITIONAL['f_i2'].get(seq[i + 2], 0) +
                CF_TURN_POSITIONAL['f_i3'].get(seq[i + 3], 0)
            )
            avg_pt = (pt[i] + pt[i + 1] + pt[i + 2] + pt[i + 3]) / 4.0
            avg_pa4 = (pa[i] + pa[i + 1] + pa[i + 2] + pa[i + 3]) / 4.0
            avg_pb4 = (pb[i] + pb[i + 1] + pb[i + 2] + pb[i + 3]) / 4.0

            if (avg_pt > self.PT_AVG_CUTOFF and
                avg_pt > avg_pa4 and
                avg_pt > avg_pb4 and
                pos_score > self.PT_POSITIONAL_THRESHOLD):
                raw_ss[i] = 'T'
                raw_ss[i + 1] = 'T'
                raw_ss[i + 2] = 'T'
                raw_ss[i + 3] = 'T'

        # --- Helix nucleation ---
        helix_flags = [False] * n
        i = 0
        while i <= n - self.HELIX_WINDOW:
            window_pa = pa[i:i + self.HELIX_WINDOW]
            window_pb = pb[i:i + self.HELIX_WINDOW]
            avg_pa_w = sum(window_pa) / self.HELIX_WINDOW
            avg_pb_w = sum(window_pb) / self.HELIX_WINDOW

            if avg_pa_w >= self.PA_HELIX_CUTOFF and avg_pa_w > avg_pb_w:
                # Nucleate helix
                for j in range(i, i + self.HELIX_WINDOW):
                    if raw_ss[j] != 'T':
                        helix_flags[j] = True
                # Extend in both directions
                # Left extension
                left = i - 1
                left_count = 0
                while left >= 0 and left_count < self.HELIX_EXTEND:
                    if raw_ss[left] == 'T':
                        break
                    sub_pa = pa[max(0, left - 3):left + 1]
                    if sum(sub_pa) / len(sub_pa) >= self.PA_HELIX_CUTOFF:
                        helix_flags[left] = True
                        left -= 1
                        left_count += 1
                    else:
                        break
                # Right extension
                right = i + self.HELIX_WINDOW
                right_count = 0
                while right < n and right_count < self.HELIX_EXTEND:
                    if raw_ss[right] == 'T':
                        break
                    sub_pa = pa[right:min(n, right + 4)]
                    if sum(sub_pa) / len(sub_pa) >= self.PA_HELIX_CUTOFF:
                        helix_flags[right] = True
                        right += 1
                        right_count += 1
                    else:
                        break
                i = right
            else:
                i += 1

        # --- Sheet nucleation ---
        i = 0
        while i <= n - self.SHEET_WINDOW:
            window_pb = pb[i:i + self.SHEET_WINDOW]
            window_pa = pa[i:i + self.SHEET_WINDOW]
            avg_pb_w = sum(window_pb) / self.SHEET_WINDOW
            avg_pa_w = sum(window_pa) / self.SHEET_WINDOW

            if avg_pb_w >= self.PB_SHEET_CUTOFF and avg_pb_w > avg_pa_w:
                for j in range(i, i + self.SHEET_WINDOW):
                    if raw_ss[j] != 'T' and not helix_flags[j]:
                        raw_ss[j] = 'E'
                # Extend
                left = i - 1
                left_count = 0
                while left >= 0 and left_count < self.SHEET_EXTEND:
                    if raw_ss[left] == 'T' or helix_flags[left]:
                        break
                    sub_pb = pb[max(0, left - 3):left + 1]
                    if sum(sub_pb) / len(sub_pb) >= self.PB_SHEET_CUTOFF:
                        raw_ss[left] = 'E'
                        left -= 1
                        left_count += 1
                    else:
                        break
                right = i + self.SHEET_WINDOW
                right_count = 0
                while right < n and right_count < self.SHEET_EXTEND:
                    if raw_ss[right] == 'T' or helix_flags[right]:
                        break
                    sub_pb = pb[right:min(n, right + 4)]
                    if sum(sub_pb) / len(sub_pb) >= self.PB_SHEET_CUTOFF:
                        raw_ss[right] = 'E'
                        right += 1
                        right_count += 1
                    else:
                        break
                i = right
            else:
                i += 1

        # Apply helix flags (after sheet to avoid conflicts)
        for i in range(n):
            if helix_flags[i] and raw_ss[i] not in ('T', 'E'):
                raw_ss[i] = 'H'

        return raw_ss

    def _smooth_boundaries(self, ss: List[str], seq: str) -> List[str]:
        """Smooth SS boundaries and resolve isolated residues"""
        n = len(ss)
        smoothed = list(ss)

        # Fix isolated helix residues (single H between non-H)
        for i in range(1, n - 1):
            if smoothed[i] == 'H' and smoothed[i - 1] != 'H' and smoothed[i + 1] != 'H':
                smoothed[i] = 'C'
        # Fix isolated sheet residues
        for i in range(1, n - 1):
            if smoothed[i] == 'E' and smoothed[i - 1] != 'E' and smoothed[i + 1] != 'E':
                smoothed[i] = 'C'

        # Merge short segments
        self._merge_short_segments(smoothed, 'H', 3)
        self._merge_short_segments(smoothed, 'E', 2)

        # Pro/Gly-rich regions = loops
        for i in range(n):
            if seq[i] == 'P':
                smoothed[i] = 'T'  # Proline = turn/loop
            if i < n - 1 and seq[i] == 'G' and seq[i + 1] == 'G':
                if smoothed[i] not in ('T',): smoothed[i] = 'C'
                if smoothed[i + 1] not in ('T',): smoothed[i + 1] = 'C'

        return smoothed

    def _merge_short_segments(self, ss: List[str], target: str, min_len: int):
        """Merge segments shorter than min_len into coil"""
        n = len(ss)
        i = 0
        while i < n:
            if ss[i] == target:
                start = i
                while i < n and ss[i] == target:
                    i += 1
                length = i - start
                if length < min_len:
                    for j in range(start, i):
                        ss[j] = 'C'
            else:
                i += 1

    # ================================================================
    # Annotation
    # ================================================================

    def _annotate_residues(self, seq: str, ss: List[str]) -> List[ResidueAnnotation]:
        """Generate per-residue annotations"""
        annotations = []
        ibs_positions = set(self._find_ibs_positions(seq))

        for i, (aa, sstype) in enumerate(zip(seq, ss)):
            pos = i + 1

            # SS confidence
            pa = CF_HELIX_PROPENSITY.get(aa, 1.0)
            pb = CF_SHEET_PROPENSITY.get(aa, 1.0)
            if sstype == 'H':
                conf = min(1.0, pa / 1.5)
            elif sstype == 'E':
                conf = min(1.0, pb / 1.5)
            elif sstype == 'T':
                conf = 0.6
            else:
                conf = 0.4

            # IBS assessment
            ibs = pos in ibs_positions
            if aa in IBS_STRONG_RESIDUES:
                ibs_conf = 0.85
            elif aa in IBS_INDICATOR_RESIDUES:
                ibs_conf = 0.55
            elif aa in IBS_FORBIDDEN_RESIDUES:
                ibs_conf = 0.05
                ibs = False
            else:
                ibs_conf = 0.25

            # Solvent accessibility heuristic
            if aa in {'A', 'V', 'I', 'L', 'F', 'W', 'Y', 'M', 'C'}:
                solv = 'buried'
            elif aa in {'K', 'R', 'D', 'E', 'N', 'Q'}:
                solv = 'exposed'
            else:
                solv = 'surface'

            annotations.append(ResidueAnnotation(
                position=pos,
                amino_acid=aa,
                ss_type=sstype,
                ss_confidence=round(conf, 3),
                ibs_candidate=ibs,
                ibs_confidence=round(ibs_conf, 3),
                solvent_accessibility=solv,
            ))

        return annotations

    def _find_ibs_positions(self, seq: str) -> List[int]:
        """Identify potential ice-binding surface positions"""
        positions = []
        for i, aa in enumerate(seq):
            pos = i + 1
            if aa in IBS_STRONG_RESIDUES:
                positions.append(pos)
            elif aa == 'S':
                # Ser near Thr → might participate
                nearby_thr = any(
                    0 <= j < len(seq) and seq[j] == 'T'
                    for j in range(max(0, i - 3), min(len(seq), i + 4))
                )
                if nearby_thr:
                    positions.append(pos)
        return positions

    # ================================================================
    # Fold identification
    # ================================================================

    def _identify_fold(self, seq: str, residues: List[ResidueAnnotation]) -> dict:
        """Identify the most likely protein fold / AFP type"""
        n = len(seq)
        ala_pct = seq.count('A') / n
        thr_pct = seq.count('T') / n
        cys_pct = seq.count('C') / n

        scores = {}

        # Type I AFP: Ala-rich amphipathic helix
        if ala_pct >= 0.40 and n >= 30:
            score = min(1.0, ala_pct / 0.60) * 0.8 + min(1.0, thr_pct / 0.10) * 0.2
            scores['Type I AFP (Amphipathic α-helix)'] = score

        # Type II AFP: C-type lectin, Cys-rich
        if cys_pct >= 0.04 and 100 <= n <= 170:
            score = min(1.0, cys_pct / 0.07) * 0.7
            scores['Type II AFP (C-type Lectin)'] = score

        # Type III AFP: small β-sandwich
        if 55 <= n <= 75:
            h_pct = sum(1 for r in residues if r.ss_type == 'H') / n
            e_pct = sum(1 for r in residues if r.ss_type == 'E') / n
            if e_pct > 0.15:
                scores['Type III AFP (β-Sandwich)'] = 0.7

        # Insect hyperactive: TXT motifs
        txt_count = sum(1 for i in range(n - 2)
                       if seq[i] == 'T' and seq[i + 2] == 'T')
        if txt_count >= 2 and cys_pct >= 0.03:
            score = min(1.0, txt_count / 10) * 0.7 + min(1.0, cys_pct / 0.06) * 0.3
            scores['Insect Hyperactive AFP (β-Helix)'] = score

        # General fold classification
        h_pct = sum(1 for r in residues if r.ss_type == 'H') / n
        e_pct = sum(1 for r in residues if r.ss_type == 'E') / n

        if h_pct > 0.30:
            fold = 'All-α Helical'
        elif e_pct > 0.25:
            fold = 'β-Sheet Rich'
        elif h_pct > 0.15 and e_pct > 0.15:
            fold = 'α/β Mixed'
        else:
            fold = 'Coil / Disordered'

        # Pick best AFP match
        if scores:
            best_match = max(scores, key=scores.get)
            best_score = scores[best_match]
            return {
                'name': best_match,
                'confidence': round(best_score, 3),
                'afp_type': best_match,
            }

        return {
            'name': fold,
            'confidence': 0.5,
            'afp_type': None,
        }

    # ================================================================
    # Ice-binding surface prediction
    # ================================================================

    def _predict_ice_binding_surface(self, seq: str, residues: List[ResidueAnnotation]) -> dict:
        """Predict ice-binding surface residues and properties"""
        positions = []
        thr_positions = []

        for r in residues:
            if r.ibs_candidate:
                positions.append(r.position)
            if r.amino_acid == 'T':
                thr_positions.append(r.position)

        # Thr spacing analysis
        thr_dists = []
        for i in range(len(thr_positions) - 1):
            d = thr_positions[i + 1] - thr_positions[i]
            thr_dists.append(round(d * 3.5, 1))  # approximate: 1aa ≈ 3.5Å

        # Flatness assessment
        forbidden_on_surface = sum(
            1 for r in residues
            if r.amino_acid in IBS_FORBIDDEN_RESIDUES and r.ibs_candidate
        )
        flatness = max(0.0, 1.0 - (forbidden_on_surface / max(len(positions), 1)) * 0.8)

        return {
            'positions': positions,
            'flatness': round(flatness, 3),
            'thr_distances': thr_dists,
        }

    # ================================================================
    # Physicochemical
    # ================================================================

    def _compute_net_charge(self, seq: str) -> float:
        """Net charge at pH 7"""
        positive = seq.count('K') + seq.count('R') + seq.count('H') * 0.1
        negative = seq.count('D') + seq.count('E') + seq.count('C') * 0.02
        return positive - negative

    def _compute_gravy(self, seq: str) -> float:
        """Grand Average of Hydropathy (Kyte-Doolittle)"""
        hydropathy = {
            'A': 1.8, 'C': 2.5, 'D': -3.5, 'E': -3.5, 'F': 2.8,
            'G': -0.4, 'H': -3.2, 'I': 4.5, 'K': -3.9, 'L': 3.8,
            'M': 1.9, 'N': -3.5, 'P': -1.6, 'Q': -3.5, 'R': -4.5,
            'S': -0.8, 'T': -0.7, 'V': 4.2, 'W': -0.9, 'Y': -1.3,
        }
        if not seq:
            return 0.0
        return sum(hydropathy.get(aa, 0.0) for aa in seq) / len(seq)

    def _compute_ss_composition(self, residues: List[ResidueAnnotation]) -> Dict[str, float]:
        """Compute SS composition percentages"""
        total = len(residues)
        if total == 0:
            return {}
        counts = {'H': 0, 'E': 0, 'T': 0, 'C': 0}
        for r in residues:
            counts[r.ss_type] = counts.get(r.ss_type, 0) + 1
        return {k: round(v / total, 3) for k, v in counts.items()}

    # ================================================================
    # Highlights
    # ================================================================

    def _generate_highlights(self, seq: str, result: StructurePrediction) -> List[str]:
        """Generate structural highlights"""
        highlights = []
        n = len(seq)

        # Ala content highlight
        if result.ala_content >= 0.45:
            highlights.append(f'Very high Ala content ({result.ala_content:.0%}) — characteristic of Type I AFP')
        elif result.ala_content >= 0.25:
            highlights.append(f'Elevated Ala content ({result.ala_content:.0%})')

        # Thr content
        if result.thr_content >= 0.08:
            highlights.append(f'High Thr content ({result.thr_content:.0%}) — strong ice-binding potential')

        # Cys/disulfide
        if result.cys_content >= 0.04:
            highlights.append(f'Significant Cys content ({result.cys_content:.0%}) — potential disulfide-stabilized scaffold')

        # IBS
        if len(result.ibs_positions) >= 4:
            highlights.append(f'{len(result.ibs_positions)} potential ice-binding residues identified')
        elif len(result.ibs_positions) >= 2:
            highlights.append(f'{len(result.ibs_positions)} ice-binding candidates — consider enriching Thr')

        # SS highlights
        h_pct = result.ss_composition.get('H', 0)
        e_pct = result.ss_composition.get('E', 0)
        if h_pct > 0.30:
            highlights.append(f'Predominantly α-helical ({h_pct:.0%})')
        if e_pct > 0.20:
            highlights.append(f'Significant β-sheet content ({e_pct:.0%})')

        # Fold
        if result.matching_afp_type:
            highlights.append(f'Matches {result.matching_afp_type}')

        return highlights

    def _generate_design_notes(self, seq: str, result: StructurePrediction) -> List[str]:
        """Generate design recommendations"""
        notes = []
        n = len(seq)

        if result.thr_content < 0.05:
            notes.append('Low Thr content — consider introducing Thr at ice-binding positions')
        if result.cys_content > 0 and result.cys_content % (1 / n) * n != int(result.cys_content * n) % 2 == 1:
            # Odd number of Cys — potential unpaired
            if int(result.cys_content * n) % 2 == 1:
                notes.append('Odd number of Cys residues — may have unpaired disulfide')

        if len(result.ibs_positions) < 3:
            notes.append('Limited ice-binding surface — consider Thr-enrichment at solvent-exposed positions')

        forbidden_on_ibs = sum(
            1 for r in result.residues
            if r.ibs_candidate and r.amino_acid in IBS_FORBIDDEN_RESIDUES
        )
        if forbidden_on_ibs > 0:
            notes.append(f'{forbidden_on_ibs} charged/bulky residues on predicted IBS — may disrupt ice binding')

        return notes


# Singleton
_predictor: Optional[LightweightStructurePredictor] = None


def get_structure_predictor() -> LightweightStructurePredictor:
    global _predictor
    if _predictor is None:
        _predictor = LightweightStructurePredictor()
    return _predictor
