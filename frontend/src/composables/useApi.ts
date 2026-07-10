import type {
  KnowledgeEntry,
  KnowledgeMotif,
  KnowledgeSummary,
  DesignSkill,
  IceBindingResult,
  EvaluationResult,
  MemoryStats,
  AFPRunRequest,
  MutationRecord,
  StructurePrediction,
} from '@/types/api'

const BASE = '/api/v1/afp'
const CHAT_BASE = '/api/v1/chat'

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json()
}

async function chatFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${CHAT_BASE}${path}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json()
}

interface ChatSession {
  id: string
  title: string
  system_prompt: string
  created_at: string
  updated_at: string
}

interface ChatMessageResponse {
  session_id: string
  assistant_message_id: string
  answer: string
  provider: string
  model: string
  contexts: Array<{ chunk_id: string; content: string; score: number }>
}

export function useApi() {
  return {
    // ── Knowledge ──
    queryKnowledge: (seq: string, intent: string) =>
      apiFetch<{ results: KnowledgeEntry[] }>('/knowledge/query', {
        method: 'POST',
        body: JSON.stringify({ sequence: seq, query_intent: intent }),
      }),

    getKnowledgeSummary: () =>
      apiFetch<KnowledgeSummary>('/knowledge/summary'),

    getMotifs: () =>
      apiFetch<{ motifs: KnowledgeMotif[] }>('/knowledge/motifs'),

    // ── Tools ──
    mutateSequence: (seq: string, mutations: MutationRecord[]) =>
      apiFetch<{ mutated_sequence: string }>('/tools/mutate', {
        method: 'POST',
        body: JSON.stringify({ original_sequence: seq, mutations }),
      }),

    evaluateMutation: (
      original: string,
      mutated: string,
      mutations: MutationRecord[]
    ) =>
      apiFetch<{ evaluation: EvaluationResult }>('/tools/evaluate', {
        method: 'POST',
        body: JSON.stringify({
          original_sequence: original,
          mutated_sequence: mutated,
          mutations,
        }),
      }),

    simulateIceBinding: (seq: string, original?: string) =>
      apiFetch<{ result: IceBindingResult }>('/tools/simulate', {
        method: 'POST',
        body: JSON.stringify({ sequence: seq, original_sequence: original }),
      }),

    // ── Design ──
    runDesign: (req: AFPRunRequest) =>
      apiFetch<{ design_id: string }>('/design', {
        method: 'POST',
        body: JSON.stringify(req),
      }),

    runLocalDesign: (req: AFPRunRequest) =>
      apiFetch<{ design_id: string }>('/design/local', {
        method: 'POST',
        body: JSON.stringify(req),
      }),

    // ── Memory ──
    getMemoryStats: () =>
      apiFetch<MemoryStats>('/memory/stats'),

    getForbiddenZones: () =>
      apiFetch<{ zones: number[] }>('/memory/forbidden-zones'),

    // ── Structure ──
    predictStructure: (seq: string) =>
      apiFetch<StructurePrediction>('/structure/predict', {
        method: 'POST',
        body: JSON.stringify({ sequence: seq }),
      }),

    fetchPdb: (seq: string) =>
      apiFetch<{ pdb: string; source: string }>('/structure/pdb', {
        method: 'POST',
        body: JSON.stringify({ sequence: seq }),
      }),

    // ── Skills ──
    getSkills: () =>
      apiFetch<{ skills: DesignSkill[] }>('/skills'),

    // ── Chat ──
    createChatSession: (title?: string) =>
      chatFetch<ChatSession>('/sessions', {
        method: 'POST',
        body: JSON.stringify({
          title: title || 'AFP Design Chat',
          system_prompt: `You are an antifreeze protein (AFP) design expert AI assistant. You help users understand AFP structure, ice-binding mechanisms, mutation strategies, and design principles.

Key knowledge areas:
- Five major AFP structural classes (Type I α-helix, Type II C-lectin, Type III β-sandwich, Type IV 4-helix bundle, insect β-helix hyperactive)
- Ice-binding surface (IBS) design: geometric complementarity, hydrogen bond matching, hydrophobic complementarity
- Core activity metrics: Thermal Hysteresis (TH) and Ice Recrystallization Inhibition (IRI)
- Ice plane specificity: basal {0001}, prism {10-10}, pyramidal {20-21}/{11-20}
- Design constraints: Thr spacing rules, IBS flatness requirements, forbidden mutation zones
- Application scenarios: food freezing, cell cryopreservation, organ preservation, anti-ice coatings

Answer questions concisely with scientific accuracy. When discussing mutations, always reference specific residue positions and their functional impact.`,
        }),
      }),

    sendChatMessage: (sessionId: string, message: string) =>
      chatFetch<ChatMessageResponse>(`/sessions/${sessionId}/messages`, {
        method: 'POST',
        body: JSON.stringify({
          message,
          use_rag: false,
        }),
      }),

    // ── Models ──
    listChatModels: () =>
      chatFetch<{ models: Array<{ id: string; label: string; model: string; ready: boolean }>; default: string }>('/models'),

    /** Stream chat response via SSE. Returns { abort, readChunks }. */
    streamChatMessage: (sessionId: string, message: string, modelKey?: string) => {
      const controller = new AbortController()

      async function* readChunks(): AsyncGenerator<{ type: string; content?: string; finish_reason?: string; message?: string }> {
        const res = await fetch(`${CHAT_BASE}/sessions/${sessionId}/messages/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message, use_rag: false, model_key: modelKey }),
          signal: controller.signal,
        })
        if (!res.ok) {
          const text = await res.text()
          throw new Error(`Stream ${res.status}: ${text}`)
        }
        const reader = res.body!.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''
          for (const line of lines) {
            const trimmed = line.trim()
            if (!trimmed || !trimmed.startsWith('data: ')) continue
            const dataStr = trimmed.slice(6)
            if (dataStr === '[DONE]') return
            try {
              const data = JSON.parse(dataStr)
              yield data
            } catch {
              // skip unparseable lines
            }
          }
        }
      }

      return { abort: () => controller.abort(), readChunks }
    },

    /** Compare responses from multiple models for the same message. */
    compareModels: (message: string, modelKeys?: string[]) =>
      chatFetch<{
        message: string
        results: Array<{
          model_key: string
          model_name: string
          provider: string
          response: string
          success: boolean
          error_message: string | null
          latency_ms: number | null
        }>
        total_models: number
        successful: number
        failed: number
      }>('/compare-models', {
        method: 'POST',
        body: JSON.stringify({
          message,
          model_keys: modelKeys,
        }),
      }),

    // ── AFP Chat (streaming) — replaces CLI interactive mode ──
    /** Stream AFP design chat via SSE. Returns { abort, readChunks }.
     *  Events: chunk, round_start, tool_call, tool_result, done, error */
    streamAfpChat: (message: string, sequence?: string) => {
      const controller = new AbortController()

      async function* readChunks(): AsyncGenerator<{
        type: string; content?: string; tool?: string; args?: Record<string, unknown>;
        result?: Record<string, unknown>; message?: string; round?: number; total?: number
      }> {
        const res = await fetch(`${BASE}/chat/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message, sequence: sequence || null }),
          signal: controller.signal,
        })
        if (!res.ok) {
          const text = await res.text()
          throw new Error(`AFP Stream ${res.status}: ${text}`)
        }
        const reader = res.body!.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''
          for (const line of lines) {
            const trimmed = line.trim()
            if (!trimmed || !trimmed.startsWith('data: ')) continue
            const dataStr = trimmed.slice(6)
            if (dataStr === '[DONE]') return
            try {
              const data = JSON.parse(dataStr)
              yield data
            } catch {
              // skip unparseable lines
            }
          }
        }
      }

      return { abort: () => controller.abort(), readChunks }
    },

    // ── Session management ──
    createSession: (title?: string) =>
      chatFetch<{ id: string; title: string }>('/sessions', {
        method: 'POST',
        body: JSON.stringify({ title: title || 'Chat Session' }),
      }),

    listSessions: () =>
      apiFetch<{ sessions: Array<{ session_id: string; created_at: string; directory: string }> }>('/sessions'),

    getSession: (sessionId: string) =>
      apiFetch<{ session_id: string; summary?: Record<string, unknown>; rounds?: Record<string, unknown>; analysis?: Record<string, unknown> }>(`/sessions/${sessionId}`),

    deleteSession: (sessionId: string) =>
      apiFetch<{ success: boolean; message: string }>(`/sessions/${encodeURIComponent(sessionId)}`, { method: 'DELETE' }),

    // ── Knowledge entries (editable) ──
    listKnowledgeEntries: () =>
      apiFetch<{ entries: KnowledgeMotif[]; custom_count: number }>('/knowledge/entries'),

    createKnowledgeEntry: (entry: Partial<KnowledgeMotif>) =>
      apiFetch<{ success: boolean; entry: KnowledgeMotif }>('/knowledge/entries', {
        method: 'POST',
        body: JSON.stringify(entry),
      }),

    updateKnowledgeEntry: (id: string, entry: Partial<KnowledgeMotif>) =>
      apiFetch<{ success: boolean; entry: KnowledgeMotif }>(`/knowledge/entries/${encodeURIComponent(id)}`, {
        method: 'PUT',
        body: JSON.stringify(entry),
      }),

    deleteKnowledgeEntry: (id: string) =>
      apiFetch<{ success: boolean }>(`/knowledge/entries/${encodeURIComponent(id)}`, {
        method: 'DELETE',
      }),

    // ── Skill files ──
    listSkillFiles: () =>
      apiFetch<{ skills: Array<{ name: string; description: string; version: string; path: string; content: string }> }>('/skills-files'),

    getSkillFile: (name: string) =>
      apiFetch<{ name: string; description: string; version: string; path: string; content: string }>(`/skills-files/${encodeURIComponent(name)}`),

    updateSkillFile: (name: string, content: string) =>
      apiFetch<{ success: boolean; message: string }>(`/skills-files/${encodeURIComponent(name)}`, {
        method: 'PUT',
        body: JSON.stringify({ content }),
      }),

    deleteSkillFile: (name: string) =>
      apiFetch<{ success: boolean; message: string }>(`/skills-files/${encodeURIComponent(name)}`, {
        method: 'DELETE',
      }),

    // ── Batch Processing ──
    /** Process multiple AFP sequences in batch */
    batchProcessSequences: (
      sequences: Array<{ sequence_id: string; sequence: string; analysis_prompt?: string }>,
      modelKey?: string,
      analysisType: 'quick' | 'comprehensive' = 'comprehensive',
      concurrentLimit: number = 5
    ) =>
      chatFetch<{
        batch_id: string
        status: string
        total_sequences: number
        successful: number
        failed: number
        skipped: number
        results: Array<{
          sequence_id: string
          sequence: string
          analysis: string
          success: boolean
          error_message: string | null
          processing_time_ms: number | null
          model_used: string | null
        }>
        total_processing_time_ms: number | null
        created_at: string
      }>('/batch/process', {
        method: 'POST',
        body: JSON.stringify({
          sequences,
          model_key: modelKey,
          analysis_type: analysisType,
          concurrent_limit: concurrentLimit,
        }),
      }),

    /** Get batch processing status */
    getBatchStatus: (batchId: string) =>
      chatFetch<{
        batch_id: string
        status: string
        progress: number
        total_sequences: number
        processed: number
        successful: number
        failed: number
        current_sequence: string | null
        estimated_remaining_seconds: number | null
        created_at: string
        completed_at: string | null
      }>(`/batch/${batchId}/status`),

    /** Export batch results as CSV or JSON */
    exportBatchResults: (batchId: string, format: 'csv' | 'json' = 'csv') => {
      const url = `${CHAT_BASE}/batch/${batchId}/export?format=${format}`
      window.open(url, '_blank')
    },
  }
}
