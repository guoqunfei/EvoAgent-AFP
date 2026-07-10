<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/appStore'
import { useApi } from '@/composables/useApi'
import SvgIcon from '@/components/common/SvgIcon.vue'
import type { IceBindingResult } from '@/types/api'

const store = useAppStore()
const api = useApi()

// ── Tab state ──
const activeTab = ref<'single' | 'batch' | 'compare'>('single')

// ── Single sequence simulation ──
const simSeq = ref('')
const simLoading = ref(false)
const simResult = ref<IceBindingResult | null>(null)
const simError = ref('')

async function runSingleSim() {
  const seq = simSeq.value.trim() || store.currentSequence
  if (!seq) return
  simLoading.value = true
  simError.value = ''
  simResult.value = null
  try {
    const res = await api.simulateIceBinding(seq)
    simResult.value = res.result
    store.setSimResult(res.result)
  } catch (e: any) {
    simError.value = e?.message || 'Simulation failed'
  } finally {
    simLoading.value = false
  }
}

// ── Batch test ──
const batchInput = ref('')
const batchLoading = ref(false)
const batchResults = ref<Array<{ sequence: string; geometryScore: number; thEstimate: number; iriEstimate: number; activityAssessment: string; rank: number }>>([])
const batchBest = ref('')
const batchError = ref('')

const batchSequences = computed(() => {
  return batchInput.value
    .split(/[\n,;]+/)
    .map(s => s.trim().toUpperCase())
    .filter(s => s.length >= 5 && /^[ACDEFGHIKLMNPQRSTVWY]+$/.test(s))
})

async function runBatch() {
  if (batchSequences.value.length < 2) {
    batchError.value = 'Enter at least 2 valid sequences (5+ aa each)'
    return
  }
  batchLoading.value = true
  batchError.value = ''
  batchResults.value = []
  try {
    const results: typeof batchResults.value = []
    for (const seq of batchSequences.value) {
      try {
        const res = await api.simulateIceBinding(seq)
        results.push({
          sequence: seq,
          geometryScore: res.result.geometryScore ?? 0,
          thEstimate: res.result.thEstimate ?? 0,
          iriEstimate: res.result.iriEstimate ?? 0,
          activityAssessment: res.result.activityAssessment ?? '',
          rank: 0,
        })
      } catch {
        // skip failed sequences
      }
    }
    results.sort((a, b) => b.geometryScore - a.geometryScore)
    results.forEach((r, i) => (r.rank = i + 1))
    batchResults.value = results
    batchBest.value = results[0]?.sequence ?? ''
  } catch (e: any) {
    batchError.value = e?.message || 'Batch test failed'
  } finally {
    batchLoading.value = false
  }
}

// ── Compare mode ──
const compareSeqA = ref('')
const compareSeqB = ref('')
const compareLoading = ref(false)
const compareResultA = ref<IceBindingResult | null>(null)
const compareResultB = ref<IceBindingResult | null>(null)
const compareError = ref('')

async function runCompare() {
  const a = compareSeqA.value.trim() || store.currentSequence
  const b = compareSeqB.value.trim()
  if (!a || !b) return
  compareLoading.value = true
  compareError.value = ''
  try {
    const [resA, resB] = await Promise.all([
      api.simulateIceBinding(a),
      api.simulateIceBinding(b, a),
    ])
    compareResultA.value = resA.result
    compareResultB.value = resB.result
  } catch (e: any) {
    compareError.value = e?.message || 'Comparison failed'
  } finally {
    compareLoading.value = false
  }
}

// ── Helpers ──
function deltaStr(a: number | undefined, b: number | undefined): string {
  if (a == null || b == null) return '—'
  const d = b - a
  const pct = a !== 0 ? ((d / Math.abs(a)) * 100) : 0
  const sign = d > 0 ? '+' : ''
  return `${sign}${d.toFixed(3)} (${sign}${pct.toFixed(1)}%)`
}

function deltaClass(a: number | undefined, b: number | undefined): string {
  if (a == null || b == null) return ''
  return b > a ? 'improved' : b < a ? 'declined' : ''
}

function truncSeq(s: string, max = 40): string {
  return s.length > max ? s.slice(0, max) + '…' : s
}
</script>

<template>
  <div class="simulation-view">
    <!-- Header -->
    <div class="sv-header">
      <div>
        <h2><SvgIcon name="ice" :size="20" /> Simulation</h2>
        <p class="text-muted text-sm">Ice-binding geometry scoring, TH/IRI prediction & batch comparison</p>
      </div>
    </div>

    <!-- Sub Tabs -->
    <div class="sv-subtabs">
      <button :class="['subtab-btn', { active: activeTab === 'single' }]" @click="activeTab = 'single'">
        <SvgIcon name="ice" :size="14" /> Single Sequence
      </button>
      <button :class="['subtab-btn', { active: activeTab === 'batch' }]" @click="activeTab = 'batch'">
        <SvgIcon name="chart" :size="14" /> Batch Test
      </button>
      <button :class="['subtab-btn', { active: activeTab === 'compare' }]" @click="activeTab = 'compare'">
        <SvgIcon name="target" :size="14" /> Compare
      </button>
    </div>

    <!-- ═══════════ SINGLE SEQUENCE ═══════════ -->
    <div v-if="activeTab === 'single'" class="sv-panel">
      <div class="card">
        <h4><SvgIcon name="ice" :size="16" /> Ice-Binding Simulation</h4>
        <p class="text-sm text-muted" style="margin-bottom:0.75rem;">
          Evaluate ice-binding geometry, predict TH (thermal hysteresis) and IRI (ice recrystallization inhibition) activity.
        </p>

        <div class="sim-input-row">
          <input
            v-model="simSeq"
            :placeholder="store.currentSequence || 'Enter AFP sequence...'"
            class="sim-seq-input"
            @keyup.enter="runSingleSim"
          />
          <button class="btn-primary" :disabled="simLoading || (!simSeq.trim() && !store.currentSequence)" @click="runSingleSim">
            <SvgIcon name="search" :size="14" />
            {{ simLoading ? 'Running...' : 'Simulate' }}
          </button>
        </div>

        <div v-if="!simSeq.trim() && store.currentSequence" class="text-xs text-muted" style="margin-top:0.35rem;">
          Will use current sequence: <code>{{ truncSeq(store.currentSequence) }}</code>
        </div>

        <!-- Loading -->
        <div v-if="simLoading" class="sim-loading">
          <span class="loading-spinner"></span> Computing geometry score & activity predictions...
        </div>

        <!-- Error -->
        <div v-if="simError" class="sim-error">{{ simError }}</div>
      </div>

      <!-- Results -->
      <div v-if="simResult" class="card sim-result-card fade-in">
        <h4><SvgIcon name="chart" :size="16" /> Simulation Results</h4>

        <div class="sim-scores-grid">
          <div class="sim-score-item">
            <div class="sim-score-ring" :style="{ '--pct': (simResult.geometryScore ?? 0) * 100 }">
              <span class="sim-score-val">{{ ((simResult.geometryScore ?? 0) * 100).toFixed(0) }}</span>
            </div>
            <span class="sim-score-label">Geometry Score</span>
          </div>
          <div class="sim-score-item">
            <span class="sim-score-big">{{ simResult.thEstimate?.toFixed(2) }}°C</span>
            <span class="sim-score-label">TH Activity</span>
          </div>
          <div class="sim-score-item">
            <span class="sim-score-big">{{ simResult.iriEstimate?.toFixed(2) }}µM</span>
            <span class="sim-score-label">IRI Activity</span>
          </div>
        </div>

        <div class="sim-detail-grid">
          <div class="sim-detail">
            <span class="sim-detail-label">Spacing Match</span>
            <div class="sim-bar-track"><div class="sim-bar geo" :style="{ width: Math.min((simResult.geometryScore ?? 0) * 100, 100) + '%' }"></div></div>
          </div>
          <div class="sim-detail">
            <span class="sim-detail-label">TH Activity</span>
            <div class="sim-bar-track"><div class="sim-bar th" :style="{ width: Math.min((simResult.thEstimate ?? 0) * 50, 100) + '%' }"></div></div>
          </div>
          <div class="sim-detail">
            <span class="sim-detail-label">IRI Activity</span>
            <div class="sim-bar-track"><div class="sim-bar iri" :style="{ width: Math.min((simResult.iriEstimate ?? 0) * 100, 100) + '%' }"></div></div>
          </div>
        </div>

        <div class="sim-assessment">
          <strong>Assessment:</strong> {{ simResult.activityAssessment }}
        </div>
      </div>
    </div>

    <!-- ═══════════ BATCH TEST ═══════════ -->
    <div v-if="activeTab === 'batch'" class="sv-panel">
      <div class="card">
        <h4><SvgIcon name="chart" :size="16" /> Batch Sequence Testing</h4>
        <p class="text-sm text-muted" style="margin-bottom:0.75rem;">
          Compare multiple sequences. Paste one per line, or comma/semicolon separated.
        </p>

        <textarea
          v-model="batchInput"
          placeholder="DTASDAAAAAALTAANAAAAAKLTADNAAAAAAATAR&#10;DTASDAAAAAALTANNAAAAAKLTADNAAAAAAATAR&#10;..."
          rows="5"
          class="batch-textarea"
        ></textarea>

        <div class="batch-actions">
          <span class="text-xs text-muted">{{ batchSequences.length }} valid sequences</span>
          <button
            class="btn-primary"
            :disabled="batchLoading || batchSequences.length < 2"
            @click="runBatch"
          >
            <SvgIcon name="play" :size="14" />
            {{ batchLoading ? 'Testing...' : `Run Batch (${batchSequences.length})` }}
          </button>
        </div>

        <div v-if="batchLoading" class="sim-loading">
          <span class="loading-spinner"></span> Testing {{ batchSequences.length }} sequences...
        </div>
        <div v-if="batchError" class="sim-error">{{ batchError }}</div>
      </div>

      <!-- Results Table -->
      <div v-if="batchResults.length" class="card fade-in">
        <h4>Batch Results ({{ batchResults.length }} sequences)</h4>
        <div class="table-wrap">
          <table class="sv-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Sequence</th>
                <th>Geometry</th>
                <th>TH (°C)</th>
                <th>IRI (µM)</th>
                <th>Assessment</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in batchResults" :key="r.sequence" :class="{ 'best-row': r.rank === 1 }">
                <td><span :class="['rank-badge', r.rank === 1 ? 'gold' : r.rank <= 3 ? 'silver' : '']">{{ r.rank }}</span></td>
                <td class="text-mono text-sm">{{ truncSeq(r.sequence, 50) }}</td>
                <td class="text-mono">{{ r.geometryScore.toFixed(3) }}</td>
                <td class="text-mono">{{ r.thEstimate.toFixed(2) }}</td>
                <td class="text-mono">{{ r.iriEstimate.toFixed(2) }}</td>
                <td class="text-sm">{{ r.activityAssessment }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ═══════════ COMPARE ═══════════ -->
    <div v-if="activeTab === 'compare'" class="sv-panel">
      <div class="card">
        <h4><SvgIcon name="target" :size="16" /> Compare Two Sequences</h4>
        <p class="text-sm text-muted" style="margin-bottom:0.75rem;">
          Compare ice-binding performance between original and mutant sequences.
        </p>

        <div class="compare-inputs">
          <div class="compare-field">
            <label class="input-label">Sequence A (Original)</label>
            <input
              v-model="compareSeqA"
              :placeholder="store.currentSequence || 'Original sequence...'"
              class="sim-seq-input"
            />
          </div>
          <div class="compare-vs">VS</div>
          <div class="compare-field">
            <label class="input-label">Sequence B (Mutant)</label>
            <input
              v-model="compareSeqB"
              placeholder="Mutant sequence..."
              class="sim-seq-input"
            />
          </div>
        </div>

        <div style="text-align:center;margin-top:0.75rem;">
          <button
            class="btn-primary"
            :disabled="compareLoading || !compareSeqB.trim()"
            @click="runCompare"
          >
            <SvgIcon name="search" :size="14" />
            {{ compareLoading ? 'Comparing...' : 'Compare' }}
          </button>
        </div>

        <div v-if="compareLoading" class="sim-loading">
          <span class="loading-spinner"></span> Running simulations...
        </div>
        <div v-if="compareError" class="sim-error">{{ compareError }}</div>
      </div>

      <!-- Comparison Results -->
      <div v-if="compareResultA && compareResultB" class="card fade-in">
        <h4>Comparison Results</h4>
        <table class="sv-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Sequence A</th>
              <th>Sequence B</th>
              <th>Delta</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="prop-name">Geometry Score</td>
              <td class="text-mono">{{ compareResultA.geometryScore?.toFixed(4) }}</td>
              <td class="text-mono">{{ compareResultB.geometryScore?.toFixed(4) }}</td>
              <td :class="['text-mono', deltaClass(compareResultA.geometryScore, compareResultB.geometryScore)]">
                {{ deltaStr(compareResultA.geometryScore, compareResultB.geometryScore) }}
              </td>
            </tr>
            <tr>
              <td class="prop-name">TH Activity</td>
              <td class="text-mono">{{ compareResultA.thEstimate?.toFixed(2) }}°C</td>
              <td class="text-mono">{{ compareResultB.thEstimate?.toFixed(2) }}°C</td>
              <td :class="['text-mono', deltaClass(compareResultA.thEstimate, compareResultB.thEstimate)]">
                {{ deltaStr(compareResultA.thEstimate, compareResultB.thEstimate) }}
              </td>
            </tr>
            <tr>
              <td class="prop-name">IRI Activity</td>
              <td class="text-mono">{{ compareResultA.iriEstimate?.toFixed(2) }}µM</td>
              <td class="text-mono">{{ compareResultB.iriEstimate?.toFixed(2) }}µM</td>
              <td :class="['text-mono', deltaClass(compareResultA.iriEstimate, compareResultB.iriEstimate)]">
                {{ deltaStr(compareResultA.iriEstimate, compareResultB.iriEstimate) }}
              </td>
            </tr>
          </tbody>
        </table>

        <div style="margin-top:0.75rem; display:flex; gap:1rem; flex-wrap:wrap;">
          <div class="sim-assessment" style="flex:1;">
            <strong>Sequence A:</strong> {{ compareResultA.activityAssessment }}
          </div>
          <div class="sim-assessment" style="flex:1;">
            <strong>Sequence B:</strong> {{ compareResultB.activityAssessment }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.simulation-view {
  padding: 1.5rem;
  max-width: 1100px;
}

.sv-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.sv-header h2 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.25rem;
}

/* Sub Tabs */
.sv-subtabs {
  display: flex;
  gap: 0.25rem;
  margin-bottom: 1.25rem;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  padding: 0.3rem;
  width: fit-content;
}

.subtab-btn {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.85rem;
  font-size: 0.78rem;
  font-weight: 500;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.subtab-btn:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.subtab-btn.active {
  background: var(--accent);
  color: #fff;
}

.sv-panel {
  animation: fadeIn 0.2s ease-out;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* ── Input ── */
.sim-input-row {
  display: flex;
  gap: 0.5rem;
}

.sim-seq-input {
  flex: 1;
  font-family: var(--font-mono);
  font-size: 0.82rem;
}

.batch-textarea {
  width: 100%;
  font-family: var(--font-mono);
  font-size: 0.78rem;
  line-height: 1.5;
}

.batch-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 0.6rem;
}

/* ── Loading / Error ── */
.sim-loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 0;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.loading-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.sim-error {
  padding: 0.6rem 0.75rem;
  margin-top: 0.5rem;
  background: #fef2f2;
  color: var(--danger);
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  border: 1px solid #fecaca;
}

/* ── Scores Grid ── */
.sim-scores-grid {
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 1.25rem 0;
  gap: 1rem;
  flex-wrap: wrap;
}

.sim-score-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
}

.sim-score-ring {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: conic-gradient(var(--accent-cyan) calc(var(--pct, 0) * 1%), #e5e7eb 0);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.sim-score-ring::before {
  content: '';
  position: absolute;
  inset: 6px;
  border-radius: 50%;
  background: var(--bg-card);
}

.sim-score-val {
  position: relative;
  z-index: 1;
  font-family: var(--font-mono);
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--accent-cyan);
}

.sim-score-big {
  font-family: var(--font-mono);
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--accent-cyan);
}

.sim-score-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
}

/* ── Detail bars ── */
.sim-detail-grid {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  margin-bottom: 0.75rem;
}

.sim-detail {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.sim-detail-label {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text-secondary);
  min-width: 100px;
}

.sim-bar-track {
  flex: 1;
  height: 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow: hidden;
}

.sim-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}

.sim-bar.geo { background: var(--accent); }
.sim-bar.th  { background: linear-gradient(90deg, var(--accent), var(--accent-cyan)); }
.sim-bar.iri { background: linear-gradient(90deg, #22d3ee, #06b6d4); }

.sim-assessment {
  padding: 0.75rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  line-height: 1.5;
}

/* ── Table ── */
.table-wrap {
  overflow-x: auto;
}

.sv-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
  margin-top: 0.5rem;
}

.sv-table th {
  text-align: left;
  padding: 0.5rem 0.65rem;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
  border-bottom: 2px solid var(--border-light);
  white-space: nowrap;
}

.sv-table td {
  padding: 0.45rem 0.65rem;
  border-bottom: 1px solid var(--border-light);
}

.best-row {
  background: #f0fdf4;
}

.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  font-size: 0.75rem;
  font-weight: 700;
  border-radius: 50%;
  font-family: var(--font-mono);
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.rank-badge.gold   { background: #fef3c7; color: #b45309; }
.rank-badge.silver { background: #e2e8f0; color: #475569; }

/* ── Compare ── */
.compare-inputs {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.compare-field {
  flex: 1;
}

.compare-field .input-label {
  display: block;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
  margin-bottom: 0.3rem;
}

.compare-vs {
  font-weight: 800;
  font-size: 0.85rem;
  color: var(--text-secondary);
  padding-top: 1.2rem;
}

.prop-name {
  font-weight: 600;
  color: var(--text-secondary);
  font-size: 0.75rem;
}

.improved { color: var(--success); font-weight: 700; }
.declined { color: var(--danger); font-weight: 700; }

/* ── Cards ── */
.sv-panel .card h4 {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
}
</style>
