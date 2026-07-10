<script setup lang="ts">
import { ref } from 'vue'
import { useAppStore } from '@/stores/appStore'
import SvgIcon from '@/components/common/SvgIcon.vue'

const store = useAppStore()

interface HistoryEntry {
  id: string
  sequence: string
  target: string
  scenario: string
  rounds: number
  mutations: number
  bestTH: number | null
  bestIRI: number | null
  status: string
  createdAt: string
}

const sortKey = ref<string>('createdAt')
const sortDir = ref<number>(-1)

// Demo history entries
const demoHistory: HistoryEntry[] = [
  {
    id: 'run-001',
    sequence: 'DTASDAAAAAALTAANAAAAAKLTADNAAAAAAATAR',
    target: 'improve TH activity',
    scenario: 'ice_cream',
    rounds: 3,
    mutations: 7,
    bestTH: 1.23,
    bestIRI: 0.56,
    status: 'completed',
    createdAt: '2026-06-10T14:30:00Z',
  },
  {
    id: 'run-002',
    sequence: 'MNAKAAKAAAKAAAKAAAKAAAKAAAKAA',
    target: 'enhance ice plane matching',
    scenario: 'general',
    rounds: 2,
    mutations: 4,
    bestTH: 0.78,
    bestIRI: 0.35,
    status: 'completed',
    createdAt: '2026-06-09T10:15:00Z',
  },
  {
    id: 'run-003',
    sequence: 'AAAAAKAAAAAKAAAAAKAAAAAKAAAAAK',
    target: 'maximize IRI activity',
    scenario: 'cell_cryopreservation',
    rounds: 1,
    mutations: 2,
    bestTH: null,
    bestIRI: null,
    status: 'failed',
    createdAt: '2026-06-08T08:00:00Z',
  },
]

const history = ref<HistoryEntry[]>([...demoHistory])

function sortedHistory() {
  return [...history.value].sort((a: any, b: any) => {
    const aVal = a[sortKey.value] ?? ''
    const bVal = b[sortKey.value] ?? ''
    if (aVal < bVal) return -1 * sortDir.value
    if (aVal > bVal) return 1 * sortDir.value
    return 0
  })
}

function toggleSort(key: string) {
  if (sortKey.value === key) {
    sortDir.value *= -1
  } else {
    sortKey.value = key
    sortDir.value = -1
  }
}

function getSortArrow(key: string): string {
  if (sortKey.value !== key) return '↕'
  return sortDir.value === 1 ? '↑' : '↓'
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function scenarioLabel(s: string): string {
  const map: Record<string, string> = {
    general: 'General Purpose',
    ice_cream: 'Ice Cream',
    cell_cryopreservation: 'Cell Cryopreservation',
    organ_preservation: 'Organ Preservation',
    anti_ice_coating: 'Anti-Ice Coating',
  }
  return map[s] || s
}
</script>

<template>
  <div class="design-history">
    <!-- Header -->
    <div class="dh-header">
      <div>
        <h2>
          <SvgIcon name="history" :size="20" />
          Design History
        </h2>
        <p class="text-muted text-sm">
          Past design runs and their outcomes
        </p>
      </div>
      <div class="dh-header-stats">
        <span class="badge badge-blue">{{ history.length }} runs</span>
        <span class="badge badge-green">
          {{ history.filter(h => h.status === 'completed').length }} completed
        </span>
      </div>
    </div>

    <!-- If no history from store, use demo data -->
    <div v-if="store.designRounds.length > 0" class="dh-notice card">
      <SvgIcon name="ice" :size="16" />
      <span>Active design session has {{ store.designRounds.length }} round(s) in progress. View in <strong>Design Lab</strong> tab.</span>
    </div>

    <!-- Table -->
    <div class="dh-table-wrap card" v-if="sortedHistory().length">
      <table class="dh-table">
        <thead>
          <tr>
            <th @click="toggleSort('createdAt')" class="sortable">
              Date {{ getSortArrow('createdAt') }}
            </th>
            <th>Sequence</th>
            <th>Scenario</th>
            <th @click="toggleSort('rounds')" class="sortable">
              Rounds {{ getSortArrow('rounds') }}
            </th>
            <th @click="toggleSort('mutations')" class="sortable">
              Mutations {{ getSortArrow('mutations') }}
            </th>
            <th @click="toggleSort('bestTH')" class="sortable">
              Best TH {{ getSortArrow('bestTH') }}
            </th>
            <th @click="toggleSort('bestIRI')" class="sortable">
              Best IRI {{ getSortArrow('bestIRI') }}
            </th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="entry in sortedHistory()" :key="entry.id">
            <td class="text-sm">{{ formatDate(entry.createdAt) }}</td>
            <td class="text-mono text-sm">
              {{ entry.sequence.substring(0, 15) }}...
            </td>
            <td class="text-sm">{{ scenarioLabel(entry.scenario) }}</td>
            <td class="text-center">{{ entry.rounds }}</td>
            <td class="text-center">{{ entry.mutations }}</td>
            <td class="text-mono text-center">
              {{ entry.bestTH ? entry.bestTH.toFixed(2) + '°C' : '—' }}
            </td>
            <td class="text-mono text-center">
              {{ entry.bestIRI ? entry.bestIRI.toFixed(2) + 'µM' : '—' }}
            </td>
            <td>
              <span :class="['status-badge', entry.status]">
                {{ entry.status }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty -->
    <div v-else class="card empty-state">
      <SvgIcon name="history" :size="48" class="empty-icon" />
      <h3>No Design History</h3>
      <p class="text-muted">Run your first AFP design to see results here.</p>
    </div>
  </div>
</template>

<style scoped>
.design-history {
  padding: 1.5rem;
  max-width: 1200px;
}

.dh-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.25rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.dh-header h2 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.25rem;
}

.dh-header-stats {
  display: flex;
  gap: 0.5rem;
}

.dh-notice {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  background: var(--accent-light);
  border-color: var(--accent);
  font-size: 0.8rem;
}

/* Table */
.dh-table-wrap {
  overflow-x: auto;
  padding: 0;
}

.dh-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}

.dh-table th {
  text-align: left;
  padding: 0.65rem 0.85rem;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
  border-bottom: 2px solid var(--border-light);
  white-space: nowrap;
  user-select: none;
}

.dh-table th.sortable {
  cursor: pointer;
}

.dh-table th.sortable:hover {
  color: var(--accent);
}

.dh-table td {
  padding: 0.6rem 0.85rem;
  border-bottom: 1px solid var(--border-light);
}

.dh-table tbody tr:hover {
  background: var(--bg-secondary);
}

.text-center {
  text-align: center;
}

/* Empty */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem;
  text-align: center;
  gap: 0.5rem;
}

.empty-icon {
  opacity: 0.2;
  color: var(--text-secondary);
}
</style>
