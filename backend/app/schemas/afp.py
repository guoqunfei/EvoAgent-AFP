"""AFPAgent API Schemas - 抗冻蛋白智能设计"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List


class AFPKnowledgeQueryRequest(BaseModel):
    sequence: str = Field(..., min_length=5, description="抗冻蛋白氨基酸序列")
    query_intent: str = Field(default="full_analysis", description="查询意图")
    application_scenario: str = Field(default="general", description="应用场景")

class AFPKnowledgeQueryResponse(BaseModel):
    afp_type: Optional[str] = None
    confidence: float = 0.0
    matched_motifs: list = Field(default_factory=list)
    ibs_residues: list = Field(default_factory=list)
    mutation_candidates: list = Field(default_factory=list)
    forbidden_regions: list = Field(default_factory=list)
    design_principles: list = Field(default_factory=list)
    summary: str = ""

class AFPKnowledgeSummaryResponse(BaseModel):
    total_motifs: int = 0
    total_principles: int = 0
    total_mutation_findings: int = 0
    supported_applications: list = Field(default_factory=list)
    afp_types_covered: list = Field(default_factory=list)

class AFPMotifInfoResponse(BaseModel):
    motif_id: str
    name: str
    afp_type: str
    source_organism: str
    th_activity: float
    iri_activity: float
    target_ice_plane: str
    design_rules: list = Field(default_factory=list)

class MutationItem(BaseModel):
    position: int
    from_aa: str
    to_aa: str

class AFPSequenceMutateRequest(BaseModel):
    original_sequence: str
    mutations: List[MutationItem] = Field(..., max_length=3)
    rationale: str = ""

class AFPSequenceMutateResponse(BaseModel):
    original_sequence: str
    mutated_sequence: str
    mutations: list = Field(default_factory=list)
    mutation_description: str = ""

class AFPEvaluateMutationRequest(BaseModel):
    original_sequence: str
    mutated_sequence: str
    mutations: List[MutationItem]
    application_scenario: str = "general"

class AFPEvaluateMutationResponse(BaseModel):
    verdict: str  # PASS / CAUTION / WARNING / REJECTED
    overall_assessment: str = ""
    warnings: list = Field(default_factory=list)
    errors: list = Field(default_factory=list)
    suggestions: list = Field(default_factory=list)

class AFPIceBindingSimulateRequest(BaseModel):
    sequence: str
    original_sequence: Optional[str] = None
    ibs_positions: Optional[List[int]] = None
    target_ice_plane: str = "auto"

class AFPIceBindingSimulateResponse(BaseModel):
    sequence_length: int
    overall_geometry_score: float
    spacing_match_score: float
    residue_quality_score: float
    flatness_prediction: float
    estimated_th_activity_C: float
    estimated_iri_activity_uM: float
    net_charge: float
    cys_content_pct: float
    thr_content_pct: float
    activity_assessment: str
    design_quality: str
    comparison: Optional[dict] = None

class AFPDesignRequest(BaseModel):
    sequence: str = Field(..., min_length=10, description="AFP氨基酸序列")
    design_target: str = Field(..., description="设计目标描述")
    application_scenario: str = Field(default="general")
    constraints: Optional[str] = None
    max_iterations: int = Field(default=10, ge=1, le=30)
    save_report: bool = False
    project_id: Optional[str] = None

class AFPDesignResponse(BaseModel):
    success: bool = True
    message: str = ""
    report_markdown: Optional[str] = None
    run_id: Optional[str] = None

class AFPBatchTestRequest(BaseModel):
    sequences: List[str] = Field(..., min_length=1, max_length=50)
    design_target: str = ""
    application_scenario: str = "general"

class AFPBatchTestResult(BaseModel):
    sequence: str
    geometry_score: float
    estimated_th: float
    estimated_iri: float
    activity_assessment: str
    rank: int

class AFPBatchTestResponse(BaseModel):
    results: List[AFPBatchTestResult]
    best_sequence: Optional[str] = None
    summary: str = ""

class AFPChatRequest(BaseModel):
    message: str
    sequence: Optional[str] = None
    conversation_id: Optional[str] = None

class AFPChatResponse(BaseModel):
    content: str
    intent: str = "chat"  # chat or design

class AFPMemoryStatsResponse(BaseModel):
    total_experiments: int = 0
    success_count: int = 0
    success_rate: float = 0.0
    forbidden_zones_count: int = 0
    success_patterns_count: int = 0
    top_mutations: list = Field(default_factory=list)
    experiments_by_target: dict = Field(default_factory=dict)

class AFPSkillListResponse(BaseModel):
    skills: list = Field(default_factory=list)
    total_count: int = 0


# ---- Structure Prediction ----

class StructurePredictRequest(BaseModel):
    sequence: str = Field(..., min_length=5, description="Amino acid sequence")

class ResidueAnnotationSchema(BaseModel):
    position: int
    amino_acid: str
    ss_type: str
    ss_confidence: float
    ibs_candidate: bool
    ibs_confidence: float
    solvent_accessibility: str

class StructurePredictResponse(BaseModel):
    sequence: str
    sequence_length: int
    residues: List[ResidueAnnotationSchema] = Field(default_factory=list)
    ss_consensus: str = ""
    ss_composition: dict = Field(default_factory=dict)
    predicted_fold: str = ""
    fold_confidence: float = 0.0
    matching_afp_type: Optional[str] = None
    ibs_positions: List[int] = Field(default_factory=list)
    ibs_flatness_score: float = 0.0
    ibs_thr_spacing: List[float] = Field(default_factory=list)
    ala_content: float = 0.0
    thr_content: float = 0.0
    cys_content: float = 0.0
    net_charge: float = 0.0
    hydrophobicity: float = 0.0
    structural_highlights: List[str] = Field(default_factory=list)
    design_notes: List[str] = Field(default_factory=list)
    pdb_data: str = ""
    pdb_source: str = ""
