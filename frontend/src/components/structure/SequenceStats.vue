<script setup lang="ts">
import { computed } from 'vue'
import SvgIcon from '@/components/common/SvgIcon.vue'

const props = defineProps<{
  sequence: string
}>()

// ── AA frequency ──
const AA_LIST = 'ACDEFGHIKLMNPQRSTVWY'.split('')

interface AAFreq {
  aa: string
  count: number
  pct: number
}

const aaFreq = computed<AAFreq[]>(() => {
  const seq = props.sequence.toUpperCase()
  const total = seq.length || 1
  return AA_LIST
    .map((aa) => ({ aa, count: seq.split(aa).length - 1, pct: 0 }))
    .map((f) => ({ ...f, pct: (f.count / total) * 100 }))
    .filter((f) => f.count > 0)
    .sort((a, b) => b.count - a.count)
})

const maxCount = computed(() => Math.max(...aaFreq.value.map((f) => f.count), 1))

// ── Sequence properties ──
const seqProps = computed(() => {
  const seq = props.sequence.toUpperCase()
  const n = seq.length || 1

  const alaCount = (seq.match(/A/g) || []).length
  const thrCount = (seq.match(/T/g) || []).length
  const cysCount = (seq.match(/C/g) || []).length
  const positiveCount = (seq.match(/[KRH]/g) || []).length
  const negativeCount = (seq.match(/[DE]/g) || []).length
  const hydrophobicCount = (seq.match(/[AILMFWYV]/g) || []).length
  const polarCount = (seq.match(/[NQST]/g) || []).length
  const chargedCount = positiveCount + negativeCount

  // Approximate MW (average ~110 Da per residue)
  const mwEstimate = n * 110

  // Hydropathy (Kyte-Doolittle scale)
  const hydropathy: Record<string, number> = {
    A: 1.8, C: 2.5, D: -3.5, E: -3.5, F: 2.8,
    G: -0.4, H: -3.2, I: 4.5, K: -3.9, L: 3.8,
    M: 1.9, N: -3.5, P: -1.6, Q: -3.5, R: -4.5,
    S: -0.8, T: -0.7, V: 4.2, W: -0.9, Y: -1.3,
  }
  const gravy = seq.split('').reduce((s, aa) => s + (hydropathy[aa] || 0), 0) / n

  // IBS-related residue counts
  const ibsStrong = (seq.match(/[TN]/g) || []).length
  const ibsIndicator = (seq.match(/[TNQSA]/g) || []).length
  const ibsForbidden = (seq.match(/[DEKRFWY]/g) || []).length

  return {
    length: n,
    mwEstimate,
    alaPct: (alaCount / n * 100),
    thrPct: (thrCount / n * 100),
    cysPct: (cysCount / n * 100),
    netCharge: positiveCount - negativeCount,
    gravy: gravy.toFixed(3),
    hydrophobicPct: (hydrophobicCount / n * 100),
    polarPct: (polarCount / n * 100),
    chargedPct: (chargedCount / n * 100),
    ibsStrong,
    ibsIndicator,
    ibsForbidden,
  }
})

// ── Per-position properties for track display ──
interface PosInfo {
  pos: number
  aa: string
  hydropathy: number
  charge: number
  isIbs: boolean
}

const posInfo = computed<PosInfo[]>(() => {
  const hydropathy: Record<string, number> = {
    A: 1.8, C: 2.5, D: -3.5, E: -3.5, F: 2.8,
    G: -0.4, H: -3.2, I: 4.5, K: -3.9, L: 3.8,
    M: 1.9, N: -3.5, P: -1.6, Q: -3.5, R: -4.5,
    S: -0.8, T: -0.7, V: 4.2, W: -0.9, Y: -1.3,
  }
  const charge: Record<string, number> = {
    K: 1, R: 1, H: 0.5, D: -1, E: -1,
  }
  const ibsSet = new Set(['T', 'N', 'Q', 'S', 'A'])

  return props.sequence.toUpperCase().split('').map((aa, i) => ({
    pos: i + 1,
    aa,
    hydropathy: hydropathy[aa] || 0,
    charge: charge[aa] || 0,
    isIbs: ibsSet.has(aa),
  }))
})

const hydroMax = computed(() => Math.max(...posInfo.value.map(p => Math.abs(p.hydropathy)), 1))

// ── AA class ──
function aaGroup(aa: string): string {
  const map: Record<string, string> = {
    A: 'hydrophobic', V: 'hydrophobic', I: 'hydrophobic', L: 'hydrophobic',
    M: 'hydrophobic', F: 'hydrophobic', W: 'hydrophobic', Y: 'hydrophobic',
    R: 'positive', K: 'positive', H: 'positive',
    D: 'negative', E: 'negative',
    N: 'polar', Q: 'polar', S: 'polar', T: 'polar',
    C: 'special', G: 'special', P: 'special',
  }
  return map[aa] || 'other'
}
</script>

<template>
  <div class="seq-stats" v-if="sequence">
    <!-- ═══ AA Composition Chart ═══ -->
    <div class="stats-section">
      <h4 class="stats-title">
        <SvgIcon name="chart" :size="14" /> Amino Acid Composition
      </h4>
      <div class="aa-chart">
        <div
          v-for="f in aaFreq"
          :key="f.aa"
          class="aa-chart-row"
        >
          <span :class="['aa-label', `aa-${f.aa}`]">{{ f.aa }}</span>
          <div class="aa-bar-track">
            <div
              :class="['aa-bar', aaGroup(f.aa)]"
              :style="{ width: (f.count / maxCount * 100) + '%' }"
            ></div>
          </div>
          <span class="aa-count">{{ f.count }}</span>
          <span class="aa-pct">{{ f.pct.toFixed(1) }}%</span>
        </div>
      </div>
      <div class="chart-legend">
        <span><span class="legend-swatch hydrophobic"></span> Hydrophobic</span>
        <span><span class="legend-swatch positive"></span> Positive</span>
        <span><span class="legend-swatch negative"></span> Negative</span>
        <span><span class="legend-swatch polar"></span> Polar</span>
        <span><span class="legend-swatch special"></span> Special</span>
      </div>
    </div>

    <!-- ═══ Properties Summary Table ═══ -->
    <div class="stats-section">
      <h4 class="stats-title">
        <SvgIcon name="target" :size="14" /> Sequence Properties
      </h4>
      <table class="props-table">
        <tbody>
          <tr>
            <td class="prop-name">Length</td>
            <td class="prop-val">{{ seqProps.length }} aa</td>
            <td class="prop-name">MW (est.)</td>
            <td class="prop-val">{{ (seqProps.mwEstimate / 1000).toFixed(1) }} kDa</td>
          </tr>
          <tr>
            <td class="prop-name">Ala</td>
            <td class="prop-val">{{ seqProps.alaPct.toFixed(1) }}%</td>
            <td class="prop-name">Thr</td>
            <td class="prop-val" :class="seqProps.thrPct >= 5 ? 'highlight' : ''">{{ seqProps.thrPct.toFixed(1) }}%</td>
          </tr>
          <tr>
            <td class="prop-name">Cys</td>
            <td class="prop-val" :class="seqProps.cysPct >= 2 ? 'highlight' : ''">{{ seqProps.cysPct.toFixed(1) }}%</td>
            <td class="prop-name">Net Charge</td>
            <td class="prop-val" :class="seqProps.netCharge > 0 ? 'positive' : seqProps.netCharge < 0 ? 'negative' : ''">{{ seqProps.netCharge > 0 ? '+' : '' }}{{ seqProps.netCharge }}</td>
          </tr>
          <tr>
            <td class="prop-name">Hydrophobic</td>
            <td class="prop-val">{{ seqProps.hydrophobicPct.toFixed(0) }}%</td>
            <td class="prop-name">Polar</td>
            <td class="prop-val">{{ seqProps.polarPct.toFixed(0) }}%</td>
          </tr>
          <tr>
            <td class="prop-name">Charged</td>
            <td class="prop-val">{{ seqProps.chargedPct.toFixed(0) }}%</td>
            <td class="prop-name">GRAVY</td>
            <td class="prop-val" :class="Number(seqProps.gravy) > 0 ? 'hydrophobic' : 'hydrophilic'">{{ seqProps.gravy }}</td>
          </tr>
          <tr>
            <td class="prop-name">IBS Strong (T/N)</td>
            <td class="prop-val highlight">{{ seqProps.ibsStrong }}</td>
            <td class="prop-name">IBS Forbidden</td>
            <td class="prop-val warn">{{ seqProps.ibsForbidden }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ═══ Position Track: Hydropathy ═══ -->
    <div class="stats-section">
      <h4 class="stats-title">
        <SvgIcon name="ice" :size="14" /> Per-Residue Hydropathy
      </h4>
      <div class="hydro-track">
        <div
          v-for="p in posInfo"
          :key="p.pos"
          class="hydro-bar-wrapper"
          :title="`${p.aa}${p.pos}: hydropathy=${p.hydropathy > 0 ? '+' : ''}${p.hydropathy.toFixed(1)}`"
        >
          <div
            :class="['hydro-bar', p.hydropathy > 0 ? 'phobic' : 'philic']"
            :style="{
              height: (Math.abs(p.hydropathy) / hydroMax * 100) + '%',
              marginTop: p.hydropathy > 0 ? (100 - Math.abs(p.hydropathy) / hydroMax * 100) + '%' : '0',
            }"
          ></div>
        </div>
      </div>
      <div class="track-legend">
        <span class="track-legend-left">Hydrophilic ▼</span>
        <span class="track-legend-center">← Position →</span>
        <span class="track-legend-right">Hydrophobic ▲</span>
      </div>
    </div>

    <!-- ═══ Position Track: Charge ═══ -->
    <div class="stats-section">
      <h4 class="stats-title">
        <SvgIcon name="shield" :size="14" /> Per-Residue Charge
      </h4>
      <div class="charge-track">
        <div
          v-for="p in posInfo"
          :key="p.pos"
          class="charge-bar-wrapper"
          :title="`${p.aa}${p.pos}: charge=${p.charge > 0 ? '+' : ''}${p.charge}`"
        >
          <div
            v-if="p.charge !== 0"
            :class="['charge-bar', p.charge > 0 ? 'pos' : 'neg']"
            :style="{
              height: (Math.abs(p.charge) / 1 * 40) + '%',
              marginTop: p.charge > 0 ? (60 - Math.abs(p.charge) / 1 * 40) + '%' : '60%',
            }"
          ></div>
        </div>
      </div>
      <div class="track-legend">
        <span class="track-legend-left positive">+</span>
        <span class="track-legend-center">← Position →</span>
        <span class="track-legend-right negative">−</span>
      </div>
    </div>

    <!-- ═══ Position Track: IBS ═══ -->
    <div class="stats-section">
      <h4 class="stats-title">
        <SvgIcon name="ice" :size="14" /> Ice-Binding Surface Residues
      </h4>
      <div class="ibs-track">
        <div
          v-for="p in posInfo"
          :key="p.pos"
          class="ibs-dot-wrapper"
          :title="`${p.aa}${p.pos}${p.isIbs ? ' — IBS candidate' : ''}`"
        >
          <span :class="['ibs-dot', { active: p.isIbs }]">{{ p.isIbs ? '❄' : '·' }}</span>
        </div>
      </div>
      <div class="track-legend">
        <span>❄ = IBS candidate (T/N/Q/S/A)</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.seq-stats {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding-top: 0.5rem;
}

.stats-section {
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  padding: 0.85rem 1rem;
}

.stats-title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
  margin-bottom: 0.6rem;
  margin-top: 0;
}

/* ── AA Bar Chart ── */
.aa-chart {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.aa-chart-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.aa-label {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.68rem;
  font-weight: 700;
  font-family: var(--font-mono);
  border-radius: 3px;
  flex-shrink: 0;
}

.aa-bar-track {
  flex: 1;
  height: 14px;
  background: rgba(0,0,0,0.04);
  border-radius: 3px;
  overflow: hidden;
}

.aa-bar {
  height: 100%;
  border-radius: 3px;
  min-width: 2px;
  transition: width 0.4s ease;
}

.aa-bar.hydrophobic { background: #94a3b8; }
.aa-bar.positive    { background: #3b82f6; }
.aa-bar.negative    { background: #ef4444; }
.aa-bar.polar       { background: #06b6d4; }
.aa-bar.special     { background: #f59e0b; }
.aa-bar.other       { background: #d1d5db; }

.aa-count {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-primary);
  width: 2em;
  text-align: right;
}

.aa-pct {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: var(--text-secondary);
  width: 3.5em;
  text-align: right;
}

.chart-legend {
  display: flex;
  gap: 0.8rem;
  margin-top: 0.5rem;
  flex-wrap: wrap;
  font-size: 0.62rem;
  color: var(--text-secondary);
  align-items: center;
}

.legend-swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
  margin-right: 3px;
  vertical-align: middle;
}

.legend-swatch.hydrophobic { background: #94a3b8; }
.legend-swatch.positive    { background: #3b82f6; }
.legend-swatch.negative    { background: #ef4444; }
.legend-swatch.polar       { background: #06b6d4; }
.legend-swatch.special     { background: #f59e0b; }

/* ── Properties Table ── */
.props-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
}

.props-table td {
  padding: 0.35rem 0.5rem;
  border-bottom: 1px solid rgba(0,0,0,0.04);
}

.prop-name {
  font-weight: 600;
  color: var(--text-secondary);
  font-size: 0.7rem;
  width: 28%;
}

.prop-val {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--text-primary);
  width: 22%;
}

.prop-val.highlight { color: var(--accent-cyan); }
.prop-val.warn { color: var(--warning); }
.prop-val.positive { color: var(--accent); }
.prop-val.negative { color: var(--danger); }
.prop-val.hydrophobic { color: #64748b; }
.prop-val.hydrophilic { color: var(--accent-cyan); }

/* ── Hydropathy Track ── */
.hydro-track {
  display: flex;
  gap: 0;
  align-items: flex-end;
  height: 60px;
}

.hydro-bar-wrapper {
  flex: 1;
  height: 100%;
  min-width: 2px;
  position: relative;
}

.hydro-bar {
  width: 100%;
  border-radius: 1px;
  min-height: 2px;
  transition: opacity 0.15s ease;
}

.hydro-bar.phobic { background: #94a3b8; }
.hydro-bar.philic { background: var(--accent-cyan); }

.hydro-bar:hover {
  opacity: 0.6;
}

/* ── Charge Track ── */
.charge-track {
  display: flex;
  gap: 0;
  align-items: flex-end;
  height: 50px;
}

.charge-bar-wrapper {
  flex: 1;
  height: 100%;
  min-width: 2px;
  position: relative;
}

.charge-bar {
  width: 100%;
  border-radius: 1px;
}

.charge-bar.pos { background: var(--accent); }
.charge-bar.neg { background: var(--danger); }

/* ── IBS Track ── */
.ibs-track {
  display: flex;
  gap: 0;
  align-items: center;
}

.ibs-dot-wrapper {
  flex: 1;
  text-align: center;
  min-width: 2px;
}

.ibs-dot {
  font-size: 0.55rem;
  color: var(--border);
  transition: all 0.15s ease;
}

.ibs-dot.active {
  color: var(--accent-cyan);
  font-size: 0.65rem;
}

/* ── Track Legend ── */
.track-legend {
  display: flex;
  justify-content: space-between;
  font-size: 0.58rem;
  color: var(--text-secondary);
  margin-top: 0.3rem;
}

.track-legend-center {
  opacity: 0.5;
}

.track-legend-right.negative { color: var(--danger); }
.track-legend-left.positive { color: var(--accent); }
</style>
