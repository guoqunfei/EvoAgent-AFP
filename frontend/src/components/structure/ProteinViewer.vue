<script setup lang="ts">
import { ref, watch, nextTick, onUnmounted, computed } from 'vue'
import { useApi } from '@/composables/useApi'
import type { StructurePrediction, StructureResidue } from '@/types/api'
import SvgIcon from '@/components/common/SvgIcon.vue'

const props = defineProps<{
  sequence: string
}>()

const emit = defineEmits<{
  (e: 'loaded', data: StructurePrediction): void
  (e: 'error', err: string): void
}>()

const api = useApi()

// ── State ──
const structureData = ref<StructurePrediction | null>(null)
const loading = ref(false)
const pdbLoading = ref(false)
const error = ref('')
const activePanel = ref<'viewer' | 'residues' | 'properties'>('viewer')
const pdbSource = ref('')
const nglContainer = ref<HTMLElement | null>(null)
let nglStage: any = null

// ── Computed ──
const hasStructure = computed(() => structureData.value !== null)
const ssConsensus = computed(() => structureData.value?.ss_consensus ?? '')

const ssComposition = computed(() => {
  const comp = structureData.value?.ss_composition
  if (!comp) return { H: 0, E: 0, T: 0, C: 0 }
  return {
    H: ((comp.H ?? 0) * 100).toFixed(0),
    E: ((comp.E ?? 0) * 100).toFixed(0),
    T: ((comp.T ?? 0) * 100).toFixed(0),
    C: ((comp.C ?? 0) * 100).toFixed(0),
  }
})

const ibsResidueMap = computed(() => {
  const set = new Set(structureData.value?.ibs_positions ?? [])
  return set
})

const ssTypeLabel = (ss: string): string => {
  const map: Record<string, string> = { H: 'α-Helix', E: 'β-Sheet', T: 'Turn', C: 'Coil' }
  return map[ss] ?? ss
}

const ssColorClass = (ss: string): string => {
  const map: Record<string, string> = { H: 'helix', E: 'sheet', T: 'loop', C: 'coil' }
  return map[ss] ?? 'coil'
}

const accessibilityLabel = (acc: string): string => {
  const map: Record<string, string> = { buried: 'Buried', exposed: 'Exposed', surface: 'Surface' }
  return map[acc] ?? acc
}

// ── Load structure data ──
async function loadStructure() {
  if (!props.sequence || loading.value) return
  loading.value = true
  error.value = ''

  try {
    structureData.value = await api.predictStructure(props.sequence)
    emit('loaded', structureData.value)

    // Auto-render 3D if viewer panel is active
    if (activePanel.value === 'viewer' && structureData.value?.pdb_data) {
      await nextTick()
      await renderNgl(structureData.value.pdb_data, structureData.value.pdb_source)
    }
  } catch (e: any) {
    const msg = e?.message || String(e) || 'Failed to load structure'
    error.value = msg
    structureData.value = null
    emit('error', msg)
  } finally {
    loading.value = false
  }
}

// ── NGL 3D rendering ──
async function renderNgl(pdbData: string, source: string = '') {
  pdbSource.value = source
  pdbLoading.value = true

  // Clean up previous stage
  if (nglStage) {
    nglStage.dispose()
    nglStage = null
  }

  try {
    const NGL = await import('ngl')
    if (!nglContainer.value) {
      pdbLoading.value = false
      return
    }

    nglStage = new NGL.Stage(nglContainer.value, {
      backgroundColor: '#f0f5fb',
    })

    // Handle resize
    new ResizeObserver(() => {
      try { nglStage?.handleResize() } catch { /* ignore */ }
    }).observe(nglContainer.value)

    // Load PDB from blob
    const blob = new Blob([pdbData], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const comp: any = await nglStage.loadFile(url, {
      ext: 'pdb',
      defaultRepresentation: true,
    })
    URL.revokeObjectURL(url)

    // Add cartoon representation for better visualization
    comp.addRepresentation('cartoon', {
      color: 'sstruc',
      aspectRatio: 4,
      scale: 1.2,
    })

    // Add ice-binding surface highlights as licorice
    if (structureData.value?.ibs_positions?.length) {
      const ibsSelection = structureData.value.ibs_positions
        .map((p) => `${p}:${structureData.value!.sequence[p - 1]}`)
        .join(' or ')
      if (ibsSelection) {
        comp.addRepresentation('ball+stick', {
          sele: ibsSelection,
          color: 'cyan',
          aspectRatio: 1.8,
          scale: 1.5,
        })
      }
    }

    comp.autoView(800)
    pdbLoading.value = false
  } catch (e: any) {
    console.warn('NGL rendering failed:', e)
    pdbLoading.value = false
  }
}

// ── Panel switching ──
async function switchPanel(panel: 'viewer' | 'residues' | 'properties') {
  activePanel.value = panel

  if (panel === 'viewer' && structureData.value?.pdb_data && !nglStage) {
    await nextTick()
    await renderNgl(structureData.value.pdb_data, structureData.value.pdb_source)
  }
}

// ── Retry ──
async function retry() {
  error.value = ''
  await loadStructure()
}

// ── Watchers ──
watch(() => props.sequence, () => {
  // Clean up
  structureData.value = null
  error.value = ''
  pdbSource.value = ''
  if (nglStage) {
    nglStage.dispose()
    nglStage = null
  }
}, { immediate: false })

// ── Cleanup ──
onUnmounted(() => {
  if (nglStage) {
    nglStage.dispose()
    nglStage = null
  }
})

// ── Expose ──
defineExpose({ loadStructure, structureData, reload: retry })
</script>

<template>
  <div class="protein-viewer">
    <!-- ===== Loading State ===== -->
    <div v-if="loading" class="pv-loading">
      <span class="loading-spinner"></span>
      <span>Analyzing protein structure...</span>
      <span class="text-xs text-muted">Chou-Fasman prediction + ESMFold 3D model</span>
    </div>

    <!-- ===== Error State ===== -->
    <div v-else-if="error" class="pv-error">
      <div class="pv-error-card">
        <SvgIcon name="chart" :size="48" class="pv-error-icon" />
        <h4>Structure Unavailable</h4>
        <p class="text-sm text-muted">{{ error }}</p>
        <button class="btn-secondary" @click="retry">
          <SvgIcon name="refresh" :size="12" /> Retry
        </button>
      </div>
    </div>

    <!-- ===== Empty State ===== -->
    <div v-else-if="!hasStructure" class="pv-empty">
      <SvgIcon name="target" :size="48" class="pv-empty-icon" />
      <p class="text-sm text-muted">Click <strong>"Predict Structure"</strong> to analyze the protein sequence</p>
      <button class="btn-primary" @click="loadStructure">
        <SvgIcon name="search" :size="14" /> Predict Structure
      </button>
    </div>

    <!-- ===== Structure Content ===== -->
    <template v-else-if="structureData">
      <!-- ── Panel Tabs ── -->
      <div class="pv-tabs">
        <button
          v-for="tab in [
            { id: 'viewer' as const, label: '3D Viewer', icon: 'ice' },
            { id: 'residues' as const, label: 'Residue Table', icon: 'dna' },
            { id: 'properties' as const, label: 'Properties', icon: 'chart' },
          ]"
          :key="tab.id"
          :class="['pv-tab', { active: activePanel === tab.id }]"
          @click="switchPanel(tab.id)"
        >
          <SvgIcon :name="tab.icon" :size="14" />
          {{ tab.label }}
        </button>
      </div>

      <!-- ═══════════════ 3D VIEWER PANEL ═══════════════ -->
      <div v-if="activePanel === 'viewer'" class="pv-panel">
        <!-- NGL Viewport -->
        <div class="ngl-viewport">
          <!-- Loading overlay for PDB -->
          <div v-if="pdbLoading" class="ngl-overlay">
            <span class="loading-spinner"></span>
            <span>Rendering 3D structure...</span>
          </div>
          <!-- NGL container -->
          <div ref="nglContainer" class="ngl-stage"></div>
          <!-- Source badge -->
          <div v-if="pdbSource && !pdbLoading" class="ngl-badge">
            {{ pdbSource }}
          </div>
        </div>

        <!-- Secondary Structure Bar -->
        <div class="ss-section">
          <div class="ss-header">
            <span class="ss-title">Secondary Structure</span>
            <span class="text-xs text-muted">Chou-Fasman prediction</span>
          </div>
          <div class="ss-track">
            <span
              v-for="(r, i) in structureData.residues"
              :key="i"
              :class="['ss-block', ssColorClass(r.ss_type)]"
              :title="`${r.amino_acid}${r.position}: ${ssTypeLabel(r.ss_type)} (${(r.ss_confidence * 100).toFixed(0)}% conf.)`"
            ></span>
          </div>
          <div class="ss-legend">
            <span v-for="item in [
              { cls: 'helix', label: 'α-Helix', pct: ssComposition.H },
              { cls: 'sheet', label: 'β-Sheet', pct: ssComposition.E },
              { cls: 'loop', label: 'Turn', pct: ssComposition.T },
              { cls: 'coil', label: 'Coil', pct: ssComposition.C },
            ]" :key="item.cls" class="ss-legend-item">
              <span :class="['ss-swatch', item.cls]"></span>
              {{ item.label }} {{ item.pct }}%
            </span>
          </div>
        </div>

        <!-- Quick Insights Row -->
        <div class="pv-insights-row">
          <div class="pv-insight">
            <span class="pv-insight-label">Predicted Fold</span>
            <span class="pv-insight-val">
              {{ structureData.predicted_fold }}
              <span v-if="structureData.fold_confidence > 0" class="confidence-chip">
                {{ (structureData.fold_confidence * 100).toFixed(0) }}%
              </span>
            </span>
          </div>
          <div class="pv-insight">
            <span class="pv-insight-label">AFP Type</span>
            <span class="pv-insight-val match">
              {{ structureData.matching_afp_type || 'Not identified' }}
            </span>
          </div>
          <div class="pv-insight">
            <span class="pv-insight-label">IBS Positions</span>
            <span class="pv-insight-val">
              <span
                v-for="pos in structureData.ibs_positions.slice(0, 8)"
                :key="pos"
                class="ibs-pos-tag"
              >{{ structureData.sequence[pos - 1] }}{{ pos }}</span>
              <span v-if="structureData.ibs_positions.length > 8" class="text-xs text-muted">
                +{{ structureData.ibs_positions.length - 8 }} more
              </span>
            </span>
          </div>
          <div class="pv-insight">
            <span class="pv-insight-label">IBS Flatness</span>
            <span class="pv-insight-val">
              <span :class="structureData.ibs_flatness_score >= 0.7 ? 'text-success' : structureData.ibs_flatness_score >= 0.4 ? 'text-warning' : 'text-danger'">
                {{ (structureData.ibs_flatness_score * 100).toFixed(0) }}%
              </span>
            </span>
          </div>
        </div>
      </div>

      <!-- ═══════════════ RESIDUE TABLE PANEL ═══════════════ -->
      <div v-if="activePanel === 'residues'" class="pv-panel">
        <div class="residue-table-wrapper">
          <!-- Column toggles -->
          <div class="rt-toggles">
            <span class="text-xs text-muted">Show columns:</span>
            <label v-for="col in [
              { key: 'position', label: 'Pos' },
              { key: 'amino_acid', label: 'AA' },
              { key: 'ss_type', label: 'SS' },
              { key: 'ss_confidence', label: 'SS Conf' },
              { key: 'ibs_candidate', label: 'IBS' },
              { key: 'ibs_confidence', label: 'IBS Conf' },
              { key: 'solvent_accessibility', label: 'Access' },
            ]" :key="col.key" class="rt-toggle">
              <input type="checkbox" checked disabled>
              <span>{{ col.label }}</span>
            </label>
          </div>

          <!-- Table -->
          <table class="rt-table">
            <thead>
              <tr>
                <th>#</th>
                <th>AA</th>
                <th>SS</th>
                <th>SS Conf</th>
                <th>IBS</th>
                <th>IBS Conf</th>
                <th>Solvent</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="r in structureData.residues"
                :key="r.position"
                :class="['rt-row', {
                  'ibs-row': ibsResidueMap.has(r.position),
                  'row-helix': r.ss_type === 'H',
                  'row-sheet': r.ss_type === 'E',
                }]"
              >
                <td class="rt-pos">{{ r.position }}</td>
                <td>
                  <span :class="['aa-badge', `aa-${r.amino_acid}`]">{{ r.amino_acid }}</span>
                </td>
                <td>
                  <span :class="['ss-badge', ssColorClass(r.ss_type)]">
                    {{ ssTypeLabel(r.ss_type) }}
                  </span>
                </td>
                <td>
                  <div class="conf-bar-cell">
                    <div
                      :class="['conf-bar', r.ss_confidence >= 0.7 ? 'high' : r.ss_confidence >= 0.4 ? 'mid' : 'low']"
                      :style="{ width: (r.ss_confidence * 100) + '%' }"
                    ></div>
                    <span class="conf-text">{{ (r.ss_confidence * 100).toFixed(0) }}%</span>
                  </div>
                </td>
                <td>
                  <span v-if="r.ibs_candidate" class="ibs-indicator" title="Ice-binding surface candidate">❄</span>
                  <span v-else class="text-muted">—</span>
                </td>
                <td>
                  <div class="conf-bar-cell">
                    <div
                      :class="['conf-bar', 'ibs', r.ibs_confidence >= 0.7 ? 'high' : r.ibs_confidence >= 0.4 ? 'mid' : 'low']"
                      :style="{ width: (r.ibs_confidence * 100) + '%' }"
                    ></div>
                    <span class="conf-text">{{ (r.ibs_confidence * 100).toFixed(0) }}%</span>
                  </div>
                </td>
                <td>
                  <span :class="['access-badge', r.solvent_accessibility]">
                    {{ accessibilityLabel(r.solvent_accessibility) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Legend -->
        <div class="rt-legend">
          <span><span class="ss-swatch helix"></span> α-Helix</span>
          <span><span class="ss-swatch sheet"></span> β-Sheet</span>
          <span><span class="ss-swatch loop"></span> Turn</span>
          <span><span class="ss-swatch coil"></span> Coil</span>
          <span class="rt-legend-sep">|</span>
          <span><span class="ibs-indicator">❄</span> IBS candidate</span>
        </div>
      </div>

      <!-- ═══════════════ PROPERTIES PANEL ═══════════════ -->
      <div v-if="activePanel === 'properties'" class="pv-panel">
        <div class="props-grid">
          <!-- Physicochemical -->
          <div class="card props-card">
            <h4><SvgIcon name="chart" :size="16" /> Physicochemical Properties</h4>
            <div class="prop-list">
              <div class="prop-row">
                <span class="prop-label">Ala Content</span>
                <span class="prop-val">{{ (structureData.ala_content * 100).toFixed(1) }}%</span>
                <div class="prop-bar-track"><div class="prop-bar ala" :style="{ width: Math.min(structureData.ala_content * 100, 100) + '%' }"></div></div>
              </div>
              <div class="prop-row">
                <span class="prop-label">Thr Content</span>
                <span class="prop-val">{{ (structureData.thr_content * 100).toFixed(1) }}%</span>
                <div class="prop-bar-track"><div class="prop-bar thr" :style="{ width: Math.min(structureData.thr_content * 100, 100) + '%' }"></div></div>
              </div>
              <div class="prop-row">
                <span class="prop-label">Cys Content</span>
                <span class="prop-val">{{ (structureData.cys_content * 100).toFixed(1) }}%</span>
                <div class="prop-bar-track"><div class="prop-bar cys" :style="{ width: Math.min(structureData.cys_content * 100, 100) + '%' }"></div></div>
              </div>
              <div class="prop-row">
                <span class="prop-label">Net Charge</span>
                <span class="prop-val" :class="structureData.net_charge > 0 ? 'text-blue' : structureData.net_charge < 0 ? 'text-red' : ''">
                  {{ structureData.net_charge > 0 ? '+' : '' }}{{ structureData.net_charge.toFixed(1) }}
                </span>
              </div>
              <div class="prop-row">
                <span class="prop-label">Hydrophobicity (GRAVY)</span>
                <span class="prop-val" :class="structureData.hydrophobicity > 0 ? 'text-blue' : 'text-red'">
                  {{ structureData.hydrophobicity.toFixed(3) }}
                </span>
              </div>
            </div>
          </div>

          <!-- Ice-Binding Surface -->
          <div class="card props-card">
            <h4><SvgIcon name="ice" :size="16" /> Ice-Binding Surface</h4>
            <div class="prop-list">
              <div class="prop-row">
                <span class="prop-label">IBS Candidates</span>
                <span class="prop-val">{{ structureData.ibs_positions.length }} residues</span>
              </div>
              <div class="prop-row">
                <span class="prop-label">Flatness Score</span>
                <span class="prop-val" :class="structureData.ibs_flatness_score >= 0.7 ? 'text-success' : structureData.ibs_flatness_score >= 0.4 ? 'text-warning' : 'text-danger'">
                  {{ (structureData.ibs_flatness_score * 100).toFixed(0) }}%
                </span>
                <div class="prop-bar-track">
                  <div
                    :class="['prop-bar', structureData.ibs_flatness_score >= 0.7 ? 'good' : structureData.ibs_flatness_score >= 0.4 ? 'mid' : 'bad']"
                    :style="{ width: (structureData.ibs_flatness_score * 100) + '%' }"
                  ></div>
                </div>
              </div>
              <div class="prop-row" v-if="structureData.ibs_thr_spacing.length">
                <span class="prop-label">Thr Spacing</span>
                <span class="prop-val">
                  <span v-for="(d, i) in structureData.ibs_thr_spacing" :key="i" class="spacing-chip">{{ d.toFixed(1) }}Å</span>
                </span>
              </div>
              <div class="prop-row">
                <span class="prop-label">IBS Residues</span>
                <span class="prop-val ibs-chips">
                  <span v-for="pos in structureData.ibs_positions" :key="pos" class="ibs-pos-tag">
                    {{ structureData.sequence[pos - 1] }}{{ pos }}
                  </span>
                  <span v-if="!structureData.ibs_positions.length" class="text-muted">None identified</span>
                </span>
              </div>
            </div>
          </div>

          <!-- Fold Info -->
          <div class="card props-card">
            <h4><SvgIcon name="target" :size="16" /> Fold Information</h4>
            <div class="prop-list">
              <div class="prop-row">
                <span class="prop-label">Predicted Fold</span>
                <span class="prop-val">{{ structureData.predicted_fold }}</span>
              </div>
              <div class="prop-row">
                <span class="prop-label">Fold Confidence</span>
                <span class="prop-val">{{ (structureData.fold_confidence * 100).toFixed(0) }}%</span>
              </div>
              <div class="prop-row">
                <span class="prop-label">Matching AFP Type</span>
                <span class="prop-val match">{{ structureData.matching_afp_type || '—' }}</span>
              </div>
              <div class="prop-row">
                <span class="prop-label">SS Consensus</span>
                <span class="prop-val text-mono text-xs" style="word-break: break-all;">{{ ssConsensus }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Structural Highlights -->
        <div v-if="structureData.structural_highlights.length" class="card" style="margin-top: 1rem;">
          <h4><SvgIcon name="search" :size="16" /> Structural Highlights</h4>
          <ul class="highlights-list">
            <li v-for="(h, i) in structureData.structural_highlights" :key="i" class="highlight-item">
              <SvgIcon name="check" :size="12" class="highlight-icon" />
              {{ h }}
            </li>
          </ul>
        </div>

        <!-- Design Notes -->
        <div v-if="structureData.design_notes.length" class="design-notes-card">
          <div class="notes-title">
            <SvgIcon name="shield" :size="14" /> Design Notes
          </div>
          <div v-for="(note, i) in structureData.design_notes" :key="i" class="note-item">
            <span class="note-bullet">⚡</span>
            {{ note }}
          </div>
        </div>

        <!-- PDB Source Info -->
        <div class="card" style="margin-top: 1rem;">
          <h4><SvgIcon name="ice" :size="16" /> 3D Structure Source</h4>
          <div class="prop-row">
            <span class="prop-label">Source</span>
            <span class="prop-val">{{ structureData.pdb_source || 'Unknown' }}</span>
          </div>
          <div class="prop-row" v-if="structureData.pdb_data">
            <span class="prop-label">PDB Size</span>
            <span class="prop-val text-mono">{{ (structureData.pdb_data.length / 1024).toFixed(1) }} KB</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.protein-viewer {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* ── States ── */
.pv-loading,
.pv-error,
.pv-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1.5rem;
  text-align: center;
  gap: 0.5rem;
}

.pv-error-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1.5rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: var(--radius);
  max-width: 400px;
}

.pv-error-icon {
  opacity: 0.3;
  color: var(--danger);
}

.pv-empty-icon {
  opacity: 0.15;
  color: var(--text-secondary);
}

/* ── Tabs ── */
.pv-tabs {
  display: flex;
  gap: 0.25rem;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  padding: 0.3rem;
  width: fit-content;
}

.pv-tab {
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

.pv-tab:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.pv-tab.active {
  background: var(--accent);
  color: #fff;
}

/* ── Panel ── */
.pv-panel {
  animation: fadeIn 0.2s ease-out;
}

/* ── NGL Viewport ── */
.ngl-viewport {
  position: relative;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: #f0f5fb;
  border: 1px solid var(--border-light);
  min-height: 380px;
  margin-bottom: 0.75rem;
}

.ngl-stage {
  width: 100%;
  height: 400px;
  min-height: 380px;
}

.ngl-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  background: rgba(240, 245, 251, 0.92);
  z-index: 10;
  font-size: 0.82rem;
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
}

.ngl-badge {
  position: absolute;
  top: 8px;
  right: 10px;
  font-size: 0.6rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  background: rgba(255, 255, 255, 0.9);
  color: var(--accent-cyan);
  padding: 0.15rem 0.5rem;
  border-radius: 3px;
  border: 1px solid var(--border-light);
  z-index: 5;
  pointer-events: none;
}

/* ── Secondary Structure Track ── */
.ss-section {
  margin-bottom: 0.75rem;
}

.ss-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 0.4rem;
}

.ss-title {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-primary);
}

.ss-track {
  display: flex;
  gap: 1px;
  flex-wrap: wrap;
  margin-bottom: 0.4rem;
}

.ss-block {
  width: 10px;
  height: 24px;
  border-radius: 2px;
  transition: transform 0.15s ease;
  cursor: default;
}

.ss-block:hover {
  transform: scaleY(1.5);
  z-index: 1;
  box-shadow: var(--shadow-sm);
}

.ss-block.helix { background: #ef4444; }
.ss-block.sheet { background: #3b82f6; }
.ss-block.coil  { background: #d1d5db; }
.ss-block.loop  { background: #f59e0b; }

.ss-legend {
  display: flex;
  gap: 0.9rem;
  font-size: 0.65rem;
  color: var(--text-secondary);
  align-items: center;
  flex-wrap: wrap;
}

.ss-legend-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.ss-swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.ss-swatch.helix { background: #ef4444; }
.ss-swatch.sheet { background: #3b82f6; }
.ss-swatch.coil  { background: #d1d5db; }
.ss-swatch.loop  { background: #f59e0b; }

/* ── Quick Insights Row ── */
.pv-insights-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.6rem;
}

.pv-insight {
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  padding: 0.6rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.pv-insight-label {
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
}

.pv-insight-val {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 3px;
}

.pv-insight-val.match {
  color: var(--accent-cyan);
}

.confidence-chip {
  font-size: 0.65rem;
  font-weight: 600;
  background: var(--accent-light);
  color: var(--accent);
  padding: 0.05rem 0.35rem;
  border-radius: 3px;
}

.ibs-pos-tag {
  display: inline-flex;
  align-items: center;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 700;
  background: #cffafe;
  color: #0891b2;
  padding: 0.08rem 0.35rem;
  border-radius: 3px;
  border: 1px solid rgba(6, 182, 212, 0.25);
}

.text-success { color: var(--success); }
.text-warning { color: var(--warning); }
.text-danger { color: var(--danger); }
.text-blue { color: var(--accent); }
.text-red { color: var(--danger); }

/* ── Residue Table ── */
.residue-table-wrapper {
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.rt-toggles {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 0.75rem;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-light);
  flex-wrap: wrap;
}

.rt-toggle {
  display: flex;
  align-items: center;
  gap: 0.2rem;
  font-size: 0.65rem;
  color: var(--text-secondary);
  cursor: default;
}

.rt-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
}

.rt-table thead {
  position: sticky;
  top: 0;
  z-index: 2;
}

.rt-table th {
  text-align: left;
  padding: 0.45rem 0.6rem;
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
  background: var(--bg-card);
  border-bottom: 2px solid var(--border);
  white-space: nowrap;
}

.rt-table td {
  padding: 0.35rem 0.6rem;
  border-bottom: 1px solid var(--border-light);
  vertical-align: middle;
}

.rt-row:hover {
  background: var(--bg-secondary);
}

.rt-row.ibs-row {
  background: #f0fdff;
}

.rt-row.row-helix {
  border-left: 3px solid #ef4444;
}

.rt-row.row-sheet {
  border-left: 3px solid #3b82f6;
}

.rt-pos {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-align: right;
  min-width: 2.5em;
}

/* AA Badge */
.aa-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  font-size: 0.7rem;
  font-weight: 700;
  border-radius: 4px;
  font-family: var(--font-mono);
}

/* SS Badge */
.ss-badge {
  display: inline-block;
  font-size: 0.68rem;
  font-weight: 600;
  padding: 0.1rem 0.45rem;
  border-radius: 3px;
  white-space: nowrap;
}

.ss-badge.helix { background: #fee2e2; color: #dc2626; }
.ss-badge.sheet { background: #dbeafe; color: #2563eb; }
.ss-badge.loop  { background: #fef3c7; color: #d97706; }
.ss-badge.coil  { background: #f3f4f6; color: #6b7280; }

/* Confidence bar cell */
.conf-bar-cell {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  min-width: 80px;
}

.conf-bar {
  height: 6px;
  border-radius: 3px;
  min-width: 4px;
  transition: width 0.3s ease;
}

.conf-bar.high { background: var(--success); }
.conf-bar.mid  { background: var(--warning); }
.conf-bar.low  { background: #d1d5db; }
.conf-bar.ibs.high { background: var(--accent-cyan); }
.conf-bar.ibs.mid  { background: #67e8f9; }
.conf-bar.ibs.low  { background: #d1d5db; }

.conf-text {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

/* IBS Indicator */
.ibs-indicator {
  font-size: 0.85rem;
  color: var(--accent-cyan);
}

/* Accessibility badge */
.access-badge {
  font-size: 0.65rem;
  font-weight: 600;
  padding: 0.08rem 0.4rem;
  border-radius: 3px;
  white-space: nowrap;
}

.access-badge.buried  { background: #f3f4f6; color: #6b7280; }
.access-badge.exposed { background: #dbeafe; color: #2563eb; }
.access-badge.surface { background: #fef3c7; color: #d97706; }

/* Rt legend */
.rt-legend {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.65rem;
  color: var(--text-secondary);
  flex-wrap: wrap;
}

.rt-legend-sep {
  color: var(--border);
}

/* ── Properties ── */
.props-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}

.props-card h4 {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.88rem;
  margin-bottom: 0.75rem;
}

.prop-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.prop-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.prop-label {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text-secondary);
  min-width: 110px;
}

.prop-val {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-mono);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 3px;
}

.prop-val.match {
  color: var(--accent-cyan);
  font-family: inherit;
}

/* Property bars */
.prop-bar-track {
  width: 100%;
  height: 5px;
  background: var(--bg-secondary);
  border-radius: 3px;
  overflow: hidden;
  margin-top: 0.15rem;
}

.prop-bar {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}

.prop-bar.ala { background: var(--accent); }
.prop-bar.thr { background: var(--accent-cyan); }
.prop-bar.cys { background: var(--warning); }
.prop-bar.good { background: var(--success); }
.prop-bar.mid  { background: var(--warning); }
.prop-bar.bad  { background: var(--danger); }

.spacing-chip {
  display: inline-flex;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 600;
  background: #f0fdf4;
  color: #16a34a;
  padding: 0.05rem 0.35rem;
  border-radius: 3px;
}

.ibs-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}

/* Highlights */
.highlights-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-top: 0.5rem;
}

.highlight-item {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: var(--text-primary);
  line-height: 1.5;
}

.highlight-icon {
  color: var(--success);
  flex-shrink: 0;
  margin-top: 2px;
}

/* Design Notes */
.design-notes-card {
  background: #fef3c7;
  border: 1px solid #fcd34d;
  border-radius: var(--radius-sm);
  padding: 0.7rem 0.85rem;
  margin-top: 1rem;
}

.notes-title {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #92400e;
  margin-bottom: 0.4rem;
}

.note-item {
  display: flex;
  align-items: flex-start;
  gap: 0.35rem;
  font-size: 0.75rem;
  color: #78350f;
  line-height: 1.5;
}

.note-bullet {
  flex-shrink: 0;
  font-size: 0.7rem;
}

/* ── Shared ── */
.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
