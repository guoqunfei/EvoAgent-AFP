<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useAppStore } from '@/stores/appStore'
import { useApi } from '@/composables/useApi'
import SvgIcon from '@/components/common/SvgIcon.vue'

const store = useAppStore()
const api = useApi()
const loading = ref(false)
const sessions = ref<Array<{ session_id: string; created_at: string; directory: string }>>([])
const expandedSession = ref<string | null>(null)
const sessionData = ref<Record<string, any>>({})

async function loadSessions() {
  loading.value = true
  try {
    const res = await api.listSessions()
    sessions.value = (res.sessions || []).reverse()
  } catch {
    sessions.value = []
  } finally {
    loading.value = false
  }
}

async function toggleSession(sid: string) {
  if (expandedSession.value === sid) {
    expandedSession.value = null
    return
  }
  expandedSession.value = sid
  if (!sessionData.value[sid]) {
    try {
      const data = await api.getSession(sid)
      sessionData.value[sid] = data
    } catch {
      sessionData.value[sid] = { error: true }
    }
  }
}

function jumpToDesignLab(sid: string) {
  store.setTab('design')
  // Use global event to pass session ID to DesignLab
  setTimeout(() => {
    window.dispatchEvent(new CustomEvent('load-session', { detail: sid }))
  }, 200)
}

function formatTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString()
}

const deleteTarget = ref<string | null>(null)
const deleting = ref(false)

function confirmDelete(sid: string) { deleteTarget.value = sid }
async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await api.deleteSession(deleteTarget.value)
    sessions.value = sessions.value.filter((s) => s.session_id !== deleteTarget.value)
    deleteTarget.value = null
  } catch { /* ignore */ }
  finally { deleting.value = false }
}

function shortId(sid: string): string {
  return sid.length > 20 ? sid.slice(0, 20) + '...' : sid
}

function verdictIcon(v: string): string {
  const m: Record<string, string> = { PASS: '✅', CAUTION: '🟡', WARNING: '⚠️', REJECTED: '❌' }
  return m[v] || '❓'
}

onMounted(() => { loadSessions() })
</script>

<template>
  <div class="results-view">
    <div class="rv-header">
      <div>
        <h2><SvgIcon name="chart" :size="20" /> Results</h2>
        <p class="text-muted text-sm">design_record 中所有历史设计会话</p>
      </div>
      <button class="btn-secondary" @click="loadSessions" :disabled="loading">
        <SvgIcon name="refresh" :size="14" /> {{ loading ? 'Loading...' : 'Refresh' }}
      </button>
    </div>

    <div v-if="loading" class="rv-loading">Loading sessions...</div>

    <div v-else-if="!sessions.length" class="empty-state">
      <SvgIcon name="chart" :size="48" class="empty-icon" />
      <h3>暂无设计记录</h3>
      <p class="text-muted">运行一次 AFP 设计后，结果将显示在这里</p>
    </div>

    <div v-else class="sessions-list">
      <div v-for="s in sessions" :key="s.session_id" :class="['session-card card', { expanded: expandedSession === s.session_id }]">
        <!-- Session header -->
        <div class="session-header" @click="toggleSession(s.session_id)">
          <div class="session-header-left">
            <span class="session-id-badge">📁 {{ shortId(s.session_id) }}</span>
            <span class="session-time text-xs text-muted">{{ formatTime(s.created_at) }}</span>
          </div>
          <div class="session-header-right">
            <button class="btn-primary btn-sm" @click.stop="jumpToDesignLab(s.session_id)" title="跳转到 Design Lab">
              <SvgIcon name="send" :size="12" /> 跳转
            </button>
            <button class="btn-del btn-sm" @click.stop="confirmDelete(s.session_id)" title="删除此会话">删除</button>
            <SvgIcon :name="expandedSession === s.session_id ? 'x' : 'search'" :size="14" />
          </div>
        </div>

        <!-- Session detail -->
        <div v-if="expandedSession === s.session_id && sessionData[s.session_id]" class="session-detail fade-in">
          <div v-if="sessionData[s.session_id].error" class="text-muted">无法加载会话数据</div>
          <template v-else>
            <div class="detail-grid">
              <!-- Sequence -->
              <div class="detail-card">
                <h4>输入序列</h4>
                <code class="seq-code">{{ (sessionData[s.session_id].rounds?.original_sequence || sessionData[s.session_id].analysis?.sequence || 'N/A') }}</code>
              </div>
              <!-- Target -->
              <div class="detail-card">
                <h4>设计目标</h4>
                <p class="text-sm">{{ sessionData[s.session_id].rounds?.design_target || sessionData[s.session_id].summary?.design_target || 'N/A' }}</p>
              </div>
            </div>

            <!-- Performance summary -->
            <div class="detail-card" v-if="sessionData[s.session_id].summary">
              <h4>性能对比</h4>
              <div class="perf-row">
                <div class="perf-item">
                  <span class="perf-label">基线 TH</span>
                  <span class="perf-val">{{ sessionData[s.session_id].summary?.baseline?.th?.toFixed(2) || '?' }}°C</span>
                </div>
                <div class="perf-item">
                  <span class="perf-label">基线 IRI</span>
                  <span class="perf-val">{{ sessionData[s.session_id].summary?.baseline?.iri?.toFixed(2) || '?' }}µM</span>
                </div>
                <div class="perf-item">
                  <span class="perf-label">总轮次</span>
                  <span class="perf-val">{{ sessionData[s.session_id].summary?.total_rounds || sessionData[s.session_id].rounds?.total_rounds || 0 }}</span>
                </div>
                <div class="perf-item" v-if="sessionData[s.session_id].summary?.final_sequence">
                  <span class="perf-label">最终序列</span>
                  <code class="final-seq">{{ sessionData[s.session_id].summary.final_sequence }}</code>
                </div>
              </div>
            </div>

            <!-- Rounds table -->
            <div class="detail-card" v-if="(sessionData[s.session_id].rounds?.rounds || []).length">
              <h4>设计轮次</h4>
              <table class="rv-table">
                <thead><tr><th>轮次</th><th>突变</th><th>判定</th><th>TH 变化</th><th>IRI 变化</th><th>表达</th><th>稳定性</th></tr></thead>
                <tbody>
                  <tr v-for="r in sessionData[s.session_id].rounds.rounds" :key="r.round">
                    <td><span class="badge badge-navy">R{{ r.round }}</span></td>
                    <td><span v-for="m in (r.mutations || [])" :key="m" class="mutation-tag">{{ m }}</span></td>
                    <td><span class="eval-tag">{{ verdictIcon(r.verdict) }} {{ r.verdict }}</span></td>
                    <td :class="r.th_change_pct > 0 ? 'improved' : ''">{{ (r.th_change_pct || 0).toFixed(1) }}%</td>
                    <td :class="r.iri_change_pct > 0 ? 'improved' : ''">{{ (r.iri_change_pct || 0).toFixed(1) }}%</td>
                    <td>{{ (r.expression_score || 0).toFixed(3) }}</td>
                    <td>{{ (r.stability_score || 0).toFixed(3) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Performance trend -->
            <div class="detail-card" v-if="(sessionData[s.session_id].summary?.performance_trend || []).length >= 2">
              <h4>性能趋势</h4>
              <div class="trend-mini">
                <div v-for="t in sessionData[s.session_id].summary.performance_trend" :key="t.round" class="trend-dot-row">
                  <span class="badge badge-navy">R{{ t.round }}</span>
                  <span :class="t.mutations?.join(', ') ? 'mutation-tag' : ''">{{ (t.mutations || []).join(', ') }}</span>
                  <span class="text-xs text-muted">TH: {{ (t.th || 0).toFixed(3) }} | IRI: {{ (t.iri || 0).toFixed(2) }} | AFP: {{ (t.afp_probability || 0).toFixed(3) }}</span>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- Loading detail -->
        <div v-else-if="expandedSession === s.session_id" class="session-detail">
          <p class="text-muted text-sm">Loading...</p>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
      <div class="modal-card">
        <h3>确认删除</h3>
        <p>确定要删除会话 <strong>{{ deleteTarget }}</strong> 吗？此操作不可恢复。</p>
        <div class="modal-actions">
          <button class="btn-danger" @click="doDelete" :disabled="deleting">{{ deleting ? '删除中...' : '确认删除' }}</button>
          <button class="btn-secondary btn-sm" @click="deleteTarget = null">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.results-view { padding: 1.5rem 2rem; max-width: 1100px; }
.rv-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem; }
.rv-header h2 { display: flex; align-items: center; gap: 0.5rem; font-size: 1.25rem; }

.sessions-list { display: flex; flex-direction: column; gap: 0.6rem; }

.session-card { cursor: pointer; transition: border-color 0.15s; }
.session-card.expanded { border-color: var(--accent); }

.session-header { display: flex; justify-content: space-between; align-items: center; }
.session-header-left { display: flex; align-items: center; gap: 0.75rem; }
.session-header-right { display: flex; align-items: center; gap: 0.5rem; color: var(--text-secondary); }

.session-id-badge { font-family: var(--font-mono); font-size: 0.78rem; font-weight: 600; color: var(--accent-cyan); }

.session-detail { margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid var(--border-light); }

.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 0.75rem; }
.detail-card { margin-bottom: 0.75rem; }
.detail-card h4 { font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-secondary); margin-bottom: 0.35rem; }

.seq-code { font-size: 0.72rem; font-family: var(--font-mono); word-break: break-all; background: #f8f9fa; padding: 0.3rem 0.5rem; border-radius: 4px; display: block; }
.final-seq { font-size: 0.68rem; font-family: var(--font-mono); word-break: break-all; }

.perf-row { display: flex; gap: 1.5rem; flex-wrap: wrap; }
.perf-item { display: flex; flex-direction: column; gap: 0.15rem; }
.perf-label { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-secondary); }
.perf-val { font-size: 1rem; font-weight: 700; font-family: var(--font-mono); color: var(--accent-cyan); }

.trend-mini { display: flex; flex-direction: column; gap: 0.35rem; }
.trend-dot-row { display: flex; align-items: center; gap: 0.5rem; }

.eval-tag { font-size: 0.72rem; }
.improved { color: var(--success); font-weight: 700; }

.rv-table { width: 100%; border-collapse: collapse; font-size: 0.72rem; margin-top: 0.3rem; }
.rv-table th { text-align: left; padding: 0.4rem 0.5rem; font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-secondary); border-bottom: 2px solid var(--border-light); }
.rv-table td { padding: 0.35rem 0.5rem; border-bottom: 1px solid var(--border-light); }

.empty-state { display: flex; flex-direction: column; align-items: center; padding: 4rem; text-align: center; gap: 0.5rem; }
.empty-icon { opacity: 0.15; color: var(--text-secondary); }

.rv-loading { text-align: center; padding: 3rem; color: var(--text-secondary); }

.btn-primary { background: var(--accent); color: #fff; border: none; padding: 0.4rem 1rem; border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 0.3rem; }
.btn-secondary { background: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border); padding: 0.4rem 1rem; border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 0.3rem; }
.btn-sm { font-size: 0.7rem; padding: 0.25rem 0.6rem; }

.btn-del { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; border-radius: 6px; font-weight: 600; cursor: pointer; }
.btn-del:hover { background: #fee2e2; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-card { background: #fff; border-radius: 12px; padding: 1.5rem 2rem; max-width: 420px; width: 90%; box-shadow: 0 8px 30px rgba(0,0,0,0.15); }
.modal-card h3 { font-size: 1.1rem; margin: 0 0 0.5rem; }
.modal-card p { font-size: 0.85rem; color: #4a5568; margin: 0 0 1.25rem; }
.modal-actions { display: flex; gap: 0.6rem; justify-content: flex-end; }
.btn-danger { background: #dc2626; color: #fff; border: none; padding: 0.4rem 1rem; border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer; }
.btn-danger:hover { background: #b91c1c; }
.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
