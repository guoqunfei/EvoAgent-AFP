export interface Project {
  id: string
  name: string
  description: string
  sequence: string
  applicationScenario: string
  designTarget: string
  createdAt: string
}

export interface DesignRound {
  roundNumber: number
  status: string
  mutations: MutationRecord[]
  evaluation: EvaluationResult | null
  iceBindingSim: IceBindingResult | null
}

export interface MutationRecord {
  position: number
  from: string
  to: string
  rationale: string
}

export interface EvaluationResult {
  verdict: 'PASS' | 'CAUTION' | 'WARNING' | 'REJECTED'
  warnings: string[]
  errors: string[]
}

export interface IceBindingResult {
  geometryScore: number
  thEstimate: number
  iriEstimate: number
  activityAssessment: string
}

export interface KnowledgeEntry {
  id: string
  type: string
  title: string
  content: string
  tags: string[]
}

export interface KnowledgeMotif {
  motif_id: string
  name: string
  afp_type: string
  target_ice_plane: string
  source_organism: string
  th_activity: number
  iri_activity: number
  design_rules: string[]
}

export interface KnowledgeSummary {
  total_motifs: number
  total_principles: number
  total_mutation_findings: number
  supported_applications: string[]
  afp_types_covered: string[]
}

export interface DesignSkill {
  name: string
  description: string
  category: string
  rules: string[]
  confidence: number
  evidenceCount: number
}

export interface ChatMessage {
  id: string
  role: string
  content: string
  timestamp: string
}

export interface AFPRunRequest {
  sequence: string
  designTarget: string
  applicationScenario: string
  maxIterations: number
}

export interface StructureResidue {
  position: number
  amino_acid: string
  ss_type: string
  ss_confidence: number
  ibs_candidate: boolean
  ibs_confidence: number
  solvent_accessibility: string
}

export interface StructurePrediction {
  sequence: string
  sequence_length: number
  residues: StructureResidue[]
  ss_consensus: string
  ss_composition: Record<string, number>
  predicted_fold: string
  fold_confidence: number
  matching_afp_type: string | null
  ibs_positions: number[]
  ibs_flatness_score: number
  ibs_thr_spacing: number[]
  ala_content: number
  thr_content: number
  cys_content: number
  net_charge: number
  hydrophobicity: number
  structural_highlights: string[]
  design_notes: string[]
  pdb_data: string
  pdb_source: string
}

export interface MemoryStats {
  forbidden_zones: number
  forbidden_positions: number[]
  total_mutations_applied: number
}
