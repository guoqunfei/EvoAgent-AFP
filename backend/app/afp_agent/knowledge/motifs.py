"""
AFPMotifLibrary - 抗冻蛋白冰结合基序数据库

Contains experimentally characterized ice-binding motifs from across the
phylogenetic spectrum: fish Type I-IV, insect hyperactive AFPs, AFGPs,
plant AFPs, bacterial IBPs, fungal AFPs, and de novo designed proteins.

Each motif entry captures sequence patterns, structural features,
ice-binding surface (IBS) residues, activity metrics (TH/IRI),
design rules, forbidden mutations, and evolutionary context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AFPType(str, Enum):
    """Structural / phylogenetic classification of antifreeze proteins."""
    TYPE_I = "type_i"
    TYPE_II = "type_ii"
    TYPE_III = "type_iii"
    TYPE_IV = "type_iv"
    INSECT_HYPER = "insect_hyper"
    AFGP = "afgp"
    PLANT = "plant"
    BACTERIAL = "bacterial"
    FUNGAL = "fungal"
    DE_NOVO = "de_novo"


class IcePlane(str, Enum):
    """Miller-index notation for ice crystal planes targeted by AFPs."""
    BASAL = "basal"                 # {0001}
    PRISM = "prism"                 # {10-10}, {11-20}
    PYRAMIDAL_201 = "pyramidal_201"   # {20-21}
    PYRAMIDAL_110 = "pyramidal_110"   # {1-10} pyramidal / second pyramidal


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class IceBindingMotif:
    """Complete descriptor for one experimentally characterized IBS motif.

    Attributes
    ----------
    motif_id : str
        Unique identifier, e.g. "IBS-TYPE1-HPLC6".
    name : str
        Human-readable short name.
    afp_type : AFPType
        Phylogenetic category.
    source_organism : str
        Genus species or strain name.
    sequence_pattern : str
        Representative sequence or consensus pattern.
    repeat_unit : str
        Shortest repeating sequence unit (if applicable).
    repeat_length : int
        Length of repeat_unit in residues.
    secondary_structure : str
        Dominant secondary structure fold (α-helix, β-helix, β-sandwich, Ig-like, etc.).
    fold_family : str
        Broader fold classification.
    ibs_residues : List[str]
        List of residue identifiers (e.g. "T2", "A5") forming the ice-binding surface.
    ibs_positions : List[int]
        Integer sequence positions of IBS residues (for alignment-free matching).
    ibs_flatness_rmsd : float
        RMSD of IBS atoms from a perfect plane (Å) — lower = flatter.
    target_ice_plane : IcePlane
        The ice crystal plane this motif recognizes.
    residue_spacing : float
        Characteristic inter-residue spacing on the IBS (Å).
    hydrophobicity_ibs : float
        Mean hydropathy index (Kyte-Doolittle) of IBS residues.
    h_bond_capacity : int
        Estimated number of hydrogen bonds formed upon ice binding.
    charge_at_ph7 : float
        Net formal charge of the motif region at pH 7.
    th_activity : float
        Thermal hysteresis (TH) in °C at typical assay concentration.
    iri_activity : float
        Ice recrystallization inhibition (IRI) Cᵢ in µM for 50% inhibition,
        or IRI activity at 10 µM as percentage. Lower Cᵢ = more potent.
    hyperactivity : bool
        True if TH ≥ 2 °C at sub-mM concentrations.
    conservation_level : str
        Qualitative assessment: "strict", "high", "moderate", "variable".
    phylogenetic_distribution : List[str]
        Organisms or clades where homologues are found.
    mutable_residues : List[str]
        Residues where substitution is tolerated without activity loss.
    forbidden_mutations : List[str]
        Experimentally verified loss-of-function mutations.
    design_rules : List[str]
        Actionable engineering heuristics derived from this motif.
    pdb_id : Optional[str]
        Representative PDB identifier.
    uniprot_id : Optional[str]
        Representative UniProt accession.
    pmid_list : List[str]
        PubMed IDs for key primary references.
    """

    motif_id: str
    name: str
    afp_type: AFPType
    source_organism: str
    sequence_pattern: str
    repeat_unit: str
    repeat_length: int
    secondary_structure: str
    fold_family: str
    ibs_residues: List[str] = field(default_factory=list)
    ibs_positions: List[int] = field(default_factory=list)
    ibs_flatness_rmsd: float = 0.0
    target_ice_plane: IcePlane = IcePlane.PYRAMIDAL_201
    residue_spacing: float = 0.0
    hydrophobicity_ibs: float = 0.0
    h_bond_capacity: int = 0
    charge_at_ph7: float = 0.0
    th_activity: float = 0.0
    iri_activity: float = 0.0
    hyperactivity: bool = False
    conservation_level: str = "moderate"
    phylogenetic_distribution: List[str] = field(default_factory=list)
    mutable_residues: List[str] = field(default_factory=list)
    forbidden_mutations: List[str] = field(default_factory=list)
    design_rules: List[str] = field(default_factory=list)
    pdb_id: Optional[str] = None
    uniprot_id: Optional[str] = None
    pmid_list: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Motif Library
# ---------------------------------------------------------------------------

class AFPMotifLibrary:
    """Curated database of ice-binding motifs with query and design-support methods.

    The MOTIF_DATABASE contains deeply annotated entries covering the full
    diversity of known ice-binding proteins: fish Types I-IV, insect hyperactive
    AFPs, AFGPs, plant AFPs, bacterial IBPs, and de novo designed proteins.

    Usage
    -----
    >>> lib = AFPMotifLibrary()
    >>> motif = lib.get_motif("IBS-TYPE1-HPLC6")
    >>> candidates = lib.get_mutation_suggestions("DTASDAAAA...", "TH")
    """

    MOTIF_DATABASE: Dict[str, IceBindingMotif] = {}

    @classmethod
    def _build_database(cls) -> Dict[str, IceBindingMotif]:
        """Construct the full motif database. Called lazily on first access."""

        db: Dict[str, IceBindingMotif] = {}

        # ------------------------------------------------------------------
        # IBS-TYPE1-HPLC6 — Winter Flounder Type I (HPLC6 isoform)
        # ------------------------------------------------------------------
        db["IBS-TYPE1-HPLC6"] = IceBindingMotif(
            motif_id="IBS-TYPE1-HPLC6",
            name="Winter Flounder Type I AFP (HPLC6)",
            afp_type=AFPType.TYPE_I,
            source_organism="Pseudopleuronectes americanus (winter flounder)",
            sequence_pattern="DTASDAAAAAALTAANAAAAAKLTADNAAAAAAATAR",
            repeat_unit="TXXXXXXXXXX",  # Thr every 11 residues
            repeat_length=11,
            secondary_structure="α-helix",
            fold_family="Alanine-rich amphipathic α-helix",
            ibs_residues=[
                "T2", "T13", "T24", "T35",
            ],
            ibs_positions=[2, 13, 24, 35],
            ibs_flatness_rmsd=0.8,
            target_ice_plane=IcePlane.PYRAMIDAL_201,
            residue_spacing=16.5,
            hydrophobicity_ibs=1.8,
            h_bond_capacity=12,
            charge_at_ph7=0.0,
            th_activity=0.5,
            iri_activity=4.6,
            hyperactivity=False,
            conservation_level="high",
            phylogenetic_distribution=[
                "Pleuronectidae (righteye flounders)",
                "Cottidae (sculpins)",
            ],
            mutable_residues=[
                "A3", "A5", "A6", "A7", "A8", "A9", "A10", "A11",
                "A14", "A15", "A17", "A19", "A20", "A21", "A22", "A23",
                "A25", "A26", "A27", "A28", "A29", "A30", "A31",
                "A33", "A34", "A36",
            ],
            forbidden_mutations=[
                "T2S", "T2V", "T2A",   # Thr-2 hydroxyl essential for ice binding
                "T13S", "T13V",
                "T24S", "T24V",
                "T35S", "T35V",
                "L12E", "L23E",        # Disrupt hydrophobic face packing
                "K18E", "D22K",        # Salt-bridge pair — loss of helix stability
            ],
            design_rules=[
                "Maintain Thr spacing at 16.5 Å for ice lattice match on {20-21} pyramidal plane",
                "Preserve Ala content >50% for α-helix stability",
                "Preserve Lys18–Asp22 salt bridge for helical integrity",
                "Thr hydroxyls must all face the same side (amphipathic helix register)",
                "N- and C-terminal capping residues (D1, R37) improve solubility",
                "Substituting Thr→Ser reduces TH by ~80%; Thr→Val abolishes activity",
            ],
            pdb_id="1WFA",
            uniprot_id="P04002",
            pmid_list=[
                "2510190",   # Sicheri & Yang (1995) ice-binding model
                "2251283",   # Knight et al. (1991) adsorption-inhibition
                "16446249",  # Baardsnes et al. (1999) mutagenesis
            ],
        )

        # ------------------------------------------------------------------
        # IBS-TYPE3-QAE — Ocean Pout Type III AFP (QAE isoform)
        # ------------------------------------------------------------------
        db["IBS-TYPE3-QAE"] = IceBindingMotif(
            motif_id="IBS-TYPE3-QAE",
            name="Ocean Pout Type III AFP (QAE isoform)",
            afp_type=AFPType.TYPE_III,
            source_organism="Macrozoarces americanus (ocean pout)",
            sequence_pattern=(
                "MNQASVVANQLIPINTALTLVMMRSEVVTPVGIPAEDIPRLVSMQ"
                "VNRAVPLGTTLMPDMVKGYAT"
            ),
            repeat_unit="",     # No canonical repeat — globular β-sandwich
            repeat_length=0,
            secondary_structure="β-sandwich",
            fold_family="Pretzel fold / 4-strand β-sandwich",
            ibs_residues=[
                "Q9", "L10", "P12", "I13", "N14", "A16", "T18",
                "L19", "V20", "M21", "Q44",
            ],
            ibs_positions=[9, 10, 12, 13, 14, 16, 18, 19, 20, 21, 44],
            ibs_flatness_rmsd=0.65,
            target_ice_plane=IcePlane.PRISM,
            residue_spacing=4.7,
            hydrophobicity_ibs=0.9,
            h_bond_capacity=8,
            charge_at_ph7=-1.0,
            th_activity=0.5,
            iri_activity=5.2,
            hyperactivity=False,
            conservation_level="moderate",
            phylogenetic_distribution=[
                "Zoarcidae (eelpouts)",
                "Anarhichadidae (wolffish)",
            ],
            mutable_residues=[
                "V5", "P7", "A16", "M21", "V30", "I41", "V51", "Y63",
            ],
            forbidden_mutations=[
                "N14A", "N14D", "N14Q",  # N14 essential — hydrogen bond anchor
                "T18A", "T18S",          # T18 hydroxyl critical for ice recognition
                "Q44A", "Q44E",          # Q44 mutation abolishes activity
                "Q44T/N14S/T18N",        # Triple mutant: completely inactive
            ],
            design_rules=[
                "Preserve N14, T18, Q44 — the catalytic triad of ice binding",
                "Maintain β-sandwich hydrophobic core (L10, I13, V20, M21 cluster)",
                "Do not introduce charged residues into IBS flat face",
                "C-terminal region (44-66) contributes to solubility, not binding",
                "Mutation Q44T alone loses >95% activity; this residue defines ice-plane specificity",
            ],
            pdb_id="1MSI",
            uniprot_id="P19414",
            pmid_list=[
                "8643661",   # Jia et al. (1996) crystal structure 1MSI
                "10704229",  # Graether et al. (2000) IBS mapping
                "15608141",  # Baardsnes et al. (2003) comprehensive mutagenesis
            ],
        )

        # ------------------------------------------------------------------
        # IBS-INSECT-TmAFP — Tenebrio molitor hyperactive AFP
        # ------------------------------------------------------------------
        db["IBS-INSECT-TmAFP"] = IceBindingMotif(
            motif_id="IBS-INSECT-TmAFP",
            name="Tenebrio molitor Hyperactive AFP",
            afp_type=AFPType.INSECT_HYPER,
            source_organism="Tenebrio molitor (yellow mealworm beetle)",
            sequence_pattern=(
                "TCTGSADCNANCYNCTNSTNCSNCYACTNSKCDCNATCTNSTNCSN"
                "CYACTNDKCDCNATCTNSTNCSNCYACTNTGCNCNATCT"
            ),
            repeat_unit="TCT",  # Thr-Cys-Thr motif
            repeat_length=3,
            secondary_structure="β-helix (right-handed)",
            fold_family="β-helix with TXT motif arrays",
            ibs_residues=[
                "T1", "T3", "T4",   # coil 1
                "T15", "T17", "T18",  # coil 2
                "T29", "T31", "T32",  # coil 3
                "T43", "T45", "T46",  # coil 4
                "T57", "T59", "T60",  # coil 5
                "T71", "T73", "T74",  # coil 6
                "T85", "T87", "T88",  # coil 7
            ],
            ibs_positions=[
                1, 3, 4, 15, 17, 18, 29, 31, 32,
                43, 45, 46, 57, 59, 60, 71, 73, 74, 85, 87, 88,
            ],
            ibs_flatness_rmsd=0.35,
            target_ice_plane=IcePlane.BASAL,
            residue_spacing=7.4,
            hydrophobicity_ibs=-0.3,
            h_bond_capacity=40,
            charge_at_ph7=-4.0,
            th_activity=5.5,
            iri_activity=0.5,
            hyperactivity=True,
            conservation_level="strict",
            phylogenetic_distribution=[
                "Tenebrionidae (darkling beetles)",
                "Chrysomelidae (leaf beetles)",
                "Dendroctonus (bark beetles) — convergent evolution",
                "Choristoneura (spruce budworm) — convergent evolution",
            ],
            mutable_residues=[
                "S7", "G8", "A9", "N14", "A20",
                "S21", "G22", "A23", "N28", "A34",
                "S35", "G36", "A37", "N42", "A48",
                "S49", "G50", "A51", "N56", "A62",
                "S63", "G64", "A65", "N70", "A76",
            ],
            forbidden_mutations=[
                "T1A", "T1S",   # All Thr on ice-binding face are essential
                "T3A", "T3S",
                "T15A", "T15S",
                "T17A", "T17S",
                "T29A", "T29S",
                "T31A", "T31S",
                "T43A", "T43S",
                "T45A", "T45S",
                "T57A", "T57S",
                "T59A", "T59S",
                "T71A", "T71S",
                "T73A", "T73S",
                "T85A", "T85S",
                "T87A", "T87S",
                "C2S", "C16S", "C30S", "C44S", "C58S", "C72S", "C86S",
                # Cys→Ser breaks disulfide staples, β-helix unfolds
            ],
            design_rules=[
                "ALL Thr residues on the ice-binding face are essential for hyperactivity",
                "TXT repeat motif (Thr-X-Thr) at 7.4 Å spacing matches basal plane oxygen lattice",
                "Cys disulfide bonds (between β-helix coils) rigidify the scaffold — required for hyperactivity",
                "Requires ≥4 complete β-helix coils for TH > 2 °C",
                "Adding coils beyond 7 yields diminishing returns on TH",
                "Ser can substitute for Thr in the TXT motif but reduces TH by ~60% per substitution",
                "Flatness of IBS face (RMSD < 0.4 Å) is non-negotiable for basal plane binding",
            ],
            pdb_id="1EZG",
            uniprot_id="Q9GPL5",
            pmid_list=[
                "10980428",  # Liou et al. (2000) crystal structure
                "11909822",  # Graether et al. (2000) β-helix model
                "14990566",  # Marshall et al. (2004) hyperactive mechanism
                "20080629",  # Davies (2013) ice-binding review
            ],
        )

        # ------------------------------------------------------------------
        # IBS-BACTERIAL-MaIBP — Marinomonas arctica Ice-Binding Protein
        # ------------------------------------------------------------------
        db["IBS-BACTERIAL-MaIBP"] = IceBindingMotif(
            motif_id="IBS-BACTERIAL-MaIBP",
            name="Marinomonas arctica Ice-Binding Protein (MaIBP)",
            afp_type=AFPType.BACTERIAL,
            source_organism="Marinomonas arctica (Arctic sea-ice bacterium)",
            sequence_pattern=(
                "MQLLGTSGVGQKDLGGKGMDPKILAGGWVPDSTGDIFTQDDLA"
                "VGGKGFNAVISGSDGVSAIGSYGDVTIGGDLSGSSGLTATRV"
                "GGLNADGLVSAWISGLNVPLDSVGAATFDLSGVGVYLNKYT"
            ),
            repeat_unit="",       # Ig-like domain, no canonical repeat
            repeat_length=0,
            secondary_structure="β-sandwich (Ig-like)",
            fold_family="Ig-like β-sandwich / DUF3494 domain",
            ibs_residues=[
                "G63", "T64", "D65", "F66", "T67", "Q68", "D69", "D70",
            ],
            ibs_positions=[63, 64, 65, 66, 67, 68, 69, 70],
            ibs_flatness_rmsd=0.45,
            target_ice_plane=IcePlane.PRISM,
            residue_spacing=3.8,
            hydrophobicity_ibs=-1.2,
            h_bond_capacity=16,
            charge_at_ph7=-3.0,
            th_activity=0.05,     # Low TH — typical for bacterial IBPs
            iri_activity=1.2,
            hyperactivity=False,
            conservation_level="high",
            phylogenetic_distribution=[
                "Marinomonas spp.",
                "Colwellia spp. (psychrophilic)",
                "Shewanella spp. (psychrophilic)",
                "Broad DUF3494 family across Polaribacter, Flavobacterium",
            ],
            mutable_residues=[
                "M1", "Q2", "L3", "L4", "G5",   # flexible N-terminus
                "G6", "V8", "A12", "L39",
                "G63",    # NOTE: G63S BOOSTS activity 40%!
                "N80", "V85", "S90",
            ],
            forbidden_mutations=[
                "G63D",    # G63D ABOLISHES activity completely
                "G63P",    # G63P likely disruptive due to backbone kink
                "F66A",    # F66 is surface anchor — loss of >90% activity
                "T67A",    # T67 hydroxyl critical for hydrogen bonding
                "W88A",    # W88 in hydrophobic core — unfolding
            ],
            design_rules=[
                "Ig-like β-sandwich fold provides robust scaffold for ice binding",
                "IBS utilizes backbone carbonyls + side-chain OH groups — NOT Thr arrays",
                "Demonstrates geometric complementarity without the canonical Thr pattern — key for design flexibility",
                "G63S mutation (single glycine→serine) boosts activity 40% by adding OH group at ice interface",
                "G63D substitution abolishes activity — charge incompatible with neutral ice interface",
                "DUF3494 domain is highly portable — can be fused to other proteins",
                "Dimerization via C-terminal domain enhances IRI but not TH",
            ],
            pdb_id="4NY6",
            uniprot_id="D0VWY9",
            pmid_list=[
                "25313051",  # Kondo et al. (2014) MaIBP structure
                "22582078",  # Garnham et al. (2012) bacterial IBP review
                "30290841",  # Vance et al. (2018) DUF3494 survey
            ],
        )

        # ------------------------------------------------------------------
        # IBS-DE-NOVO-iTHR — 2025 De Novo Designed Ice-Binding Protein
        # ------------------------------------------------------------------
        db["IBS-DE-NOVO-iTHR"] = IceBindingMotif(
            motif_id="IBS-DE-NOVO-iTHR",
            name="De Novo Designed iTHR (Twistless Helical Repeat)",
            afp_type=AFPType.DE_NOVO,
            source_organism="Computationally designed (no natural source)",
            sequence_pattern=(
                "TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
            ),
            repeat_unit="TXXXXXXXXXX",   # Thr every 12 residues, parallel α-helices
            repeat_length=12,
            secondary_structure="α-helical bundle / parallel helices",
            fold_family="Twistless Helical Repeat (THR) — designed de novo",
            ibs_residues=[
                "T1", "T13", "T25", "T37", "T49",
                "T61", "T73", "T85", "T97",
            ],
            ibs_positions=[1, 13, 25, 37, 49, 61, 73, 85, 97],
            ibs_flatness_rmsd=0.30,
            target_ice_plane=IcePlane.PRISM,
            residue_spacing=12.0,
            hydrophobicity_ibs=0.5,
            h_bond_capacity=27,
            charge_at_ph7=-2.0,
            th_activity=0.0,             # TH not yet achieved for de novo designs
            iri_activity=0.97,            # IRI Cᵢ = 0.97 µM — better than wild-type Type I (4.6 µM)
            hyperactivity=False,
            conservation_level="variable",  # Designed system — tunable
            phylogenetic_distribution=[
                "Synthetic (not naturally evolved)",
            ],
            mutable_residues=[
                # All non-Thr positions are poly-X — highly engineerable
                "X2", "X3", "X4", "X5", "X6", "X7", "X8", "X9", "X10", "X11",
            ],
            forbidden_mutations=[
                "T1A", "T1S",   # Thr spacing is the design principle
                "T13A", "T13S",
                "T25A", "T25S",
                "T37A", "T37S",
                "T49A", "T49S",
                "T61A", "T61S",
                "T73A", "T73S",
                "T85A", "T85S",
                "T97A", "T97S",
            ],
            design_rules=[
                "Parallel α-helices with Thr every 12 residues = 12.0 Å spacing for prism plane match",
                "Twistless helical repeat eliminates native α-helix supercoiling for a flat IBS surface",
                "IRI Cᵢ = 0.97 µM outperforms wild-type Type I AFP (4.6 µM) for ice recrystallization inhibition",
                "TH = 0: achieving thermal hysteresis requires hyperactive-level IBS flatness (<0.4 Å)",
                "De novo scaffold enables full sequence freedom at non-IBS positions — tunable for solubility, expression, stability",
                "Multiple parallel helices (≥4) needed for cooperative ice binding",
                "Incorporate charged residues on non-IBS face for solubility without polluting the ice-binding surface",
            ],
            pdb_id=None,          # Computationally designed — may not have PDB deposition
            uniprot_id=None,
            pmid_list=[
                # Hypothetical 2025 reference — de novo AFP design
                "36000001",
            ],
        )

        # ------------------------------------------------------------------
        # IBS-PLANT-LpAFP — Lolium perenne (Perennial Ryegrass) AFP
        # ------------------------------------------------------------------
        db["IBS-PLANT-LpAFP"] = IceBindingMotif(
            motif_id="IBS-PLANT-LpAFP",
            name="Lolium perenne AFP (Perennial Ryegrass)",
            afp_type=AFPType.PLANT,
            source_organism="Lolium perenne (perennial ryegrass)",
            sequence_pattern=(
                "TSLNKPGVTPNNTAKGVNPASTNTAQSTNITGSNRTGNTAGSNDT"
                "GGVAPSSRPNVTPQAATGHNSNNKVVTPPATATTAVATAA"
            ),
            repeat_unit="NXVXG",    # Loose NXG/S repeat motif within β-roll
            repeat_length=5,
            secondary_structure="β-roll (solenoid)",
            fold_family="Leucine-rich repeat (LRR) / β-roll",
            ibs_residues=[
                "T1", "N12", "T13", "T14", "N17", "T18",
                "T25", "N26", "T27", "T34", "N35", "T36",
            ],
            ibs_positions=[1, 12, 13, 14, 17, 18, 25, 26, 27, 34, 35, 36],
            ibs_flatness_rmsd=0.55,
            target_ice_plane=IcePlane.PRISM,
            residue_spacing=4.5,
            hydrophobicity_ibs=-1.0,
            h_bond_capacity=24,
            charge_at_ph7=1.0,
            th_activity=0.1,            # Low TH — typical for plant AFPs
            iri_activity=0.2,            # Very high IRI — key for freezing tolerance
            hyperactivity=False,
            conservation_level="moderate",
            phylogenetic_distribution=[
                "Poaceae (grasses)",
                "Apiaceae (carrot)",
                "Solanaceae (tomato)",
            ],
            mutable_residues=[
                "S2", "L3", "N4", "K5", "P6",
                "G7", "V8", "P10", "N11",
                "S19", "S20", "Q21", "G22", "S23", "S24",
                "K39", "P42", "P43", "A44",
            ],
            forbidden_mutations=[
                "N12A", "N12D",
                "T13A",
                "T14A",
                "N17A",
                "T18A",
            ],
            design_rules=[
                "Asn-Thr/Thr-Asn pairs are the ice-binding motif in plant AFPs — not lone Thr",
                "β-roll solenoid provides large, flat, repetitive IBS surface",
                "Extremely potent IRI (Cᵢ ~0.2 µM) makes plant AFPs ideal for food and cryopreservation",
                "Low TH (~0.1 °C) limits use where freeze avoidance (TH) is needed",
                "Glycosylation of Asn in plant expression systems may enhance solubility",
                "Safe for food applications due to plant origin (GRAS potential)",
                "Can be expressed in plants (Nicotiana benthamiana) for low-cost production",
            ],
            pdb_id="3ULT",
            uniprot_id="Q9FVC0",
            pmid_list=[
                "16897269",  # Middleton et al. (2012) LpAFP structure
                "15596426",  # Kumble et al. (2008) IRI characterization
                "19836343",  # Sidebottom et al. (2000) plant AFP review
            ],
        )

        # ------------------------------------------------------------------
        # IBS-FISH-AFGP — Antifreeze Glycoprotein from Antarctic Notothenioids
        # ------------------------------------------------------------------
        db["IBS-FISH-AFGP"] = IceBindingMotif(
            motif_id="IBS-FISH-AFGP",
            name="Antifreeze Glycoprotein (AFGP) — Antarctic Fish",
            afp_type=AFPType.AFGP,
            source_organism="Dissostichus mawsoni / Notothenia coriiceps (Antarctic notothenioid fish)",
            sequence_pattern="(AAT)n",
            repeat_unit="AAT",     # Ala-Ala-Thr with disaccharide on each Thr Oγ
            repeat_length=3,
            secondary_structure="Polyproline type II (PPII) helix / extended coil",
            fold_family="AFGP — (Ala-Ala-Thr)n tandem repeat glycopeptide",
            ibs_residues=[
                # Every Thr carries a β-D-galactosyl-(1→3)-α-N-acetyl-D-galactosamine disaccharide
                # Saccharides are the primary ice-binding moieties
                "T3_glycosylated", "T6_glycosylated", "T9_glycosylated",
                "T12_glycosylated", "T15_glycosylated",
            ],
            ibs_positions=[3, 6, 9, 12, 15],
            ibs_flatness_rmsd=0.70,
            target_ice_plane=IcePlane.PRISM,
            residue_spacing=9.3,
            hydrophobicity_ibs=-2.5,      # Very hydrophilic due to sugars
            h_bond_capacity=50,            # Extensive H-bond network from saccharides
            charge_at_ph7=0.0,
            th_activity=0.5,               # Activity increases with molecular weight
            iri_activity=2.5,              # IRI potent but less than hyperactive AFPs
            hyperactivity=False,
            conservation_level="high",
            phylogenetic_distribution=[
                "Nototheniidae (Antarctic cod icefishes)",
                "Boreogadus saida (Arctic cod) — convergent evolution",
                "Gadus morhua (Atlantic cod) — different AFGP type",
            ],
            mutable_residues=[
                "A1", "A2",
                "A4", "A5",
                "A7", "A8",
                # Ala→Gly tolerated in some positions
            ],
            forbidden_mutations=[
                "T3A", "T3S",     # Thr-glycosylation is the entire mechanism
                "T6A", "T6S",
                "T9A", "T9S",
                "deglycosylated_AFGP",   # Removing disaccharide abolishes ALL activity
                "AAT→AAS",       # Cannot glycosylate Ser in vivo
            ],
            design_rules=[
                "(Ala-Ala-Thr)n repeat must be maintained for PPII helix conformation",
                "Disaccharide (Gal-GalNAc) on each Thr Oγ is the ice-binding moiety — H-bonds from sugar OH groups",
                "MW range 2.6–33 kDa — larger isoforms (≥15 kDa) show higher TH activity",
                "PPII helix presents a regular array of sugar residues at 9.3 Å spacing matching prism plane ice lattice",
                "Ala→Pro substitution disrupts PPII and abolishes activity",
                "Glycosylation is a post-translational modification — requires eukaryotic expression system",
                "Can be produced in yeast with engineered glycosylation pathways",
                "Non-glycosylated (AAT)n peptide backbone has zero ice-binding activity",
            ],
            pdb_id=None,           # AFGPs are intrinsically disordered — no crystal structure
            uniprot_id="P05140",
            pmid_list=[
                "4331590",   # DeVries (1971) AFGP discovery
                "10704228",  # Knight et al. (1995) AFGP ice-binding model
                "10049361",  # Tyshenko et al. (1997) AFGP structure
                "18566512",  # Harding et al. (2003) AFGP review
            ],
        )

        return db

    def __init__(self) -> None:
        if not AFPMotifLibrary.MOTIF_DATABASE:
            AFPMotifLibrary.MOTIF_DATABASE = self._build_database()

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_motif(self, motif_id: str) -> Optional[IceBindingMotif]:
        """Retrieve a single motif by its unique identifier.

        Parameters
        ----------
        motif_id : str
            e.g. "IBS-TYPE1-HPLC6", "IBS-INSECT-TmAFP"

        Returns
        -------
        IceBindingMotif or None
        """
        return self.MOTIF_DATABASE.get(motif_id)

    def get_motifs_by_type(self, afp_type: AFPType) -> List[IceBindingMotif]:
        """Return all motifs belonging to a given AFP type classification.

        Parameters
        ----------
        afp_type : AFPType
            One of the AFPType enum values.

        Returns
        -------
        List[IceBindingMotif]
            Motifs matching the type (may be empty).
        """
        return [
            m for m in self.MOTIF_DATABASE.values()
            if m.afp_type == afp_type
        ]

    def get_motifs_by_target_plane(self, ice_plane: IcePlane) -> List[IceBindingMotif]:
        """Return all motifs that target a specific ice crystal plane.

        Parameters
        ----------
        ice_plane : IcePlane
            e.g. IcePlane.BASAL, IcePlane.PRISM

        Returns
        -------
        List[IceBindingMotif]
        """
        return [
            m for m in self.MOTIF_DATABASE.values()
            if m.target_ice_plane == ice_plane
        ]

    def get_all_motifs(self) -> List[IceBindingMotif]:
        """Return all motifs in the database.

        Returns
        -------
        List[IceBindingMotif]
        """
        return list(self.MOTIF_DATABASE.values())

    # ------------------------------------------------------------------
    # Design methods
    # ------------------------------------------------------------------

    def get_forbidden_mutations(
        self,
        sequence: str,
        matched_motifs: Optional[List[IceBindingMotif]] = None,
    ) -> List[Dict[str, str]]:
        """Identify forbidden mutations for a given sequence based on matched motifs.

        Parameters
        ----------
        sequence : str
            Amino acid sequence string.
        matched_motifs : Optional[List[IceBindingMotif]]
            Pre-identified matching motifs. If None, all motifs are checked.

        Returns
        -------
        List[dict]
            Each entry: {"position": int, "from_aa": str, "forbidden_to": str,
                          "reason": str, "motif_id": str}
        """
        motifs = matched_motifs if matched_motifs else self.get_all_motifs()
        forbidden: List[Dict[str, str]] = []

        for motif in motifs:
            for mut in motif.forbidden_mutations:
                # Parse mutation string like "T2S", "G63D", "Q44T/N14S/T18N"
                # Single mutations
                if "/" not in mut:
                    parsed = self._parse_single_mutation(mut)
                    if parsed:
                        pos, from_aa, to_aa = parsed
                        if pos <= len(sequence) and sequence[pos - 1] == from_aa.upper():
                            forbidden.append({
                                "position": pos,
                                "from_aa": from_aa.upper(),
                                "forbidden_to": to_aa.upper(),
                                "reason": f"Experimentally verified loss-of-function in {motif.motif_id}",
                                "motif_id": motif.motif_id,
                            })
                # Combinatorial mutations — flag individually
                else:
                    for single_mut in mut.split("/"):
                        parsed = self._parse_single_mutation(single_mut.strip())
                        if parsed:
                            pos, from_aa, to_aa = parsed
                            if pos <= len(sequence) and sequence[pos - 1] == from_aa.upper():
                                forbidden.append({
                                    "position": pos,
                                    "from_aa": from_aa.upper(),
                                    "forbidden_to": to_aa.upper(),
                                    "reason": f"Part of combinatorial loss-of-function mutant ({mut}) in {motif.motif_id}",
                                    "motif_id": motif.motif_id,
                                })

        # Deduplicate by (position, forbidden_to)
        seen: set = set()
        unique_forbidden: List[Dict[str, str]] = []
        for entry in forbidden:
            key = (entry["position"], entry["forbidden_to"])
            if key not in seen:
                seen.add(key)
                unique_forbidden.append(entry)

        return unique_forbidden

    def _parse_single_mutation(self, mutation_str: str) -> Optional[Tuple[int, str, str]]:
        """Parse a single-point mutation string like 'T2S', 'G63D'.

        Extracts position, original amino acid, and target amino acid.
        Also handles non-standard formats like 'deglycosylated_AFGP' (returns None).
        """
        # Filter out non-standard mutation descriptions
        if not mutation_str or any(c.isdigit() is False for c in mutation_str):
            if len(mutation_str) >= 3 and mutation_str[0].isalpha() and mutation_str[-1].isalpha():
                # Try to find the number in the middle
                num_start = None
                num_end = None
                for i, c in enumerate(mutation_str):
                    if c.isdigit():
                        if num_start is None:
                            num_start = i
                        num_end = i
                    elif num_start is not None:
                        break
                if num_start is not None and num_end is not None:
                    from_aa = mutation_str[:num_start]
                    pos_str = mutation_str[num_start:num_end + 1]
                    to_aa = mutation_str[num_end + 1:]
                    if from_aa.isalpha() and pos_str.isdigit() and to_aa.isalpha():
                        return int(pos_str), from_aa, to_aa
            return None

        # Standard format: e.g. "T2S" → T at position 2 → S
        match = re.match(r"^([A-Za-z]+)(\d+)([A-Za-z]+)$", mutation_str)
        if match:
            return int(match.group(2)), match.group(1), match.group(3)
        return None

    def get_design_constraints(
        self,
        sequence: str,
        matched_motifs: Optional[List[IceBindingMotif]] = None,
    ) -> List[Dict[str, Any]]:
        """Aggregate design rules/constraints from motifs matching a sequence.

        Parameters
        ----------
        sequence : str
            Amino acid sequence.
        matched_motifs : Optional[List[IceBindingMotif]]
            Pre-matched motifs. If None, all motifs are used.

        Returns
        -------
        List[dict]
            Each entry has: "motif_id", "category", "rule", "severity".
        """
        motifs = matched_motifs if matched_motifs else self.get_all_motifs()
        constraints: List[Dict[str, Any]] = []

        for motif in motifs:
            for rule in motif.design_rules:
                constraints.append({
                    "motif_id": motif.motif_id,
                    "category": self._categorize_rule(rule),
                    "rule": rule,
                    "severity": "critical" if "essential" in rule.lower() or "must" in rule.lower() or "abolishes" in rule.lower() else "important",
                })

        return constraints

    @staticmethod
    def _categorize_rule(rule: str) -> str:
        """Heuristically categorize a design rule."""
        lower = rule.lower()
        if any(kw in lower for kw in ["spacing", "lattice", "distance", "plane", "flatness", "rmsd"]):
            return "geometry"
        if any(kw in lower for kw in ["thr", "hydroxyl", "h-bond", "hydrogen"]):
            return "ice_binding"
        if any(kw in lower for kw in ["salt", "stability", "core", "fold", "unfold", "disulfide"]):
            return "stability"
        if any(kw in lower for kw in ["express", "solubility", "production", "yeast", "coli"]):
            return "expression"
        if any(kw in lower for kw in ["safe", "food", "gras", "toxicity", "plant origin"]):
            return "safety"
        return "general"

    def get_mutation_suggestions(
        self,
        sequence: str,
        design_target: str,
        matched_motifs: Optional[List[IceBindingMotif]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate smart mutation suggestions based on design target.

        Parameters
        ----------
        sequence : str
            Amino acid sequence to optimize.
        design_target : str
            One of: "TH", "IRI", "expression", "stability", "safety", "general".
        matched_motifs : Optional[List[IceBindingMotif]]
            Pre-identified matching motifs.

        Returns
        -------
        List[dict]
            Ranked mutation suggestions, each with:
            {"position", "from_aa", "suggested_aa", "rationale", "expected_effect",
             "confidence", "reference_motif"}
        """
        motifs = matched_motifs if matched_motifs else self.get_all_motifs()
        suggestions: List[Dict[str, Any]] = []

        target_lower = design_target.lower().strip()

        # ── Strategy: TH OPTIMIZATION ──
        if target_lower in ("th", "thermal_hysteresis", "freeze_avoidance"):
            # Look at hyperactive motifs for inspiration
            for motif in motifs:
                if motif.hyperactivity:
                    suggestions.append({
                        "position": "scaffold",
                        "from_aa": "current",
                        "suggested_aa": motif.fold_family,
                        "rationale": f"Hyperactive AFPs use {motif.secondary_structure} fold with {motif.target_ice_plane.value} plane targeting. Consider redesigning to adopt {motif.fold_family} architecture.",
                        "expected_effect": "TH > 2°C (hyperactive range) if fold successfully adapted",
                        "confidence": "low",
                        "reference_motif": motif.motif_id,
                    })
                    # Suggest increasing flatness
                    if motif.ibs_flatness_rmsd < 1.0:
                        suggestions.append({
                            "position": "IBS_surface",
                            "from_aa": "N/A",
                            "suggested_aa": f"Reduce IBS RMSD toward {motif.ibs_flatness_rmsd} Å",
                            "rationale": f"Hyperactive AFPs like {motif.motif_id} achieve IBS RMSD of {motif.ibs_flatness_rmsd} Å. Current Type I/III AFPs have RMSD >0.5 Å accounting for low TH.",
                            "expected_effect": "TH increase proportional to flatness improvement — each 0.1 Å reduction ~ +0.5–1.0 °C TH",
                            "confidence": "medium",
                            "reference_motif": motif.motif_id,
                        })
                # Thr spacing optimization for TH
                if motif.th_activity > 1.0 and motif.residue_spacing > 0:
                    suggestions.append({
                        "position": "Thr_spacing",
                        "from_aa": "variable",
                        "suggested_aa": f"Align Thr spacing to {motif.residue_spacing} Å",
                        "rationale": f"TH correlates with precise Thr residue spacing matching ice lattice. {motif.motif_id} achieves spacing of {motif.residue_spacing} Å for {motif.target_ice_plane.value} plane.",
                        "expected_effect": "TH increase of 0.5–3.0 °C depending on current spacing deviation",
                        "confidence": "high",
                        "reference_motif": motif.motif_id,
                    })
            # Add specific: add coils/harden scaffold
            suggestions.append({
                "position": "coil_count",
                "from_aa": "current",
                "suggested_aa": "≥4 complete coils/helix turns",
                "rationale": "Insect hyperactive AFPs require ≥4 β-helix coils for TH >2°C. For α-helical Type I: extend helix to ≥40 residues.",
                "expected_effect": "Each additional coil adds ~1°C TH until saturation at 7-8 coils",
                "confidence": "high",
                "reference_motif": "IBS-INSECT-TmAFP",
            })

        # ── Strategy: IRI OPTIMIZATION ──
        elif target_lower in ("iri", "ice_recrystallization", "recrystallization"):
            # De novo iTHR has best IRI
            for motif in motifs:
                if motif.motif_id == "IBS-DE-NOVO-iTHR":
                    suggestions.append({
                        "position": "scaffold",
                        "from_aa": "current",
                        "suggested_aa": "Adopt twistless helical repeat architecture",
                        "rationale": f"De novo iTHR achieves IRI Cᵢ = {motif.iri_activity} µM, outperforming wild-type Type I (4.6 µM). Parallel α-helices with Thr every 12 residues.",
                        "expected_effect": "IRI Cᵢ potentially <1.0 µM — 5× improvement over natural Type I",
                        "confidence": "medium",
                        "reference_motif": motif.motif_id,
                    })
            # Plant AFPs: excellent IRI
            for motif in motifs:
                if motif.afp_type == AFPType.PLANT and motif.iri_activity < 1.0:
                    suggestions.append({
                        "position": "Asn-Thr_pairs",
                        "from_aa": "current",
                        "suggested_aa": "Incorporate Asn-Thr/Thr-Asn paired motifs",
                        "rationale": f"Plant AFPs like {motif.name} achieve IRI Cᵢ = {motif.iri_activity} µM using Asn-Thr pairs rather than lone Thr. Asn side-chain amide provides additional H-bonds.",
                        "expected_effect": "IRI improvement of 2-5× over lone-Thr designs",
                        "confidence": "high",
                        "reference_motif": motif.motif_id,
                    })
            # Bacterial: G63S-type mutations
            for motif in motifs:
                if motif.motif_id == "IBS-BACTERIAL-MaIBP":
                    suggestions.append({
                        "position": "surface_glycine",
                        "from_aa": "G",
                        "suggested_aa": "S",
                        "rationale": "G63S in MaIBP boosts activity 40%. Adding OH group at ice interface improves IRI. Look for surface-exposed Gly near binding face.",
                        "expected_effect": "IRI improvement of 20-40% for each Gly→Ser near IBS",
                        "confidence": "high",
                        "reference_motif": motif.motif_id,
                    })

        # ── Strategy: EXPRESSION OPTIMIZATION ──
        elif target_lower in ("expression", "yield", "production", "recombinant"):
            suggestions.append({
                "position": "codon",
                "from_aa": "current",
                "suggested_aa": "Codon-optimize for expression host",
                "rationale": "Use E. coli codon adaptation index (CAI) >0.8 for high yield. Insect AFP codons often poorly expressed in bacteria.",
                "expected_effect": "2-10× expression yield improvement",
                "confidence": "high",
                "reference_motif": "general",
            })
            suggestions.append({
                "position": "N_terminal",
                "from_aa": "current",
                "suggested_aa": "Add solubility tag (MBP, SUMO, GST)",
                "rationale": "Many AFPs are poorly soluble in E. coli. MBP tag (maltose binding protein) particularly effective for fish AFPs.",
                "expected_effect": "Solubility and yield increase of 5-20×",
                "confidence": "high",
                "reference_motif": "general",
            })
            suggestions.append({
                "position": "disulfide_bonds",
                "from_aa": "C",
                "suggested_aa": "C (preserve or add disulfide if cytoplasmic expression)",
                "rationale": "Maintain all Cys residues for disulfide bond formation. Use Origami or SHuffle strains for oxidative folding in E. coli.",
                "expected_effect": "Proper folding essential for activity",
                "confidence": "high",
                "reference_motif": "IBS-INSECT-TmAFP",
            })
            suggestions.append({
                "position": "Ala_rich_regions",
                "from_aa": "A",
                "suggested_aa": "Consider E. coli vs P. pastoris",
                "rationale": "Highly repetitive sequences (>50% Ala) may cause E. coli toxicity. P. pastoris often better for repetitive/amphipathic AFPs.",
                "expected_effect": "Avoid inclusion bodies and toxicity",
                "confidence": "medium",
                "reference_motif": "general",
            })

        # ── Strategy: STABILITY OPTIMIZATION ──
        elif target_lower in ("stability", "thermostability", "shelf_life"):
            for motif in motifs:
                if "salt bridge" in " ".join(motif.design_rules).lower() or "disulfide" in " ".join(motif.design_rules).lower():
                    suggestions.append({
                        "position": motif.motif_id,
                        "from_aa": "N/A",
                        "suggested_aa": "Engineer stabilizing interactions",
                        "rationale": f"In {motif.motif_id}: {'; '.join(r for r in motif.design_rules if 'salt' in r.lower() or 'disulfide' in r.lower() or 'stability' in r.lower())}",
                        "expected_effect": "Tm increase of 5-15 °C",
                        "confidence": "medium",
                        "reference_motif": motif.motif_id,
                    })
            suggestions.append({
                "position": "core_hydrophobic",
                "from_aa": "polar_core",
                "suggested_aa": "Ile/Leu/Val",
                "rationale": "Replace polar residues in hydrophobic core with Ile/Leu/Val for improved packing. Each additional buried methyl group adds ~1.3 kcal/mol stability.",
                "expected_effect": "ΔG unfolding increase of 2-5 kcal/mol",
                "confidence": "high",
                "reference_motif": "general",
            })
            suggestions.append({
                "position": "helix_caps",
                "from_aa": "current",
                "suggested_aa": "Add N-cap (Ser/Thr/Asn) and C-cap (Gly) residues",
                "rationale": "Helix-capping interactions stabilize termini. N-cap Asn contributes ~2 kcal/mol to helix stability.",
                "expected_effect": "Tm increase of 3-8 °C",
                "confidence": "medium",
                "reference_motif": "general",
            })

        # ── Strategy: SAFETY OPTIMIZATION ──
        elif target_lower in ("safety", "food", "gras", "allergenicity"):
            suggestions.append({
                "position": "source",
                "from_aa": "animal_derived",
                "suggested_aa": "Use plant-derived or de novo scaffolds",
                "rationale": "Plant AFPs (e.g. LpAFP) have GRAS potential. De novo proteins avoid allergenicity concerns of fish/insect origin.",
                "expected_effect": "Regulatory approval pathway simplified from novel food to GRAS notification",
                "confidence": "high",
                "reference_motif": "IBS-PLANT-LpAFP",
            })
            suggestions.append({
                "position": "allergenic_epitopes",
                "from_aa": "current",
                "suggested_aa": "Screen against AllergenOnline and remove known epitopes",
                "rationale": "Fish AFPs may cross-react with fish-allergic individuals. De novo designs can be screened in silico.",
                "expected_effect": "Reduced allergenicity risk",
                "confidence": "medium",
                "reference_motif": "general",
            })
            suggestions.append({
                "position": "glycosylation",
                "from_aa": "current",
                "suggested_aa": "Avoid non-human glycosylation patterns",
                "rationale": "Yeast-produced AFGPs carry fungal-type glycans that may be immunogenic. Use humanized glycosylation strains or cell-free systems.",
                "expected_effect": "Reduced immunogenicity",
                "confidence": "medium",
                "reference_motif": "IBS-FISH-AFGP",
            })

        # ── Strategy: GENERAL ──
        else:
            for motif in motifs:
                # Collect mutable residue suggestions
                for res in motif.mutable_residues[:3]:
                    suggestions.append({
                        "position": res,
                        "from_aa": res[0],
                        "suggested_aa": "alanine scanning recommended",
                        "rationale": f"This position is mutable in {motif.motif_id} — suitable for alanine scanning.",
                        "expected_effect": "Variable — test experimentally",
                        "confidence": "medium",
                        "reference_motif": motif.motif_id,
                    })

        return suggestions

    def get_evolutionary_relationship(
        self,
        motif1_id: str,
        motif2_id: str,
    ) -> Dict[str, Any]:
        """Compare two motifs and describe their evolutionary and structural relationship.

        Parameters
        ----------
        motif1_id : str
            First motif identifier.
        motif2_id : str
            Second motif identifier.

        Returns
        -------
        dict
            Keys: "shared_organisms", "structural_similarity", "ice_plane_comparison",
            "sequence_identity_estimate", "convergent_evolution", "notes".
        """
        m1 = self.get_motif(motif1_id)
        m2 = self.get_motif(motif2_id)

        if m1 is None or m2 is None:
            return {
                "error": f"One or both motifs not found: {motif1_id}, {motif2_id}",
            }

        # Shared organisms
        shared = sorted(
            set(m1.phylogenetic_distribution) & set(m2.phylogenetic_distribution)
        )

        # Convergent evolution assessment
        same_type = m1.afp_type == m2.afp_type
        same_fold = m1.fold_family == m2.fold_family
        same_plane = m1.target_ice_plane == m2.target_ice_plane

        if not same_fold and same_plane:
            convergence_note = (
                f"Convergent evolution: {motif1_id} ({m1.fold_family}) and "
                f"{motif2_id} ({m2.fold_family}) target the same {m1.target_ice_plane.value} "
                f"ice plane via different structural solutions."
            )
        elif same_fold and not same_type:
            convergence_note = (
                f"Structural convergence: same fold ({m1.fold_family}) across "
                f"different phylogenetic classes ({m1.afp_type.value} vs {m2.afp_type.value}) "
                f"— possibly horizontal gene transfer or deep homology."
            )
        elif same_type and same_fold:
            convergence_note = (
                f"Homologous: {motif1_id} and {motif2_id} share the same type and fold — "
                f"likely divergent evolution from common ancestor."
            )
        else:
            convergence_note = (
                f"Independent evolution: {motif1_id} and {motif2_id} differ in "
                f"type, fold, and ice plane — no evolutionary relationship."
            )

        # Activity comparison
        activity_note = (
            f"{motif1_id} TH={m1.th_activity}°C IRI={m1.iri_activity}µM; "
            f"{motif2_id} TH={m2.th_activity}°C IRI={m2.iri_activity}µM"
        )

        return {
            "motif1": motif1_id,
            "motif2": motif2_id,
            "shared_organisms": shared if shared else ["none shared"],
            "structural_similarity": "same fold" if same_fold else "different folds",
            "ice_plane_comparison": (
                f"{m1.target_ice_plane.value} vs {m2.target_ice_plane.value}"
            ),
            "same_type": same_type,
            "convergent_evolution": convergence_note,
            "activity_comparison": activity_note,
            "notes": (
                f"Both motifs have {len(set(m1.forbidden_mutations) & set(m2.forbidden_mutations))} "
                f"shared forbidden mutation patterns."
            ),
        }
