"""
AFPKnowledgeBase - 抗冻蛋白综合知识查询与分析引擎

Integrates the motif library and literature knowledge to provide a unified
sequence analysis pipeline. Given an amino acid sequence and optional
application scenario, it annotates motifs, identifies ice-binding surface
residues, flags forbidden mutation regions, matches literature findings,
generates ranked mutation candidates, and applies scenario-specific requirements.

The output is structured as an AFPKnowledgeQuery dataclass suitable for both
programmatic consumption and LLM prompt formatting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .motifs import AFPMotifLibrary, IceBindingMotif
from .literature import AFPLiteratureKnowledge, MutationFinding, DesignPrinciple


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class AFPKnowledgeQuery:
    """Complete analytical result for one AFP sequence query.

    Attributes
    ----------
    sequence : str
        Input amino acid sequence.
    afp_type_prediction : str
        Predicted AFP type classification.
    confidence : float
        Confidence score 0–1 for the type prediction.
    matched_motifs : list
        Motif IDs (str) that matched this sequence.
    ibs_residues_identified : list
        Residue positions predicted as ice-binding surface residues.
    mutation_candidates : List[dict]
        Each entry: {"position", "from_aa", "suggested_aa", "rationale"}.
    forbidden_regions : List[dict]
        Each entry: {"position", "from_aa", "reason"}.
    design_principles_matched : List[dict]
        Each entry: {"principle_id", "category", "title", "rule", "relevance"}.
    literature_findings_matched : List[dict]
        Each entry: {"source_protein", "mutation", "mechanism", "relevance"}.
    application_recommendations : dict
        Scenario-specific recommendations if an application was specified.
    """

    sequence: str
    afp_type_prediction: str = "unknown"
    confidence: float = 0.0
    matched_motifs: List[str] = field(default_factory=list)
    ibs_residues_identified: List[Dict[str, Any]] = field(default_factory=list)
    mutation_candidates: List[Dict[str, Any]] = field(default_factory=list)
    forbidden_regions: List[Dict[str, Any]] = field(default_factory=list)
    design_principles_matched: List[Dict[str, Any]] = field(default_factory=list)
    literature_findings_matched: List[Dict[str, Any]] = field(default_factory=list)
    application_recommendations: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Knowledge Base Engine
# ---------------------------------------------------------------------------

class AFPKnowledgeBase:
    """Unified query engine combining motif and literature knowledge.

    Usage
    -----
    >>> kb = AFPKnowledgeBase()
    >>> result = kb.analyze_sequence("DTASDAAAAAAL...", application_scenario="ice_cream")
    >>> text = kb.get_reference_for_llm(result)
    """

    def __init__(
        self,
        motif_library: Optional[AFPMotifLibrary] = None,
        literature_knowledge: Optional[AFPLiteratureKnowledge] = None,
    ) -> None:
        """Initialize with optional pre-built components.

        Parameters
        ----------
        motif_library : AFPMotifLibrary, optional
            Motif database instance. Created fresh if not provided.
        literature_knowledge : AFPLiteratureKnowledge, optional
            Literature database instance. Created fresh if not provided.
        """
        self.motif_library = motif_library or AFPMotifLibrary()
        self.literature = literature_knowledge or AFPLiteratureKnowledge()

    # ------------------------------------------------------------------
    # Main analysis pipeline
    # ------------------------------------------------------------------

    def analyze_sequence(
        self,
        sequence: str,
        application_scenario: str = "general",
    ) -> AFPKnowledgeQuery:
        """Comprehensive sequence analysis: annotate, flag, match, recommend.

        Parameters
        ----------
        sequence : str
            Amino acid sequence (uppercase one-letter codes).
        application_scenario : str
            Target application, e.g. "ice_cream", "cell_cryo", "organ_preservation",
            "anti_ice_coating", "frozen_dough", "meat_preservation". Default is
            "general" (balanced weights).

        Returns
        -------
        AFPKnowledgeQuery
            Complete analysis result.
        """
        seq = sequence.strip().upper()

        result = AFPKnowledgeQuery(sequence=seq)

        # --- Step 1: Predict AFP type from sequence features ---
        afp_type, confidence = self._predict_afp_type(seq)
        result.afp_type_prediction = afp_type
        result.confidence = confidence

        # --- Step 2: Match motifs ---
        matched = self._match_motifs(seq)
        result.matched_motifs = [m.motif_id for m in matched]

        # --- Step 3: Identify IBS residues ---
        result.ibs_residues_identified = self._identify_ibs_residues(seq, matched)

        # --- Step 4: Flag forbidden regions ---
        forbidden = self.motif_library.get_forbidden_mutations(seq, matched)
        result.forbidden_regions = [
            {"position": f["position"], "from_aa": f["from_aa"], "reason": f["reason"]}
            for f in forbidden
        ]

        # --- Step 5: Generate mutation candidates ---
        if application_scenario != "general":
            design_target = self._scenario_to_design_target(application_scenario)
        else:
            design_target = "general"
        result.mutation_candidates = self.motif_library.get_mutation_suggestions(
            seq, design_target, matched,
        )

        # --- Step 6: Match design principles ---
        result.design_principles_matched = self._match_principles(
            seq, matched, application_scenario,
        )

        # --- Step 7: Match literature findings ---
        result.literature_findings_matched = self._match_literature(seq, matched)

        # --- Step 8: Application recommendations ---
        if application_scenario != "general":
            app_reqs = self.literature.get_requirements_for_application(
                application_scenario,
            )
            if app_reqs:
                result.application_recommendations = {
                    "scenario": application_scenario,
                    "description": app_reqs.get("description", ""),
                    "th_weight": app_reqs.get("th_weight", 0.5),
                    "iri_weight": app_reqs.get("iri_weight", 0.5),
                    "stability_weight": app_reqs.get("stability_weight", 0.5),
                    "safety_requirements": app_reqs.get("safety_requirements", ""),
                    "expression_level_needs": app_reqs.get("expression_level_needs", ""),
                    "target_concentration": app_reqs.get("target_concentration", ""),
                    "key_considerations": app_reqs.get("key_considerations", []),
                    "recommended_strategy": self._generate_strategy(
                        seq, matched, app_reqs,
                    ),
                }

        return result

    # ------------------------------------------------------------------
    # Internal analysis helpers
    # ------------------------------------------------------------------

    def _predict_afp_type(self, sequence: str) -> Tuple[str, float]:
        """Heuristic AFP type prediction from sequence composition.

        Returns (type_name, confidence 0–1).
        """
        seq = sequence.upper()
        n = len(seq)

        if n == 0:
            return "unknown", 0.0

        # Count key residues
        ala_pct = seq.count("A") / n
        thr_pct = seq.count("T") / n
        cys_pct = seq.count("C") / n
        gly_pct = seq.count("G") / n
        asn_pct = seq.count("N") / n
        ala_plus_gly = ala_pct + gly_pct

        # Check for Thr periodic patterns
        thr_spacing = self._detect_thr_periodicity(seq)

        # --- AFGP: high A+T, low other residues ---
        if ala_pct + thr_pct > 0.6 and cys_pct < 0.02:
            return "afgp", 0.7

        # --- Insect hyperactive: Cys-rich + Thr + TXT pattern ---
        if cys_pct > 0.08 and "TXT" in self._extract_triplets(seq):
            return "insect_hyper", 0.85

        # --- Type I: Ala >50%, Thr ~8%, α-helical ---
        if ala_pct > 0.45 and thr_pct > 0.05 and cys_pct < 0.05:
            if thr_spacing and 10 <= thr_spacing <= 12:
                return "type_i", 0.80
            return "type_i", 0.60

        # --- Type III: moderate Ala, globular pattern ---
        if 0.15 < ala_pct < 0.35 and thr_pct > 0.03 and asn_pct > 0.03:
            return "type_iii", 0.55

        # --- Plant: moderate Thr+Asn, NXT/NXS patterns ---
        if asn_pct > 0.05 and thr_pct > 0.08 and cys_pct < 0.03:
            return "plant", 0.65

        # --- Bacterial: Gly-rich, moderate everything ---
        if gly_pct > 0.08 and ala_plus_gly > 0.25:
            return "bacterial", 0.50

        # --- De novo: balanced AA composition, engineered look ---
        if ala_pct > 0.20 and thr_pct > 0.06 and gly_pct > 0.05:
            return "de_novo", 0.40

        return "unknown", 0.10

    @staticmethod
    def _extract_triplets(sequence: str) -> str:
        """Extract all overlapping triplets as space-separated string for pattern matching."""
        return " ".join(sequence[i:i + 3] for i in range(len(sequence) - 2))

    @staticmethod
    def _detect_thr_periodicity(sequence: str) -> Optional[int]:
        """Detect the most common Thr-Thr spacing in a sequence.

        Returns the modal spacing, or None if no Thr periodicity detected.
        """
        thr_positions = [i for i, aa in enumerate(sequence) if aa == "T"]
        if len(thr_positions) < 3:
            return None

        spacings = [
            thr_positions[i + 1] - thr_positions[i]
            for i in range(len(thr_positions) - 1)
        ]
        if not spacings:
            return None

        # Find mode
        from collections import Counter
        counter = Counter(spacings)
        mode_spacing, count = counter.most_common(1)[0]

        # Require at least 2 occurrences of the spacing
        if count >= 2:
            return mode_spacing
        return None

    def _match_motifs(self, sequence: str) -> List[IceBindingMotif]:
        """Identify motifs whose patterns are present in the sequence.

        Uses a scoring approach: Thr periodicity, composition, length, and
        specific signature patterns.
        """
        matched: List[IceBindingMotif] = []
        seq = sequence.upper()
        n = len(seq)

        ala_pct = seq.count("A") / max(n, 1)
        thr_pct = seq.count("T") / max(n, 1)
        cys_pct = seq.count("C") / max(n, 1)
        thr_spacing = self._detect_thr_periodicity(seq)

        for motif in self.motif_library.get_all_motifs():
            score = 0.0

            # Thr periodicity match
            if thr_spacing is not None and motif.repeat_length > 0:
                if abs(thr_spacing - motif.repeat_length) <= 1:
                    score += 0.3
                elif abs(thr_spacing - motif.repeat_length) <= 2:
                    score += 0.15

            # Composition match
            if motif.afp_type.value == "type_i":
                if ala_pct > 0.40 and thr_pct > 0.04:
                    score += 0.25
            elif motif.afp_type.value == "insect_hyper":
                if cys_pct > 0.05 and thr_pct > 0.15:
                    score += 0.25
            elif motif.afp_type.value == "type_iii":
                if 0.15 < ala_pct < 0.40 and thr_pct > 0.02:
                    score += 0.20
            elif motif.afp_type.value == "plant":
                if seq.count("N") / max(n, 1) > 0.04 and thr_pct > 0.06:
                    score += 0.20
            elif motif.afp_type.value == "bacterial":
                if seq.count("G") / max(n, 1) > 0.06:
                    score += 0.20
            elif motif.afp_type.value == "afgp":
                if ala_pct + thr_pct > 0.55:
                    score += 0.25
            elif motif.afp_type.value == "de_novo":
                if thr_pct > 0.05 and thr_spacing is not None:
                    score += 0.20

            # Length similarity
            motif_len = len(motif.sequence_pattern)
            if motif_len > 0:
                len_ratio = min(n, motif_len) / max(n, motif_len)
                score += len_ratio * 0.15

            # Signature patterns
            if motif.motif_id == "IBS-INSECT-TmAFP" and cys_pct > 0.06:
                triplets = self._extract_triplets(seq)
                if "TCT" in triplets or "TST" in triplets:
                    score += 0.2
            if motif.motif_id == "IBS-TYPE1-HPLC6" and ala_pct > 0.45:
                if thr_spacing and 10 <= thr_spacing <= 12:
                    score += 0.2

            if score >= 0.35:
                matched.append(motif)

        # Sort by score (approximate)
        return matched

    def _identify_ibs_residues(
        self,
        sequence: str,
        matched_motifs: List[IceBindingMotif],
    ) -> List[Dict[str, Any]]:
        """Predict IBS residues by combining motif knowledge with sequence.

        Returns a list of {"position", "residue", "evidence", "confidence"} dicts.
        """
        identified: List[Dict[str, Any]] = []
        seq = sequence.upper()
        n = len(seq)

        # From matched motifs: map known IBS positions
        for motif in matched_motifs:
            for pos in motif.ibs_positions:
                if pos <= n:
                    identified.append({
                        "position": pos,
                        "residue": seq[pos - 1],
                        "evidence": f"Matches {motif.motif_id} IBS residue at position {pos}",
                        "confidence": 0.85,
                    })

        # De novo prediction: all Thr in periodic spacing are candidates
        thr_spacing = self._detect_thr_periodicity(seq)
        if thr_spacing:
            for i, aa in enumerate(seq):
                if aa == "T":
                    pos = i + 1
                    already_identified = any(
                        entry["position"] == pos for entry in identified
                    )
                    if not already_identified:
                        identified.append({
                            "position": pos,
                            "residue": "T",
                            "evidence": f"Thr at periodicity {thr_spacing} — candidate IBS residue",
                            "confidence": 0.55,
                        })

        # De novo prediction: surface-exposed Asn near Thr
        if "N" in seq:
            thr_positions = [j for j, aa in enumerate(seq) if aa == "T"]
            for i, aa in enumerate(seq):
                if aa == "N":
                    pos = i + 1
                    near_thr = any(abs(i - t) <= 2 for t in thr_positions)
                    if near_thr:
                        already_identified = any(
                            entry["position"] == pos for entry in identified
                        )
                        if not already_identified:
                            identified.append({
                                "position": pos,
                                "residue": "N",
                                "evidence": "Asn near Thr — potential plant-type Asn-Thr pair",
                                "confidence": 0.45,
                            })

        # Sort by position
        identified.sort(key=lambda x: x["position"])

        # Deduplicate — keep highest confidence for each position
        seen_positions: Dict[int, Dict[str, Any]] = {}
        for entry in identified:
            pos = entry["position"]
            if pos not in seen_positions or entry["confidence"] > seen_positions[pos]["confidence"]:
                seen_positions[pos] = entry

        return list(seen_positions.values())

    def _match_principles(
        self,
        sequence: str,
        matched_motifs: List[IceBindingMotif],
        application_scenario: str,
    ) -> List[Dict[str, Any]]:
        """Match design principles based on sequence features and scenario."""
        matched: List[Dict[str, Any]] = []

        # Determine which categories to prioritize based on scenario
        app_reqs = self.literature.get_requirements_for_application(
            application_scenario,
        ) if application_scenario != "general" else None

        if app_reqs:
            th_w = app_reqs.get("th_weight", 0.5)
            iri_w = app_reqs.get("iri_weight", 0.5)
            categories_to_search = []
            if th_w >= 0.4:
                categories_to_search.append("TH_OPTIMIZATION")
            if iri_w >= 0.4:
                categories_to_search.append("IRI_OPTIMIZATION")
            categories_to_search.extend(["STABILITY", "EXPRESSION", "SAFETY"])
        else:
            categories_to_search = [
                "TH_OPTIMIZATION", "IRI_OPTIMIZATION", "STABILITY",
                "EXPRESSION", "SAFETY",
            ]

        for category in categories_to_search:
            principles = self.literature.get_principles_for_category(category)
            for p in principles:
                # Check if principle applies to any matched motif type
                motif_types = {m.afp_type.value for m in matched_motifs}
                applies = (
                    not p.applicable_afp_types
                    or any(t in motif_types for t in p.applicable_afp_types)
                )
                if applies or not matched_motifs:
                    matched.append({
                        "principle_id": p.principle_id,
                        "category": p.category,
                        "title": p.title,
                        "rule": p.rule,
                        "relevance": f"evidence: {p.evidence_strength}",
                    })

        return matched

    def _match_literature(
        self,
        sequence: str,
        matched_motifs: List[IceBindingMotif],
    ) -> List[Dict[str, Any]]:
        """Match literature findings relevant to the sequence."""
        findings: List[Dict[str, Any]] = []

        # Match by motif source organisms
        for motif in matched_motifs:
            lit_findings = self.literature.query_by_protein(
                motif.source_organism.split("(")[0].strip(),
            )
            if not lit_findings:
                lit_findings = self.literature.query_by_protein(motif.name)

            for f in lit_findings:
                findings.append({
                    "source_protein": f.source_protein,
                    "mutation": f.mutation,
                    "th_change_pct": f.th_change_pct,
                    "iri_change_pct": f.iri_change_pct,
                    "mechanism": f.mechanism,
                    "relevance": f.relevance_score,
                    "pmid": f.pmid,
                })

        # Also match by sequence content (G→S findings for Gly-rich sequences, etc.)
        if sequence:
            seq = sequence.upper()
            if seq.count("G") / max(len(seq), 1) > 0.05:
                gs_findings = self.literature.query_by_mutation_type("G", "S")
                for f in gs_findings:
                    findings.append({
                        "source_protein": f.source_protein,
                        "mutation": f.mutation,
                        "th_change_pct": f.th_change_pct,
                        "iri_change_pct": f.iri_change_pct,
                        "mechanism": f.mechanism,
                        "relevance": f.relevance_score,
                        "pmid": f.pmid,
                        "note": "Matched by sequence composition (Gly-rich)",
                    })

        # Deduplicate
        seen: set = set()
        unique: List[Dict[str, Any]] = []
        for f in findings:
            key = (f["source_protein"], f["mutation"])
            if key not in seen:
                seen.add(key)
                unique.append(f)

        return unique

    def _scenario_to_design_target(self, scenario: str) -> str:
        """Map an application scenario to the primary design optimization target."""
        app_reqs = self.literature.get_requirements_for_application(scenario)
        if not app_reqs:
            return "general"

        th_w = app_reqs.get("th_weight", 0.5)
        iri_w = app_reqs.get("iri_weight", 0.5)

        if th_w >= 0.7:
            return "TH"
        elif iri_w >= 0.7:
            return "IRI"
        elif th_w > iri_w:
            return "TH"
        else:
            return "IRI"

    def _generate_strategy(
        self,
        sequence: str,
        matched_motifs: List[IceBindingMotif],
        app_reqs: Dict[str, Any],
    ) -> str:
        """Generate a textual strategy recommendation for the application."""
        th_w = app_reqs.get("th_weight", 0.5)
        iri_w = app_reqs.get("iri_weight", 0.5)
        stability_w = app_reqs.get("stability_weight", 0.5)

        parts: List[str] = []

        if th_w >= 0.5:
            parts.append(
                "Prioritize TH optimization: reduce IBS RMSD, verify Thr spacing, "
                "consider adopting hyperactive fold (β-helix) if TH >2 °C is required."
            )
        if iri_w >= 0.5:
            parts.append(
                "Prioritize IRI optimization: maximize IBS surface area, incorporate "
                "Asn-Thr pairs, consider plant-type β-roll or bacterial DUF3494 scaffold."
            )
        if stability_w >= 0.7:
            parts.append(
                "High stability requirement: engineer disulfide bonds, optimize "
                "hydrophobic core packing, add helix-capping residues."
            )

        if not parts:
            parts.append("Balanced optimization of TH, IRI, and stability.")

        return " ".join(parts)

    # ------------------------------------------------------------------
    # LLM Reference Formatter
    # ------------------------------------------------------------------

    def get_reference_for_llm(self, query_result: AFPKnowledgeQuery) -> str:
        """Format the complete query result as a readable text block for LLM prompting.

        Parameters
        ----------
        query_result : AFPKnowledgeQuery
            Result from analyze_sequence().

        Returns
        -------
        str
            Formatted reference text suitable for inclusion in an LLM system prompt
            or RAG context window.
        """
        lines: List[str] = []

        lines.append("=" * 72)
        lines.append("AFP KNOWLEDGE BASE — SEQUENCE ANALYSIS REFERENCE")
        lines.append("=" * 72)
        lines.append("")

        # Input
        lines.append(f"Sequence: {query_result.sequence[:60]}{'...' if len(query_result.sequence) > 60 else ''}")
        lines.append(f"Length: {len(query_result.sequence)} aa")
        lines.append(f"Predicted AFP Type: {query_result.afp_type_prediction} (confidence: {query_result.confidence:.2f})")
        lines.append("")

        # Matched motifs
        if query_result.matched_motifs:
            lines.append("--- MATCHED ICE-BINDING MOTIFS ---")
            for motif_id in query_result.matched_motifs:
                motif = self.motif_library.get_motif(motif_id)
                if motif:
                    lines.append(f"  [{motif_id}] {motif.name}")
                    lines.append(f"    Type: {motif.afp_type.value} | Fold: {motif.fold_family}")
                    lines.append(f"    TH: {motif.th_activity}°C | IRI: {motif.iri_activity} µM")
                    lines.append(f"    Target plane: {motif.target_ice_plane.value}")
                    lines.append(f"    Design rules:")
                    for rule in motif.design_rules:
                        lines.append(f"      • {rule}")
            lines.append("")

        # IBS residues
        if query_result.ibs_residues_identified:
            lines.append("--- IDENTIFIED IBS RESIDUES ---")
            for entry in query_result.ibs_residues_identified:
                lines.append(
                    f"  Position {entry['position']}: {entry['residue']} "
                    f"({entry['evidence']}, confidence={entry['confidence']:.2f})"
                )
            lines.append("")

        # Forbidden regions
        if query_result.forbidden_regions:
            lines.append("--- FORBIDDEN MUTATION REGIONS (EXPERIMENTALLY VERIFIED) ---")
            lines.append("  DO NOT mutate the following — these mutations abolish activity:")
            for entry in query_result.forbidden_regions:
                lines.append(
                    f"  ✗ Position {entry['position']} ({entry['from_aa']}): "
                    f"{entry['reason']}"
                )
            lines.append("")

        # Mutation candidates
        if query_result.mutation_candidates:
            lines.append("--- SUGGESTED MUTATION CANDIDATES ---")
            for i, cand in enumerate(query_result.mutation_candidates, 1):
                lines.append(f"  {i}. {cand.get('position', '?')} | {cand.get('from_aa', '?')}→{cand.get('suggested_aa', '?')}")
                lines.append(f"     Rationale: {cand.get('rationale', '')}")
                lines.append(f"     Expected: {cand.get('expected_effect', '')}")
                lines.append(f"     Confidence: {cand.get('confidence', 'unknown')}")
                if cand.get("reference_motif"):
                    lines.append(f"     Reference: {cand['reference_motif']}")
            lines.append("")

        # Design principles
        if query_result.design_principles_matched:
            lines.append("--- MATCHED DESIGN PRINCIPLES ---")
            by_category: Dict[str, List[Dict[str, Any]]] = {}
            for p in query_result.design_principles_matched:
                by_category.setdefault(p["category"], []).append(p)
            for cat, principles in sorted(by_category.items()):
                lines.append(f"  [{cat}]")
                for p in principles:
                    lines.append(f"    {p['principle_id']}: {p['title']}")
                    lines.append(f"      Rule: {p['rule']}")
                    lines.append(f"      Evidence: {p['relevance']}")
            lines.append("")

        # Literature findings
        if query_result.literature_findings_matched:
            lines.append("--- RELEVANT LITERATURE FINDINGS ---")
            for f in query_result.literature_findings_matched:
                th_str = f"{f['th_change_pct']:+.0f}%" if isinstance(f['th_change_pct'], (int, float)) else str(f['th_change_pct'])
                iri_str = f"{f['iri_change_pct']:+.0f}%" if isinstance(f['iri_change_pct'], (int, float)) else str(f['iri_change_pct'])
                lines.append(f"  {f['mutation']} in {f['source_protein']}")
                lines.append(f"    TH: {th_str} | IRI: {iri_str}")
                lines.append(f"    Mechanism: {f['mechanism']}")
                lines.append(f"    PMID: {f['pmid']} | Relevance: {f['relevance']}/10")
            lines.append("")

        # Application recommendations
        if query_result.application_recommendations:
            app = query_result.application_recommendations
            lines.append("--- APPLICATION-SPECIFIC RECOMMENDATIONS ---")
            lines.append(f"  Scenario: {app.get('scenario', 'unknown')}")
            lines.append(f"  Description: {app.get('description', '')}")
            lines.append(f"  Weights: TH={app.get('th_weight', 0):.1f}, IRI={app.get('iri_weight', 0):.1f}, Stability={app.get('stability_weight', 0):.1f}")
            lines.append(f"  Safety: {app.get('safety_requirements', '')}")
            lines.append(f"  Expression: {app.get('expression_level_needs', '')}")
            lines.append(f"  Target concentration: {app.get('target_concentration', '')}")
            if app.get("key_considerations"):
                lines.append("  Key considerations:")
                for kc in app["key_considerations"]:
                    lines.append(f"    • {kc}")
            if app.get("recommended_strategy"):
                lines.append(f"  Strategy: {app['recommended_strategy']}")
            lines.append("")

        lines.append("=" * 72)
        lines.append("END OF AFP KNOWLEDGE BASE REFERENCE")
        lines.append("=" * 72)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_knowledge_summary(self) -> Dict[str, Any]:
        """Return a summary dictionary with statistics about the knowledge base.

        Returns
        -------
        dict
            Keys: "total_motifs", "motif_types", "total_mutation_findings",
            "total_design_principles", "application_scenarios", "ice_planes_covered".
        """
        all_motifs = self.motif_library.get_all_motifs()

        # Count motif types
        type_counts: Dict[str, int] = {}
        for m in all_motifs:
            t = m.afp_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        # Count principles
        principle_count = sum(
            len(principles)
            for principles in self.literature.DESIGN_PRINCIPLES.values()
        )

        # Ice planes covered
        planes_covered = sorted(set(
            m.target_ice_plane.value for m in all_motifs
        ))

        # PDB entries available
        pdb_count = sum(1 for m in all_motifs if m.pdb_id)

        # Activity ranges
        th_values = [m.th_activity for m in all_motifs if m.th_activity > 0]
        iri_values = [m.iri_activity for m in all_motifs if m.iri_activity > 0]

        return {
            "total_motifs": len(all_motifs),
            "motif_types": type_counts,
            "total_mutation_findings": len(self.literature.MUTATION_FINDINGS),
            "total_design_principles": principle_count,
            "principle_categories": list(self.literature.DESIGN_PRINCIPLES.keys()),
            "application_scenarios": self.literature.list_applications(),
            "ice_planes_covered": planes_covered,
            "pdb_structures_available": pdb_count,
            "th_range_celsius": f"{min(th_values):.1f}–{max(th_values):.1f}" if th_values else "N/A",
            "iri_range_um": f"{min(iri_values):.2f}–{max(iri_values):.1f}" if iri_values else "N/A",
            "hyperactive_motifs": sum(1 for m in all_motifs if m.hyperactivity),
        }
