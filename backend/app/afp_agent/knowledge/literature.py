"""
AFPLiteratureKnowledge - 抗冻蛋白文献知识与设计原则

Aggregates experimentally validated mutation findings, evidence-based design
principles organized by optimization category, and application-specific
requirement mappings for real-world AFP deployment scenarios.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class MutationFinding:
    """A single mutation characterization from the published literature.

    Attributes
    ----------
    source_protein : str
        Name of the protein/motif tested.
    mutation : str
        Mutation descriptor, e.g. "G63S", "T16G/A19G/S22G".
    position : int
        Residue position (for single mutations; primary position for combos).
    from_aa : str
        Original amino acid (one-letter code).
    to_aa : str
        Mutated amino acid (one-letter code).
    th_change_pct : float
        Percentage change in TH activity (positive = gain, negative = loss).
    iri_change_pct : float
        Percentage change in IRI activity.
    stability_change : str
        Qualitative: "increased", "decreased", "unchanged", "not_measured".
    mechanism : str
        Proposed molecular mechanism of the effect.
    relevance_score : float
        0–10 score reflecting importance for protein design.
    pmid : str
        PubMed ID of the primary reference.
    """

    source_protein: str
    mutation: str
    position: int
    from_aa: str
    to_aa: str
    th_change_pct: float
    iri_change_pct: float
    stability_change: str
    mechanism: str
    relevance_score: float
    pmid: str


@dataclass
class DesignPrinciple:
    """An engineering rule distilled from experimental data.

    Attributes
    ----------
    principle_id : str
        Unique ID like "TH-001", "IRI-003".
    category : str
        One of: TH_OPTIMIZATION, IRI_OPTIMIZATION, STABILITY, EXPRESSION, SAFETY.
    title : str
        Short descriptive title.
    rule : str
        Actionable design rule.
    evidence_strength : str
        "strong" (>5 independent studies), "moderate" (2–4), "preliminary" (1).
    applicable_afp_types : List[str]
        Types of AFPs this applies to.
    counter_examples : List[str]
        Known exceptions where this rule does NOT hold.
    pmid_list : List[str]
        Supporting references.
    """

    principle_id: str
    category: str
    title: str
    rule: str
    evidence_strength: str
    applicable_afp_types: List[str] = field(default_factory=list)
    counter_examples: List[str] = field(default_factory=list)
    pmid_list: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Literature Knowledge Base
# ---------------------------------------------------------------------------

class AFPLiteratureKnowledge:
    """Curated AFP literature knowledge: mutations, design principles, and
    application-specific requirement profiles.

    Usage
    -----
    >>> lit = AFPLiteratureKnowledge()
    >>> findings = lit.query_by_protein("MaIBP")
    >>> principles = lit.get_principles_for_category("IRI_OPTIMIZATION")
    >>> reqs = lit.get_requirements_for_application("ice_cream")
    """

    # ------------------------------------------------------------------
    # MUTATION FINDINGS — 10 Key Literature Findings
    # ------------------------------------------------------------------
    MUTATION_FINDINGS: List[MutationFinding] = [
        MutationFinding(
            source_protein="Marinomonas arctica IBP (MaIBP)",
            mutation="G63S",
            position=63,
            from_aa="G",
            to_aa="S",
            th_change_pct=40.0,
            iri_change_pct=40.0,
            stability_change="unchanged",
            mechanism="Addition of Ser hydroxyl group at ice-binding interface provides extra H-bond without disrupting geometry; neutral charge compatible with ice",
            relevance_score=9.5,
            pmid="25313051",
        ),
        MutationFinding(
            source_protein="Marinomonas arctica IBP (MaIBP)",
            mutation="G63D",
            position=63,
            from_aa="G",
            to_aa="D",
            th_change_pct=-100.0,
            iri_change_pct=-100.0,
            stability_change="unchanged",
            mechanism="Aspartate introduces negative charge at ice interface — charge-clathrate incompatibility completely blocks ice binding",
            relevance_score=9.0,
            pmid="25313051",
        ),
        MutationFinding(
            source_protein="Winter Flounder Type I AFP (HPLC6)",
            mutation="T16G/A19G/S22G",
            position=16,
            from_aa="T",
            to_aa="G",
            th_change_pct=128.0,     # >2× gain — rare gain-of-function
            iri_change_pct=128.0,
            stability_change="decreased",
            mechanism="Triple Gly substitution increases helix flexibility, expanding the ice-binding footprint; Ala→Gly allows tighter packing against ice",
            relevance_score=9.0,
            pmid="16446249",
        ),
        MutationFinding(
            source_protein="Ocean Pout Type III AFP (QAE)",
            mutation="Q44T/N14S/T18N",
            position=44,
            from_aa="Q",
            to_aa="T",
            th_change_pct=-100.0,
            iri_change_pct=-100.0,
            stability_change="unchanged",
            mechanism="Triple mutant of the 'catalytic triad' (N14/T18/Q44) completely abolishes ice binding — these three residues form the minimal IBS unit",
            relevance_score=10.0,
            pmid="15608141",
        ),
        MutationFinding(
            source_protein="Ocean Pout Type III AFP (QAE)",
            mutation="A16L",
            position=16,
            from_aa="A",
            to_aa="L",
            th_change_pct=-30.0,
            iri_change_pct=-25.0,
            stability_change="increased",
            mechanism="Larger Leu side chain sterically obstructs IBS flatness — demonstrates importance of small residues (Ala/Gly) at IBS periphery",
            relevance_score=7.0,
            pmid="15608141",
        ),
        MutationFinding(
            source_protein="Winter Flounder Type I AFP (HPLC6)",
            mutation="T2S",
            position=2,
            from_aa="T",
            to_aa="S",
            th_change_pct=-80.0,
            iri_change_pct=-75.0,
            stability_change="unchanged",
            mechanism="Ser hydroxyl is one methylene shorter than Thr — breaks the precise 16.5 Å spacing required for {20-21} pyramidal plane match",
            relevance_score=9.5,
            pmid="16446249",
        ),
        MutationFinding(
            source_protein="Tenebrio molitor Hyperactive AFP",
            mutation="T3A",
            position=3,
            from_aa="T",
            to_aa="A",
            th_change_pct=-95.0,
            iri_change_pct=-90.0,
            stability_change="unchanged",
            mechanism="Individual Thr→Ala on β-helix IBS face destroys cooperative ice binding — hyperactivity requires full Thr array integrity",
            relevance_score=10.0,
            pmid="11909822",
        ),
        MutationFinding(
            source_protein="Tenebrio molitor Hyperactive AFP",
            mutation="C2S",
            position=2,
            from_aa="C",
            to_aa="S",
            th_change_pct=-85.0,
            iri_change_pct=-80.0,
            stability_change="decreased",
            mechanism="Loss of disulfide staple between β-helix coils increases scaffold flexibility, reducing IBS flatness below hyperactivity threshold",
            relevance_score=9.0,
            pmid="14990566",
        ),
        MutationFinding(
            source_protein="Lolium perenne AFP (LpAFP)",
            mutation="N12A/T13A",
            position=12,
            from_aa="N",
            to_aa="A",
            th_change_pct=-90.0,
            iri_change_pct=-85.0,
            stability_change="unchanged",
            mechanism="Asn-Thr pair is the plant AFP ice-binding motif — double Ala mutation removes both amide and hydroxyl H-bond donors simultaneously",
            relevance_score=8.5,
            pmid="16897269",
        ),
        MutationFinding(
            source_protein="Winter Flounder Type I AFP",
            mutation="K18E",
            position=18,
            from_aa="K",
            to_aa="E",
            th_change_pct=-70.0,
            iri_change_pct=-65.0,
            stability_change="decreased",
            mechanism="K18–D22 salt bridge neutralization unfolds the helix C-terminal half at 0 °C — structural integrity prerequisite for ice binding",
            relevance_score=8.0,
            pmid="2251283",
        ),
    ]

    # ------------------------------------------------------------------
    # DESIGN PRINCIPLES — Organized by Category
    # ------------------------------------------------------------------
    DESIGN_PRINCIPLES: Dict[str, List[DesignPrinciple]] = {
        "TH_OPTIMIZATION": [
            DesignPrinciple(
                principle_id="TH-001",
                category="TH_OPTIMIZATION",
                title="Thr Hydroxyl Periodicity Matches Ice Lattice",
                rule="Thr residue spacing must match the repeat distance of oxygen atoms on the target ice plane (±0.5 Å tolerance). For pyramidal {20-21}: 16.5 Å; for basal: 7.4 Å; for prism: 4.5 Å.",
                evidence_strength="strong",
                applicable_afp_types=["type_i", "insect_hyper", "de_novo"],
                counter_examples=[
                    "Bacterial IBPs (MaIBP) bind without strict Thr arrays — use backbone carbonyls instead",
                ],
                pmid_list=["2510190", "10980428", "14990566"],
            ),
            DesignPrinciple(
                principle_id="TH-002",
                category="TH_OPTIMIZATION",
                title="IBS Flatness Determines TH Potency",
                rule="TH activity correlates inversely with IBS RMSD from a perfect plane. RMSD <0.4 Å required for hyperactivity (TH >2 °C); RMSD <0.8 Å for moderate TH (0.3–1.0 °C); RMSD >1.0 Å = negligible TH.",
                evidence_strength="strong",
                applicable_afp_types=["type_i", "type_ii", "type_iii", "insect_hyper", "bacterial", "de_novo"],
                counter_examples=[
                    "AFGPs — disordered coil, moderate TH despite no flat surface; mechanism relies on sugar array",
                ],
                pmid_list=["10980428", "20080629", "14990566"],
            ),
            DesignPrinciple(
                principle_id="TH-003",
                category="TH_OPTIMIZATION",
                title="Scaffold Rigidity Correlates with Hyperactivity",
                rule="Disulfide bonds or extensive H-bond networks that rigidify the protein scaffold are REQUIRED for hyperactivity (TH ≥2 °C). Flexible scaffolds cannot maintain IBS flatness.",
                evidence_strength="strong",
                applicable_afp_types=["insect_hyper", "type_ii"],
                counter_examples=[
                    "Type I AFP — no disulfides, moderate TH; Type III — no disulfides, moderate TH",
                ],
                pmid_list=["11909822", "14990566"],
            ),
            DesignPrinciple(
                principle_id="TH-004",
                category="TH_OPTIMIZATION",
                title="Cooperative Binding Requires ≥4 Repeat Units",
                rule="Hyperactive insect AFPs require at least 4 complete β-helix coils for cooperative ice binding. Fewer coils = proportionate TH loss (~25% per missing coil below 4).",
                evidence_strength="moderate",
                applicable_afp_types=["insect_hyper", "de_novo"],
                counter_examples=[
                    "Type III globular AFPs achieve moderate TH without repeats",
                ],
                pmid_list=["11909822"],
            ),
            DesignPrinciple(
                principle_id="TH-005",
                category="TH_OPTIMIZATION",
                title="Target Basal Plane for Maximum TH",
                rule="Basal plane binders (insect hyperactive AFPs) achieve 5–10× higher TH than prism/pyramidal binders at equivalent concentrations. Redesigning prism binders to target basal plane is the most direct route to hyperactivity.",
                evidence_strength="strong",
                applicable_afp_types=["insect_hyper", "type_i", "type_iii", "de_novo"],
                counter_examples=["No known counter-examples — basal plane binding consistently yields highest TH"],
                pmid_list=["14990566", "20080629"],
            ),
        ],

        "IRI_OPTIMIZATION": [
            DesignPrinciple(
                principle_id="IRI-001",
                category="IRI_OPTIMIZATION",
                title="Asn-Thr Pairs Outperform Lone Thr for IRI",
                rule="Plant AFP-style Asn-Thr/Thr-Asn pairs provide 3–5× greater IRI potency than lone Thr residues because Asn amide side chain contributes additional hydrogen bonds to the ice interface.",
                evidence_strength="strong",
                applicable_afp_types=["plant", "de_novo"],
                counter_examples=["Insect hyperactive AFPs — lone Thr sufficient for high IRI via high binding affinity"],
                pmid_list=["16897269", "15596426"],
            ),
            DesignPrinciple(
                principle_id="IRI-002",
                category="IRI_OPTIMIZATION",
                title="Large IBS Surface Area Enhances IRI",
                rule="IRI improves with total ice-binding surface area. Repeat proteins (β-roll, β-helix, THR) with ≥8 repeat units achieve sub-µM IRI. Globular single-domain AFPs plateau at ~1–5 µM IRI.",
                evidence_strength="moderate",
                applicable_afp_types=["plant", "insect_hyper", "de_novo"],
                counter_examples=["AFGPs — moderate IRI despite extended surface, limited by sugar density"],
                pmid_list=["19836343", "36000001"],
            ),
            DesignPrinciple(
                principle_id="IRI-003",
                category="IRI_OPTIMIZATION",
                title="Bacterial IBP Motif (DUF3494) Offers Portable IRI",
                rule="The DUF3494 Ig-like domain from bacterial IBPs can be fused to other proteins and retains IRI activity. This enables modular IRI engineering — attach DUF3494 to any target protein for ice recrystallization protection.",
                evidence_strength="moderate",
                applicable_afp_types=["bacterial", "de_novo"],
                counter_examples=["Fusion to large (>50 kDa) proteins may sterically hinder ice binding"],
                pmid_list=["22582078", "30290841"],
            ),
        ],

        "STABILITY": [
            DesignPrinciple(
                principle_id="STAB-001",
                category="STABILITY",
                title="Preserve Salt Bridges in Amphipathic Helices",
                rule="Intra-helical salt bridges (e.g., K18–D22 in Type I AFP, spaced i→i+4) contribute 2–3 kcal/mol stabilization and are essential for maintaining amphipathic register at low temperature.",
                evidence_strength="strong",
                applicable_afp_types=["type_i", "de_novo"],
                counter_examples=["Type III uses β-sandwich — relies on hydrophobic core, not salt bridges"],
                pmid_list=["2251283"],
            ),
            DesignPrinciple(
                principle_id="STAB-002",
                category="STABILITY",
                title="Disulfide Staples Essential for β-Helix Integrity",
                rule="Each β-helix coil in insect AFPs is stapled by Cys disulfides. Removing even one disulfide reduces Tm by ≥15 °C and abolishes hyperactivity. Disulfide engineering is a design REQUIREMENT for β-helix-based AFPs.",
                evidence_strength="strong",
                applicable_afp_types=["insect_hyper"],
                counter_examples=["Bacterial DUF3494 — no disulfides, stable via hydrophobic core"],
                pmid_list=["10980428", "14990566"],
            ),
            DesignPrinciple(
                principle_id="STAB-003",
                category="STABILITY",
                title="High Ala Content Requires Proper Helix Capping",
                rule="Ala-rich (>50%) α-helices are marginally stable. N-cap (Ser/Thr/Asn) and C-cap (Gly) residues each contribute 1–2 kcal/mol stabilization. Without caps, helices unfold cooperatively at 0–10 °C.",
                evidence_strength="moderate",
                applicable_afp_types=["type_i", "de_novo"],
                counter_examples=["AFGP PPII helix — Ala-rich but stabilized by glycosylation"],
                pmid_list=["2510190", "16446249"],
            ),
        ],

        "EXPRESSION": [
            DesignPrinciple(
                principle_id="EXP-001",
                category="EXPRESSION",
                title="E. coli Expresses Fish AFPs Poorly — Use Yeast or Tags",
                rule="Fish Type I AFPs (Ala-rich) are toxic to E. coli and form inclusion bodies. Use P. pastoris or MBP/SUMO fusion tags for soluble expression. Codon optimization alone is insufficient.",
                evidence_strength="strong",
                applicable_afp_types=["type_i", "afgp"],
                counter_examples=["Type III AFP expresses well in E. coli — globular, soluble"],
                pmid_list=["15608141"],
            ),
            DesignPrinciple(
                principle_id="EXP-002",
                category="EXPRESSION",
                title="De Novo Designs Have Optimal Codon Usage by Default",
                rule="Computationally designed proteins can use expression-host-optimized codons from the start, bypassing natural codon bias issues. Target CAI ≥0.85 for E. coli, ≥0.75 for yeast.",
                evidence_strength="moderate",
                applicable_afp_types=["de_novo"],
                counter_examples=["Some repetitive de novo designs still cause toxicity due to mRNA secondary structure"],
                pmid_list=["36000001"],
            ),
            DesignPrinciple(
                principle_id="EXP-003",
                category="EXPRESSION",
                title="Secretory Expression Improves Disulfide Formation",
                rule="For disulfide-rich insect AFPs, secretory expression (pelB leader in E. coli, α-factor in yeast) enables oxidative folding. Cytoplasmic expression requires Origami/SHuffle strains and typically yields <50% correctly folded protein.",
                evidence_strength="moderate",
                applicable_afp_types=["insect_hyper", "type_ii"],
                counter_examples=["AFPs without disulfides — cytoplasmic expression is fine"],
                pmid_list=["14990566"],
            ),
        ],

        "SAFETY": [
            DesignPrinciple(
                principle_id="SAFE-001",
                category="SAFETY",
                title="Plant-Derived AFPs Have GRAS Potential for Food",
                rule="Plant AFPs (e.g., LpAFP from ryegrass) are from edible sources and have a clearer path to GRAS status than fish/insect AFPs. Use plant or de novo scaffolds for food applications.",
                evidence_strength="strong",
                applicable_afp_types=["plant"],
                counter_examples=["Some plant proteins are allergenic — screen against allergen databases"],
                pmid_list=["19836343"],
            ),
            DesignPrinciple(
                principle_id="SAFE-002",
                category="SAFETY",
                title="Avoid Known Allergenic Fold Families",
                rule="Screen designed sequences against AllergenOnline (COMPARE database). Avoid fold families with high allergenic prevalence (e.g., 2S albumin, nsLTP, profilin). De novo folds are inherently safer.",
                evidence_strength="moderate",
                applicable_afp_types=["de_novo", "type_i", "type_iii", "plant"],
                counter_examples=["No reported AFP allergies — but novel food assessment required"],
                pmid_list=["19836343"],
            ),
            DesignPrinciple(
                principle_id="SAFE-003",
                category="SAFETY",
                title="Non-Human Glycosylation is Immunogenic",
                rule="Yeast-produced AFGPs carry hyper-mannosylated glycans that elicit immune responses. Use GlycoSwitch strains or cell-free expression with defined glycosylation to match human patterns.",
                evidence_strength="moderate",
                applicable_afp_types=["afgp"],
                counter_examples=["Non-glycosylated AFPs — no glycosylation concern"],
                pmid_list=["18566512"],
            ),
        ],
    }

    # ------------------------------------------------------------------
    # APPLICATION REQUIREMENTS
    # ------------------------------------------------------------------
    APPLICATION_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
        "ice_cream": {
            "description": "Ice cream and frozen desserts — control ice crystal size for smooth texture",
            "th_weight": 0.1,
            "iri_weight": 0.9,
            "stability_weight": 0.7,
            "safety_requirements": "GRAS or approved food additive; plant or de novo origin preferred",
            "expression_level_needs": "High (kg-scale production); E. coli or P. pastoris at industrial scale",
            "target_concentration": "10–100 µg/mL in final product",
            "temperature_range": "-20 to -5 °C (storage to serving)",
            "key_considerations": [
                "IRI is the primary activity — TH irrelevant at freezer temperatures",
                "Protein must remain active at acidic pH (4.5–5.5 in ice cream mix)",
                "Heat stability required — survives pasteurization (72 °C, 15 s)",
                "Cost is critical — <$10/kg final formulation needed",
            ],
        },
        "cell_cryo": {
            "description": "Cell cryopreservation — protect mammalian cells during freeze-thaw",
            "th_weight": 0.3,
            "iri_weight": 0.7,
            "stability_weight": 0.8,
            "safety_requirements": "Non-toxic to mammalian cells; endotoxin-free; sterile-filterable",
            "expression_level_needs": "Medium (mg-scale per batch); recombinant E. coli with endotoxin removal",
            "target_concentration": "0.1–1.0 mg/mL in cryopreservation medium",
            "temperature_range": "-196 to +37 °C (LN2 storage to thawing)",
            "key_considerations": [
                "Must not penetrate cell membrane — extracellular AFP only",
                "Compatible with DMSO/glycerol — synergistic or replacement effect",
                "No immunogenicity for therapeutic cells (CAR-T, stem cells)",
                "IRI protects against recrystallization during thawing; moderate TH helps prevent intracellular ice",
            ],
        },
        "organ_preservation": {
            "description": "Organ preservation for transplant — extend viable storage time",
            "th_weight": 0.5,
            "iri_weight": 0.5,
            "stability_weight": 1.0,
            "safety_requirements": "Medical-grade; no toxicity at perfusion concentrations; no immunogenicity; stable in UW/Custodiol solutions",
            "expression_level_needs": "High (gram-scale); mammalian or yeast expression for proper folding; endotoxin-free",
            "target_concentration": "1–10 mg/mL in perfusion solution",
            "temperature_range": "0 to +4 °C (hypothermic preservation) or -6 to 0 °C (subzero preservation)",
            "key_considerations": [
                "Both TH and IRI matter — TH prevents ice formation, IRI limits growth of any nucleated ice",
                "Must function in complex solutions (UW solution, blood, plasma)",
                "Extended stability — 24–72 hour perfusion at 4 °C",
                "No platelet activation or complement activation",
                "Permeation into tissue interstitium required for uniform protection",
            ],
        },
        "anti_ice_coating": {
            "description": "Anti-ice coatings — surfaces that prevent ice accretion (aircraft, wind turbines, power lines)",
            "th_weight": 0.9,
            "iri_weight": 0.1,
            "stability_weight": 1.0,
            "safety_requirements": "Environmental safety — non-toxic to aquatic life; UV-stable; no bioaccumulation",
            "expression_level_needs": "Very high (ton-scale ideal); industrial fermentation or plant-based production",
            "target_concentration": "Immobilized on surface (covalent attachment); 1–10 mg/cm² coating density",
            "temperature_range": "-40 to 0 °C (environmental exposure)",
            "key_considerations": [
                "TH is primary metric — must prevent ice nucleation on surface",
                "Immobilization chemistry must not block IBS face",
                "Mechanical durability — withstand rain erosion, UV, thermal cycling",
                "Hyperactive insect-type AFPs preferred for highest TH per unit area",
                "De novo design enables oriented immobilization via engineered Cys/His tags",
            ],
        },
        "frozen_dough": {
            "description": "Frozen dough and bakery — protect yeast and gluten network during frozen storage",
            "th_weight": 0.1,
            "iri_weight": 0.9,
            "stability_weight": 0.6,
            "safety_requirements": "Food-grade; GRAS or novel food approved; plant origin strongly preferred; no effect on dough rheology or baking performance",
            "expression_level_needs": "High (kg-scale); plant-based expression or recombinant yeast (same as baker's yeast)",
            "target_concentration": "0.01–0.1% (w/w flour basis)",
            "temperature_range": "-20 to -10 °C (frozen storage)",
            "key_considerations": [
                "IRI protects yeast cells and gluten network from ice recrystallization damage",
                "Must survive baking temperatures (up to 200 °C internal) — post-bake activity irrelevant",
                "Plant AFPs (LpAFP-type) already proven in frozen dough applications",
                "No effect on yeast fermentation activity",
                "Cost-sensitive — must be <$50/kg for commercial viability",
            ],
        },
        "meat_preservation": {
            "description": "Meat and seafood preservation — reduce freeze damage during frozen storage",
            "th_weight": 0.2,
            "iri_weight": 0.8,
            "stability_weight": 0.7,
            "safety_requirements": "Food-grade; no effect on taste/texture/color; GRAS or approved; clear labeling requirements",
            "expression_level_needs": "Medium-high (kg-scale); yeast or plant expression",
            "target_concentration": "0.05–0.5 mg/g meat",
            "temperature_range": "-30 to -5 °C (frozen storage to thawing)",
            "key_considerations": [
                "IRI is dominant — prevents drip loss from ice recrystallization during temperature fluctuation",
                "Must penetrate muscle tissue or be injected as brine component",
                "No proteolytic activity (degrade meat proteins)",
                "Compatible with salt (0.5–3% NaCl in processed meats)",
                "AFGP-type glycosylated AFPs have precedent in seafood preservation",
            ],
        },
    }

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def query_by_protein(self, protein_name: str) -> List[MutationFinding]:
        """Retrieve all mutation findings for a given source protein.

        Searches case-insensitively for partial name matches.

        Parameters
        ----------
        protein_name : str
            Protein name or part of it, e.g. "MaIBP", "Type I", "LpAFP".

        Returns
        -------
        List[MutationFinding]
        """
        name_lower = protein_name.lower()
        return [
            f for f in self.MUTATION_FINDINGS
            if name_lower in f.source_protein.lower()
        ]

    def query_by_mutation_type(
        self,
        from_aa: str,
        to_aa: str,
    ) -> List[MutationFinding]:
        """Find all literature findings involving a specific amino acid substitution.

        Parameters
        ----------
        from_aa : str
            Original amino acid one-letter code.
        to_aa : str
            Target amino acid one-letter code.

        Returns
        -------
        List[MutationFinding]
        """
        return [
            f for f in self.MUTATION_FINDINGS
            if f.from_aa.upper() == from_aa.upper()
            and f.to_aa.upper() == to_aa.upper()
        ]

    def get_principles_for_category(self, category: str) -> List[DesignPrinciple]:
        """Return all design principles for a given optimization category.

        Parameters
        ----------
        category : str
            One of: "TH_OPTIMIZATION", "IRI_OPTIMIZATION", "STABILITY",
            "EXPRESSION", "SAFETY".

        Returns
        -------
        List[DesignPrinciple]
        """
        return self.DESIGN_PRINCIPLES.get(category.upper(), [])

    def get_all_principles(self) -> Dict[str, List[DesignPrinciple]]:
        """Return all design principles organized by category.

        Returns
        -------
        Dict[str, List[DesignPrinciple]]
        """
        return dict(self.DESIGN_PRINCIPLES)

    def get_requirements_for_application(
        self,
        scenario: str,
    ) -> Optional[Dict[str, Any]]:
        """Get the full requirements profile for a specific application scenario.

        Parameters
        ----------
        scenario : str
            One of the application keys: "ice_cream", "cell_cryo",
            "organ_preservation", "anti_ice_coating", "frozen_dough",
            "meat_preservation".

        Returns
        -------
        dict or None
            Requirements profile with weights, safety notes, and key considerations.
        """
        key = scenario.lower().replace(" ", "_")
        return self.APPLICATION_REQUIREMENTS.get(key)

    def list_applications(self) -> List[str]:
        """Return all available application scenarios.

        Returns
        -------
        List[str]
        """
        return sorted(self.APPLICATION_REQUIREMENTS.keys())

    def get_high_impact_mutations(self, min_relevance: float = 8.0) -> List[MutationFinding]:
        """Return mutations with high design relevance.

        Parameters
        ----------
        min_relevance : float
            Minimum relevance score (0–10). Default 8.0.

        Returns
        -------
        List[MutationFinding]
        """
        return sorted(
            [f for f in self.MUTATION_FINDINGS if f.relevance_score >= min_relevance],
            key=lambda x: x.relevance_score,
            reverse=True,
        )

    def get_gain_of_function_mutations(self) -> List[MutationFinding]:
        """Return only mutations that INCREASE activity.

        Returns
        -------
        List[MutationFinding]
        """
        return [
            f for f in self.MUTATION_FINDINGS
            if f.th_change_pct > 0 or f.iri_change_pct > 0
        ]

    def get_loss_of_function_mutations(self) -> List[MutationFinding]:
        """Return only mutations that DECREASE or ABOLISH activity.

        Returns
        -------
        List[MutationFinding]
        """
        return [
            f for f in self.MUTATION_FINDINGS
            if f.th_change_pct < 0 or f.iri_change_pct < 0
        ]
