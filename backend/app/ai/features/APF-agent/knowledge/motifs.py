# knowledge/motifs.py
"""
AFP 冰结合基序库
涵盖5大结构类别 + AFGP + 植物 + 细菌 + 真菌 + de novo 设计
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional


class AFPType(Enum):
    """AFP 结构类型"""
    TYPE_I = "Type I (α-helical, fish)"
    TYPE_II = "Type II (C-type lectin, fish)"
    TYPE_III = "Type III (β-sandwich, fish)"
    TYPE_IV = "Type IV (4-helix bundle, fish)"
    INSECT_HYPER = "Insect hyperactive (β-helical)"
    AFGP = "Antifreeze glycoprotein"
    PLANT = "Plant AFP (β-roll/LRR)"
    BACTERIAL = "Bacterial IBP (multi-domain)"
    FUNGAL = "Fungal AFP (β-helix)"
    DE_NOVO = "De novo designed"
    UNKNOWN = "Unknown/Unclassified"


class IcePlane(Enum):
    """冰晶面类型"""
    BASAL = "Basal plane {0001}"
    PRISM = "Prism plane {10-10}"
    PYRAMIDAL_201 = "Pyramidal plane {20-21}"
    PYRAMIDAL_110 = "Pyramidal plane {11-20}"


@dataclass
class IceBindingMotif:
    """冰结合基序数据类"""
    motif_id: str
    name: str
    afp_type: AFPType
    source_organism: str

    # 序列特征
    sequence_pattern: str           # 正则表达式
    repeat_unit: str                # 重复单元描述
    repeat_length: int              # 重复长度

    # 结构特征
    secondary_structure: str
    fold_family: str

    # 冰结合面特征
    ibs_residues: List[str]         # IBS核心残基（单字母+位置）
    ibs_positions: List[int]        # IBS残基位置
    ibs_flatness_rmsd: float        # IBS平坦性（Å）
    target_ice_plane: IcePlane      # 靶向冰晶面
    residue_spacing: float          # 冰结合残基间距（Å）

    # 物理化学特征
    hydrophobicity_ibs: float
    h_bond_capacity: int
    charge_at_ph7: float

    # 功能特征
    th_activity: float              # TH活性（°C, 1 mg/mL）
    iri_activity: float             # IRI IC₅₀（µM）
    hyperactivity: bool             # 是否为超活性AFP

    # 进化特征
    conservation_level: str
    phylogenetic_distribution: List[str] = field(default_factory=list)

    # 设计约束
    mutable_residues: List[str] = field(default_factory=list)
    forbidden_mutations: List[str] = field(default_factory=list)
    design_rules: List[str] = field(default_factory=list)

    # 参考文献
    pdb_id: Optional[str] = None
    uniprot_id: Optional[str] = None
    pmid_list: List[str] = field(default_factory=list)


# ============================================
# 预建基序库
# ============================================
AFP_MOTIF_DATABASE: Dict[str, IceBindingMotif] = {
    # ========================
    # Type I AFP
    # ========================
    "IBS-TYPE1-HPLC6": IceBindingMotif(
        motif_id="IBS-TYPE1-HPLC6",
        name="Type I HPLC6 11-mer Thr-Ala repeat motif",
        afp_type=AFPType.TYPE_I,
        source_organism="Pseudopleuronectes americanus (winter flounder)",
        sequence_pattern="T[A-Z]{2}A[A-Z]{7}",
        repeat_unit="TxxAxxxxxxx",
        repeat_length=11,
        secondary_structure="α-helix",
        fold_family="Amphipathic α-helix",
        ibs_residues=["T2", "T13", "T24", "T35"],
        ibs_positions=[2, 13, 24, 35],
        ibs_flatness_rmsd=0.8,
        target_ice_plane=IcePlane.PYRAMIDAL_201,
        residue_spacing=16.5,
        hydrophobicity_ibs=0.65,
        h_bond_capacity=4,
        charge_at_ph7=0.0,
        th_activity=0.5,
        iri_activity=4.6,
        hyperactivity=False,
        conservation_level="Highly conserved",
        phylogenetic_distribution=["Pleuronectidae", "Cottidae"],
        mutable_residues=["A", "S", "D", "N", "K", "L"],
        forbidden_mutations=["T2*", "T13*", "T24*", "T35*"],
        design_rules=[
            "保持 Thr@2,13,24,35 —— 精确匹配冰{20-21}面氧原子间距",
            "Ala含量保持>50%以确保α-螺旋稳定性",
            "非IBS面: Ala→Ser 可提高溶解度而不影响活性",
            "Lys18-Asp22盐桥应保留以保证折叠稳定性",
            "避免在IBS面引入大体积疏水残基（破坏平面性）"
        ],
        pdb_id="1WFA",
        uniprot_id="P04002",
        pmid_list=["7638597", "10545318"]
    ),

    "IBS-TYPE1-HPLC8": IceBindingMotif(
        motif_id="IBS-TYPE1-HPLC8",
        name="Type I HPLC8 high-activity variant",
        afp_type=AFPType.TYPE_I,
        source_organism="Pseudopleuronectes americanus (winter flounder)",
        sequence_pattern="T[A-Z]{2}A[A-Z]{7}",
        repeat_unit="TxxAxxxxxxx",
        repeat_length=11,
        secondary_structure="α-helix",
        fold_family="Amphipathic α-helix",
        ibs_residues=["T2", "T13", "T24", "T35"],
        ibs_positions=[2, 13, 24, 35],
        ibs_flatness_rmsd=0.7,
        target_ice_plane=IcePlane.PYRAMIDAL_201,
        residue_spacing=16.5,
        hydrophobicity_ibs=0.68,
        h_bond_capacity=4,
        charge_at_ph7=0.0,
        th_activity=0.7,
        iri_activity=4.2,
        hyperactivity=False,
        conservation_level="Highly conserved",
        phylogenetic_distribution=["Pleuronectidae"],
        mutable_residues=["A", "S", "D", "N", "K", "L"],
        forbidden_mutations=["T2*", "T13*", "T24*", "T35*"],
        design_rules=[
            "与HPLC6相同的Thr间距要求",
            "HPLC8通过非IBS区域的微小差异获得更高活性"
        ],
        pdb_id="1WFB",
        uniprot_id="P04003",
        pmid_list=["7638597"]
    ),

    # ========================
    # Type II AFP
    # ========================
    "IBS-TYPE2-Ca": IceBindingMotif(
        motif_id="IBS-TYPE2-Ca",
        name="Type II Ca²⁺-dependent ice-binding motif",
        afp_type=AFPType.TYPE_II,
        source_organism="Clupea harengus (herring)",
        sequence_pattern="D[^.]{1}T[^.]{1}L[^.]{1}E",
        repeat_unit="DxTxLxE (hexapeptide)",
        repeat_length=6,
        secondary_structure="C-type Lectin (3α+9β)",
        fold_family="C-type Lectin-like domain",
        ibs_residues=["D94", "T96", "T97", "L98", "T99", "E100"],
        ibs_positions=[94, 96, 97, 98, 99, 100],
        ibs_flatness_rmsd=1.2,
        target_ice_plane=IcePlane.PRISM,
        residue_spacing=4.5,
        hydrophobicity_ibs=0.45,
        h_bond_capacity=6,
        charge_at_ph7=-1.0,
        th_activity=0.5,
        iri_activity=5.0,
        hyperactivity=False,
        conservation_level="Highly conserved",
        phylogenetic_distribution=["Clupeidae", "Osmeridae"],
        mutable_residues=["S", "A", "G"],
        forbidden_mutations=["T96*", "T98*", "C* (5对二硫键)"],
        design_rules=[
            "T96, T98 不可突变（丧失活性）",
            "Ca²⁺配位残基(Q92, D94, E99, N113, D114)必须保留",
            "5对二硫键(Cys模式)不可破坏",
            "非IBS环区可插入表位或功能标签"
        ],
        pdb_id="2AFP",
        uniprot_id=None,
        pmid_list=["8918876"]
    ),

    # ========================
    # Type III AFP
    # ========================
    "IBS-TYPE3-QAE": IceBindingMotif(
        motif_id="IBS-TYPE3-QAE",
        name="Type III QAE β-sandwich flat surface motif",
        afp_type=AFPType.TYPE_III,
        source_organism="Macrozoarces americanus (ocean pout)",
        sequence_pattern="N[^.]{3}T[^.]{25}Q[^.]{1}N",
        repeat_unit="non-repetitive",
        repeat_length=66,
        secondary_structure="β-sandwich",
        fold_family="Orthogonal β-sandwich (pretzel fold)",
        ibs_residues=["Q9", "L10", "P12", "I13", "N14", "A16", "T18",
                       "L19", "V20", "M21", "Q44"],
        ibs_positions=[9, 10, 12, 13, 14, 16, 18, 19, 20, 21, 44],
        ibs_flatness_rmsd=0.6,
        target_ice_plane=IcePlane.PRISM,
        residue_spacing=4.5,
        hydrophobicity_ibs=0.55,
        h_bond_capacity=8,
        charge_at_ph7=0.0,
        th_activity=0.5,
        iri_activity=3.0,
        hyperactivity=False,
        conservation_level="Highly conserved",
        phylogenetic_distribution=["Zoarcidae"],
        mutable_residues=["S", "A", "G", "K", "E"],
        forbidden_mutations=["N14*", "T18*", "Q44*", "A16F", "A16W"],
        design_rules=[
            "N14, T18, Q44 绝对不可突变——任何一个突变都会完全丧失活性",
            "A16必须保持小体积(Gly/Ala/Ser)——IBS平坦性至关重要",
            "非IBS β-折叠面可耐受大量突变",
            "五残基簇(N14-A16-T18...Q44)形成冰锚定核心",
            "疏水残基(L10,I13,L19,V20,M21)提供van der Waals互补"
        ],
        pdb_id="1MSI",
        uniprot_id="P19414",
        pmid_list=["8639620", "10346894"]
    ),

    # ========================
    # 昆虫超活性 AFP
    # ========================
    "IBS-INSECT-TmAFP": IceBindingMotif(
        motif_id="IBS-INSECT-TmAFP",
        name="Tenebrio molitor β-helical Thr-X-Thr array motif",
        afp_type=AFPType.INSECT_HYPER,
        source_organism="Tenebrio molitor (yellow mealworm beetle)",
        sequence_pattern="T.CT",
        repeat_unit="TCT (Thr-Cys-Thr)",
        repeat_length=12,
        secondary_structure="β-helix (right-handed)",
        fold_family="Right-handed parallel β-helix",
        ibs_residues=["T"] * 48,
        ibs_positions=list(range(5, 261, 7)),
        ibs_flatness_rmsd=0.3,
        target_ice_plane=IcePlane.BASAL,
        residue_spacing=7.4,
        hydrophobicity_ibs=0.45,
        h_bond_capacity=48,
        charge_at_ph7=0.0,
        th_activity=5.5,
        iri_activity=0.5,
        hyperactivity=True,
        conservation_level="Highly conserved",
        phylogenetic_distribution=["Tenebrionidae", "Tortricidae"],
        mutable_residues=["S", "G"],
        forbidden_mutations=[
            "T5*", "T7*", "T9*", "T11*",
            "C6*", "C8*", "C10*", "C12*"
        ],
        design_rules=[
            "IBS面所有Thr均不可突变——间距7.4Å精确匹配基面",
            "Cys残基形成二硫键刚性化β-螺旋支架",
            "非IBS面可耐受插入以进行功能化",
            "超活性需要≥4个完整β-螺旋圈(≥48个Thr在IBS面)",
            "较短构建体(≤3圈)丧失超活性但可能保留中等TH"
        ],
        pdb_id="1EZG",
        uniprot_id="O16197",
        pmid_list=["10655467", "14526017"]
    ),

    "IBS-INSECT-sbwAFP": IceBindingMotif(
        motif_id="IBS-INSECT-sbwAFP",
        name="Spruce budworm β-helical (left-handed) AFP motif",
        afp_type=AFPType.INSECT_HYPER,
        source_organism="Choristoneura fumiferana (spruce budworm)",
        sequence_pattern="T.T",
        repeat_unit="TXT (Thr-X-Thr)",
        repeat_length=15,
        secondary_structure="β-helix (left-handed)",
        fold_family="Left-handed parallel β-helix",
        ibs_residues=["T"] * 24,
        ibs_positions=list(range(1, 100, 7)),
        ibs_flatness_rmsd=0.4,
        target_ice_plane=IcePlane.BASAL,
        residue_spacing=7.4,
        hydrophobicity_ibs=0.50,
        h_bond_capacity=24,
        charge_at_ph7=0.0,
        th_activity=4.5,
        iri_activity=1.0,
        hyperactivity=True,
        conservation_level="Highly conserved",
        phylogenetic_distribution=["Tortricidae"],
        mutable_residues=["S", "G", "A"],
        forbidden_mutations=["IBS面Thr*", "二硫键Cys*"],
        design_rules=[
            "左旋β-螺旋的TXT基序间距7.4Å",
            "二硫键对结构完整性至关重要"
        ],
        pdb_id="1M8N",
        uniprot_id=None,
        pmid_list=["14526017"]
    ),

    "IBS-INSECT-sfAFP": IceBindingMotif(
        motif_id="IBS-INSECT-sfAFP",
        name="Snow flea hyperactive polyproline-type AFP",
        afp_type=AFPType.INSECT_HYPER,
        source_organism="Hypogastrura harveyi (snow flea)",
        sequence_pattern="G[^.]{1}G[^.]{1}G",
        repeat_unit="GxGxG (polyproline-type)",
        repeat_length=6,
        secondary_structure="Polyproline type II helix",
        fold_family="Coiled-coil / superhelix",
        ibs_residues=["T16", "A19", "S22"],
        ibs_positions=[16, 19, 22],
        ibs_flatness_rmsd=0.5,
        target_ice_plane=IcePlane.BASAL,
        residue_spacing=7.4,
        hydrophobicity_ibs=0.40,
        h_bond_capacity=6,
        charge_at_ph7=0.0,
        th_activity=2.2,
        iri_activity=1.0,
        hyperactivity=True,
        conservation_level="Moderate",
        phylogenetic_distribution=["Hypogastruridae"],
        mutable_residues=["T16G", "A19G", "S22G"],
        forbidden_mutations=["破坏二聚化界面的突变"],
        design_rules=[
            "T16G/A19G/S22G三重突变体TH增强128%至5°C",
            "二聚化冰结合面优化是关键设计策略",
            "非经典polyproline型折叠——证明AFP折叠多样性"
        ],
        pdb_id="2PNE",
        uniprot_id=None,
        pmid_list=["2025_rational_design_SfAFP"]
    ),

    # ========================
    # 细菌 IBP
    # ========================
    "IBS-BACTERIAL-MaIBP": IceBindingMotif(
        motif_id="IBS-BACTERIAL-MaIBP",
        name="Marinomonas non-canonical Thr-free ice-binding site",
        afp_type=AFPType.BACTERIAL,
        source_organism="Marinomonas arctica (Arctic sea ice bacterium)",
        sequence_pattern="non-canonical",
        repeat_unit="non-repetitive",
        repeat_length=0,
        secondary_structure="β-sandwich (Ig-like)",
        fold_family="Immunoglobulin-like β-sandwich",
        ibs_residues=["G63"],
        ibs_positions=[63],
        ibs_flatness_rmsd=0.9,
        target_ice_plane=IcePlane.PRISM,
        residue_spacing=0.0,
        hydrophobicity_ibs=0.35,
        h_bond_capacity=2,
        charge_at_ph7=-1.0,
        th_activity=0.3,
        iri_activity=4.0,
        hyperactivity=False,
        conservation_level="Moderate",
        phylogenetic_distribution=["Marinomonas spp. (Arctic & Antarctic)"],
        mutable_residues=["G63S (+40%)", "G63A (+10%)"],
        forbidden_mutations=["G63D", "G63E", "G63K"],
        design_rules=[
            "G63位于冰结合界面——仅允许小型中性残基",
            "G63S通过引入羟基增强H-bond，活性+40%",
            "G63D/E/K引入负/正电荷排斥冰面",
            "非经典IBS——证明Thr并非必需",
            "趋同进化：北极和南极Marinomonas具有相似位点(28%序列一致性)"
        ],
        pdb_id="3WP9",
        uniprot_id=None,
        pmid_list=["41197692"]
    ),

    "IBS-BACTERIAL-Colwellia": IceBindingMotif(
        motif_id="IBS-BACTERIAL-Colwellia",
        name="Colwellia sp. hyperactive IBP",
        afp_type=AFPType.BACTERIAL,
        source_organism="Colwellia sp. (Antarctic bacterium)",
        sequence_pattern="T[^.]{2}T",
        repeat_unit="TxxT",
        repeat_length=0,
        secondary_structure="β-helix",
        fold_family="Parallel β-helix",
        ibs_residues=["T"] * 24,
        ibs_positions=[],  # 可变的
        ibs_flatness_rmsd=0.4,
        target_ice_plane=IcePlane.BASAL,
        residue_spacing=7.4,
        hydrophobicity_ibs=0.40,
        h_bond_capacity=24,
        charge_at_ph7=0.0,
        th_activity=3.8,
        iri_activity=0.8,
        hyperactivity=True,
        conservation_level="Moderate",
        phylogenetic_distribution=["Colwellia spp."],
        mutable_residues=["S", "A", "G"],
        forbidden_mutations=["IBS面Thr*"],
        design_rules=[
            "超活性细菌IBP——TH可达3.8°C",
            "β-螺旋支架与昆虫AFP趋同"
        ],
        pdb_id=None,
        uniprot_id=None,
        pmid_list=[]
    ),

    # ========================
    # 抗冻糖蛋白 AFGP
    # ========================
    "IBS-AFGP": IceBindingMotif(
        motif_id="IBS-AFGP",
        name="Antifreeze glycoprotein (Ala-Ala-Thr)n repeat motif",
        afp_type=AFPType.AFGP,
        source_organism="Dissostichus mawsoni (Antarctic cod)",
        sequence_pattern="AAT",
        repeat_unit="AAT (Ala-Ala-Thr)",
        repeat_length=3,
        secondary_structure="Polyproline type II / extended",
        fold_family="Disordered / PPII helix",
        ibs_residues=["T"] * 14,
        ibs_positions=list(range(3, 50, 3)),
        ibs_flatness_rmsd=1.5,
        target_ice_plane=IcePlane.PRISM,
        residue_spacing=4.5,
        hydrophobicity_ibs=0.55,
        h_bond_capacity=14,
        charge_at_ph7=0.0,
        th_activity=0.8,
        iri_activity=3.0,
        hyperactivity=False,
        conservation_level="Highly conserved",
        phylogenetic_distribution=["Notothenioidei", "Gadidae"],
        mutable_residues=["A→S", "A→G"],
        forbidden_mutations=["T* (Thr羟基和二糖修饰)"],
        design_rules=[
            "(Ala-Ala-Thr)n重复是AFGP的核心结构",
            "Thr的O-糖基化(二糖)是功能必需的",
            "重复次数n≥4才显示活性",
            "PPII螺旋结构提供冰结合面柔性匹配"
        ],
        pdb_id=None,
        uniprot_id=None,
        pmid_list=["25440715"]
    ),

    # ========================
    # 植物 AFP
    # ========================
    "IBS-PLANT-LpAFP": IceBindingMotif(
        motif_id="IBS-PLANT-LpAFP",
        name="Lolium perenne β-roll IRI-active AFP",
        afp_type=AFPType.PLANT,
        source_organism="Lolium perenne (perennial ryegrass)",
        sequence_pattern="N[^.]{5}V[^.]{5}G",
        repeat_unit="NxxxxxVxxxxxG",
        repeat_length=12,
        secondary_structure="β-roll (solenoid)",
        fold_family="β-roll / parallel β-helix",
        ibs_residues=["N1", "V7", "T12"],
        ibs_positions=[1, 7, 12],
        ibs_flatness_rmsd=0.6,
        target_ice_plane=IcePlane.PRISM,
        residue_spacing=4.5,
        hydrophobicity_ibs=0.50,
        h_bond_capacity=6,
        charge_at_ph7=-1.0,
        th_activity=0.2,
        iri_activity=0.5,
        hyperactivity=False,
        conservation_level="Highly conserved",
        phylogenetic_distribution=["Poaceae"],
        mutable_residues=["A", "S", "G"],
        forbidden_mutations=["N1*", "V7*", "T12*"],
        design_rules=[
            "高IRI但低TH——适合食品冷冻应用",
            "β-roll结构提供大而平坦的冰结合面",
            "Asn-Val-Thr三联体是IRI活性的关键"
        ],
        pdb_id="3ULT",
        uniprot_id="Q9FVC6",
        pmid_list=[]
    ),

    # ========================
    # 真菌 AFP
    # ========================
    "IBS-FUNGAL-TisAFP": IceBindingMotif(
        motif_id="IBS-FUNGAL-TisAFP",
        name="Typhula ishikariensis fungal AFP",
        afp_type=AFPType.FUNGAL,
        source_organism="Typhula ishikariensis (snow mold fungus)",
        sequence_pattern="T[^.]{4}G",
        repeat_unit="TxxxxG",
        repeat_length=6,
        secondary_structure="β-helix",
        fold_family="Parallel β-helix",
        ibs_residues=["T"] * 16,
        ibs_positions=[],  # variable
        ibs_flatness_rmsd=0.5,
        target_ice_plane=IcePlane.BASAL,
        residue_spacing=7.4,
        hydrophobicity_ibs=0.45,
        h_bond_capacity=16,
        charge_at_ph7=0.0,
        th_activity=1.5,
        iri_activity=1.5,
        hyperactivity=True,
        conservation_level="Moderate",
        phylogenetic_distribution=["Typhulaceae"],
        mutable_residues=["S", "A"],
        forbidden_mutations=["IBS面Thr*"],
        design_rules=[
            "真菌AFP的TH活性介于鱼源和昆虫AFP之间",
            "β-螺旋结构趋同于昆虫AFP"
        ],
        pdb_id=None,
        uniprot_id=None,
        pmid_list=[]
    ),

    "IBS-FUNGAL-LeIBP": IceBindingMotif(
        motif_id="IBS-FUNGAL-LeIBP",
        name="Leucosporidium fungal AFP (semi-pear-shaped β-helix)",
        afp_type=AFPType.FUNGAL,
        source_organism="Leucosporidium sp. (Antarctic yeast)",
        sequence_pattern="T[^.]{2}T",
        repeat_unit="TxxT",
        repeat_length=0,
        secondary_structure="β-helix (semi-pear-shaped)",
        fold_family="Right-handed β-helix + helical capping",
        ibs_residues=["T"] * 18,
        ibs_positions=[],
        ibs_flatness_rmsd=0.5,
        target_ice_plane=IcePlane.BASAL,
        residue_spacing=7.4,
        hydrophobicity_ibs=0.50,
        h_bond_capacity=18,
        charge_at_ph7=0.0,
        th_activity=1.8,
        iri_activity=1.2,
        hyperactivity=True,
        conservation_level="Moderate",
        phylogenetic_distribution=["Leucosporidiaceae"],
        mutable_residues=["S", "A", "G"],
        forbidden_mutations=["IBS面Thr*"],
        design_rules=[
            "半梨形β-螺旋——独特的几何冰结合面",
            "N端α-螺旋帽提供额外稳定性"
        ],
        pdb_id="3UYU",
        uniprot_id=None,
        pmid_list=[]
    ),

    # ========================
    # De Novo 设计的 AFP
    # ========================
    "IBS-DE-NOVO-iTHR": IceBindingMotif(
        motif_id="IBS-DE-NOVO-iTHR",
        name="De novo designed iTHR (ice-binding Twistless Helical Repeat)",
        afp_type=AFPType.DE_NOVO,
        source_organism="De novo designed (computational)",
        sequence_pattern="TXXXXXXXXXX",
        repeat_unit="Txxxxxxxxxx (11-mer)",
        repeat_length=11,
        secondary_structure="α-helix (parallel bundle)",
        fold_family="Twistless helical repeat",
        ibs_residues=["T"],
        ibs_positions=[1, 12, 23, 34],
        ibs_flatness_rmsd=0.5,
        target_ice_plane=IcePlane.PYRAMIDAL_201,
        residue_spacing=16.5,
        hydrophobicity_ibs=0.55,
        h_bond_capacity=4,
        charge_at_ph7=0.0,
        th_activity=0.0,
        iri_activity=0.97,
        hyperactivity=False,
        conservation_level="N/A (de novo)",
        phylogenetic_distribution=["N/A (de novo)"],
        mutable_residues=["All non-Thr positions"],
        forbidden_mutations=["T1*", "T12*", "T23*", "T34*"],
        design_rules=[
            "Thr间距11aa→16.5Å匹配{201}金字塔面",
            "仅几何互补即可驱动显著IRI活性",
            "TH对de novo设计仍然难以实现——可能需要更长的驻留时间",
            "a-iTHR-201实现IRI Cᵢ 0.97 µM vs野生型wfAFP 4.6 µM",
            "空间敲除(Thr→Glu, Ala→Glu on IBS)降低但不消除IRI",
            "非IBS面残基对IRI活性不重要"
        ],
        pdb_id=None,
        uniprot_id=None,
        pmid_list=["2025_bioRxiv_de_novo_iTHR"]
    ),

    "IBS-DE-NOVO-AFPT": IceBindingMotif(
        motif_id="IBS-DE-NOVO-AFPT",
        name="De novo AFPT (JACS 2025) — Glu-based super-binder",
        afp_type=AFPType.DE_NOVO,
        source_organism="De novo designed (computational)",
        sequence_pattern="E[^.]{n}E",  # Glu间距匹配冰晶格
        repeat_unit="E-based with precise spacing",
        repeat_length=0,
        secondary_structure="α-helix / designed",
        fold_family="Designed fold",
        ibs_residues=["E"],
        ibs_positions=[],
        ibs_flatness_rmsd=0.3,
        target_ice_plane=IcePlane.PRISM,
        residue_spacing=6.75,
        hydrophobicity_ibs=0.30,
        h_bond_capacity=8,
        charge_at_ph7=-2.0,
        th_activity=0.5,
        iri_activity=0.2,
        hyperactivity=False,
        conservation_level="N/A (de novo)",
        phylogenetic_distribution=["N/A (de novo)"],
        mutable_residues=["按设计规则调整间距"],
        forbidden_mutations=["E* (核心冰结合残基)"],
        design_rules=[
            "Glu(E)的结合能是天然IBS残基(Thr)的4倍以上",
            "位点间距离必须精确匹配冰晶格间距",
            "设计肽性能显著超过100+种天然和此前设计的AFP",
            "1.5×冰晶格间距(6.75Å)匹配策略"
        ],
        pdb_id=None,
        uniprot_id=None,
        pmid_list=["40358480"]
    ),
}


class AFPMotifLibrary:
    """AFP冰结合基序库 —— 查询和匹配"""

    def __init__(self):
        self.motifs = AFP_MOTIF_DATABASE

    def search_by_sequence(self, sequence: str) -> List[Dict]:
        """
        基于序列匹配已知基序
        使用滑动窗口+关键词匹配
        """
        results = []
        seq_upper = sequence.upper()

        for motif_id, motif in self.motifs.items():
            # 检查基序模式
            pattern_aa = self._pattern_to_search_terms(motif.sequence_pattern)
            match_score = 0

            for aa in pattern_aa:
                if aa in seq_upper:
                    match_score += 1

            # Thr含量匹配
            thr_pct = seq_upper.count('T') / max(len(seq_upper), 1)
            if motif.afp_type == AFPType.TYPE_I and thr_pct > 0.08:
                match_score += 2
            if motif.afp_type == AFPType.INSECT_HYPER and thr_pct > 0.10:
                match_score += 3
            if motif.afp_type == AFPType.TYPE_III:
                if 'N' in seq_upper and 'Q' in seq_upper and 'T' in seq_upper:
                    match_score += 2

            # Ala含量匹配（Type I特征）
            ala_pct = seq_upper.count('A') / max(len(seq_upper), 1)
            if motif.afp_type == AFPType.TYPE_I and ala_pct > 0.30:
                match_score += 2

            # Cys含量匹配（昆虫/细菌特征）
            cys_pct = seq_upper.count('C') / max(len(seq_upper), 1)
            if motif.hyperactivity and cys_pct > 0.05:
                match_score += 2

            if match_score > 0:
                results.append({
                    "motif_id": motif_id,
                    "name": motif.name,
                    "afp_type": motif.afp_type.value,
                    "source_organism": motif.source_organism,
                    "match_score": match_score,
                    "ibs_residues": motif.ibs_residues,
                    "ibs_positions": motif.ibs_positions,
                    "target_ice_plane": motif.target_ice_plane.value,
                    "th_activity": motif.th_activity,
                    "iri_activity": motif.iri_activity,
                    "hyperactivity": motif.hyperactivity,
                    "forbidden_mutations": motif.forbidden_mutations,
                    "design_rules": motif.design_rules,
                    "pdb_id": motif.pdb_id,
                })

        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results

    def search_by_type(self, afp_type: AFPType) -> List[IceBindingMotif]:
        """按AFP类型查询基序"""
        return [m for m in self.motifs.values() if m.afp_type == afp_type]

    def get_motif(self, motif_id: str) -> Optional[IceBindingMotif]:
        """获取指定ID的基序"""
        return self.motifs.get(motif_id)

    def get_all_motifs(self) -> Dict[str, IceBindingMotif]:
        """获取全部基序"""
        return self.motifs

    def get_design_rules_by_type(self, afp_type_str: str) -> List[str]:
        """按AFP类型获取设计规则"""
        rules = []
        for motif in self.motifs.values():
            if motif.afp_type.value == afp_type_str or motif.afp_type.name == afp_type_str:
                rules.extend(motif.design_rules)
        return list(set(rules))

    def get_all_forbidden_positions(self, afp_type_str: str) -> List[str]:
        """获取某类AFP的所有禁区（禁突变残基）"""
        forbidden = []
        for motif in self.motifs.values():
            if motif.afp_type.value == afp_type_str or motif.afp_type.name == afp_type_str:
                forbidden.extend(motif.forbidden_mutations)
        return list(set(forbidden))

    def _pattern_to_search_terms(self, pattern: str) -> List[str]:
        """将基序模式转换为搜索词"""
        # 提取模式中的关键氨基酸
        import re
        terms = re.findall(r'[A-Z]', pattern)
        return terms

    def get_summary_for_llm(self) -> str:
        """生成给LLM的基序库摘要"""
        lines = ["## AFP基序库摘要\n"]
        for motif_id, m in self.motifs.items():
            lines.append(f"- **{m.name}** ({m.afp_type.value})")
            lines.append(f"  IBS: {', '.join(m.ibs_residues[:5])}")
            lines.append(f"  TH: {m.th_activity}°C | IRI: {m.iri_activity} µM")
            lines.append(f"  靶向冰面: {m.target_ice_plane.value}")
            lines.append(f"  禁区: {', '.join(m.forbidden_mutations[:5])}")
            lines.append("")
        return "\n".join(lines)
