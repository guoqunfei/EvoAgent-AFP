<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useAppStore } from '@/stores/appStore'
import { useApi } from '@/composables/useApi'
import SvgIcon from '@/components/common/SvgIcon.vue'
import { marked } from 'marked'
import type { KnowledgeMotif } from '@/types/api'

function renderMD(text: string): string {
  return marked.parse(text, { async: false }) as string
}

const store = useAppStore()
const api = useApi()
const loading = ref(false)
const searchQuery = ref('')
const expandedMotif = ref<string | null>(null)

function toggleMotif(id: string) {
  expandedMotif.value = expandedMotif.value === id ? null : id
}

const filteredMotifs = computed(() => {
  let list = store.motifs
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(
      (m) =>
        m.name.toLowerCase().includes(q) ||
        m.afp_type.toLowerCase().includes(q) ||
        m.source_organism.toLowerCase().includes(q) ||
        m.design_rules.some((r) => r.toLowerCase().includes(q))
    )
  }
  return list
})

const editingEntry = ref<KnowledgeMotif | null>(null)
const editForm = ref({ name: '', afp_type: '', source_organism: '', th_activity: 0, iri_activity: 0, target_ice_plane: '', design_rules: [] as string[], rulesText: '' })
const addingNew = ref(false)
const deleteTarget = ref<string | null>(null)

async function loadKnowledge() {
  loading.value = true
  try {
    const res = await api.listKnowledgeEntries()
    store.setMotifs(res.entries || [])
  } catch {
    store.setMotifs([])
  } finally {
    loading.value = false
  }
}

function startEdit(m: KnowledgeMotif) {
  editingEntry.value = m
  editForm.value = {
    name: m.name,
    afp_type: m.afp_type,
    source_organism: m.source_organism,
    th_activity: m.th_activity,
    iri_activity: m.iri_activity,
    target_ice_plane: m.target_ice_plane,
    design_rules: [...m.design_rules],
    rulesText: m.design_rules.join('\n'),
  }
}

function startAdd() {
  addingNew.value = true
  editForm.value = { name: '', afp_type: 'Type I (α-helical, fish)', source_organism: '', th_activity: 0.5, iri_activity: 4.0, target_ice_plane: '', design_rules: [], rulesText: '' }
}

function cancelEdit() {
  editingEntry.value = null
  addingNew.value = false
}

async function saveEdit() {
  const data = {
    name: editForm.value.name,
    afp_type: editForm.value.afp_type,
    source_organism: editForm.value.source_organism,
    th_activity: editForm.value.th_activity,
    iri_activity: editForm.value.iri_activity,
    target_ice_plane: editForm.value.target_ice_plane,
    design_rules: editForm.value.rulesText.split('\n').filter((l) => l.trim()),
  }
  if (addingNew.value) {
    await api.createKnowledgeEntry(data)
  } else if (editingEntry.value) {
    await api.updateKnowledgeEntry(editingEntry.value.motif_id, data)
  }
  cancelEdit()
  loadKnowledge()
}

function confirmDelete(id: string) { deleteTarget.value = id }
async function doDelete() {
  if (!deleteTarget.value) return
  await api.deleteKnowledgeEntry(deleteTarget.value)
  deleteTarget.value = null
  loadKnowledge()
}

function typeLabel(t: string): string {
  const map: Record<string, string> = {
    'Type I (α-helical, fish)': 'Type I',
    'Type II (C-type lectin, fish)': 'Type II',
    'Type III (β-sandwich, fish)': 'Type III',
    'Type IV (4-helix bundle, fish)': 'Type IV',
    'Insect hyperactive (β-helical)': 'Hyperactive',
    'AFGP': 'AFGP',
    'Plant AFP': 'Plant',
    'Bacterial IBP': 'Bacterial',
    'De novo designed': 'De novo',
  }
  return map[t] || t
}

const typeFilters = computed(() => {
  const types = new Set(store.motifs.map((m) => typeLabel(m.afp_type)))
  return ['all', ...Array.from(types)]
})

onMounted(() => {
  if (store.motifs.length === 0) loadKnowledge()
})
</script>

<template>
  <div class="knowledge-browser">
    <div class="kb-header">
      <div>
        <h2><SvgIcon name="book" :size="20" /> Knowledge Base</h2>
        <p class="text-muted text-sm">AFP 基序库 · 冰结合模式 · 设计原则 — 来自后端 AFP 知识库</p>
      </div>
      <div class="kb-header-actions">
        <div class="search-box">
          <SvgIcon name="search" :size="14" />
          <input v-model="searchQuery" placeholder="搜索基序..." class="search-input" />
        </div>
        <button class="btn-primary btn-sm" @click="startAdd">+ 新增</button>
        <button class="btn-secondary" @click="loadKnowledge" :disabled="loading">
          <SvgIcon name="refresh" :size="14" /> {{ loading ? 'Loading...' : 'Refresh' }}
        </button>
      </div>
    </div>

    <div class="kb-stats" v-if="store.knowledgeSummary">
      <div class="stat-card">
        <span class="stat-number">{{ (store.knowledgeSummary as any).total_motifs || store.motifs.length }}</span>
        <span class="stat-label-text">AFP Motifs</span>
      </div>
      <div class="stat-card">
        <span class="stat-number">{{ (store.knowledgeSummary as any).total_principles || 0 }}</span>
        <span class="stat-label-text">Design Principles</span>
      </div>
      <div class="stat-card">
        <span class="stat-number">{{ ((store.knowledgeSummary as any).supported_applications || []).length }}</span>
        <span class="stat-label-text">Application Scenarios</span>
      </div>
    </div>

    <div v-if="loading" class="kb-loading text-muted">Loading knowledge base...</div>

    <div v-else class="kb-cards">
      <div
        v-for="motif in filteredMotifs"
        :key="motif.motif_id"
        :class="['motif-card card', { expanded: expandedMotif === motif.motif_id }]"
      >
        <div class="motif-card-header" @click="toggleMotif(motif.motif_id)">
          <div class="motif-card-left">
            <span class="badge badge-cyan">{{ typeLabel(motif.afp_type) }}</span>
            <h4>{{ motif.name }}</h4>
          </div>
          <div class="motif-card-right">
            <span class="organism text-xs text-muted">{{ motif.source_organism }}</span>
            <button class="btn-mini" @click.stop="startEdit(motif)">编辑</button>
            <button class="btn-mini btn-mini-del" @click.stop="confirmDelete(motif.motif_id)">删除</button>
          </div>
        </div>

        <div class="motif-ice-plane text-sm">
          <SvgIcon name="ice" :size="13" /> {{ motif.target_ice_plane }}
        </div>

        <div class="motif-activity">
          <div class="activity-row">
            <span class="activity-label">TH</span>
            <div class="activity-bar-track">
              <div class="activity-bar th" :style="{ width: Math.min(motif.th_activity * 50, 100) + '%' }"></div>
            </div>
            <span class="activity-val">{{ motif.th_activity.toFixed(2) }}°C</span>
          </div>
          <div class="activity-row">
            <span class="activity-label">IRI</span>
            <div class="activity-bar-track">
              <div class="activity-bar iri" :style="{ width: Math.min((5 - motif.iri_activity) * 20, 100) + '%' }"></div>
            </div>
            <span class="activity-val">{{ motif.iri_activity.toFixed(2) }}µM</span>
          </div>
        </div>

        <div v-if="expandedMotif === motif.motif_id" class="motif-rules fade-in">
          <div class="rules-title">Design Rules</div>
          <ul>
            <li v-for="(rule, i) in motif.design_rules" :key="i" v-html="renderMD(rule)"></li>
          </ul>
        </div>
      </div>

      <div v-if="!loading && filteredMotifs.length === 0" class="empty-state">
        <SvgIcon name="search" :size="36" class="empty-icon" />
        <p class="text-muted">暂无数据，点击 + 新增 添加知识条目</p>
      </div>
    </div>

    <!-- Edit / Add Modal -->
    <div v-if="editingEntry || addingNew" class="modal-overlay" @click.self="cancelEdit">
      <div class="modal-card modal-wide">
        <h3>{{ addingNew ? '新增知识条目' : '编辑 ' + (editingEntry?.name || '') }}</h3>
        <div class="edit-form">
          <label>名称 <input v-model="editForm.name" /></label>
          <label>AFP 类型 <input v-model="editForm.afp_type" /></label>
          <label>来源物种 <input v-model="editForm.source_organism" /></label>
          <div class="form-row">
            <label>TH (°C) <input v-model.number="editForm.th_activity" type="number" step="0.01" /></label>
            <label>IRI (µM) <input v-model.number="editForm.iri_activity" type="number" step="0.01" /></label>
          </div>
          <label>靶向冰面 <input v-model="editForm.target_ice_plane" /></label>
          <label>设计规则 — 每行一条，支持 **加粗** / `代码` / 列表
            <textarea v-model="editForm.rulesText" rows="8" class="edit-textarea" placeholder="每行一条规则，支持 Markdown 格式"></textarea>
          </label>
        </div>
        <div class="modal-actions">
          <button class="btn-primary btn-sm" @click="saveEdit">保存</button>
          <button class="btn-secondary btn-sm" @click="cancelEdit">取消</button>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation -->
    <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
      <div class="modal-card">
        <h3>确认删除</h3>
        <p>确定要删除知识条目 <strong>{{ deleteTarget }}</strong> 吗？</p>
        <div class="modal-actions">
          <button class="btn-danger" @click="doDelete">确认删除</button>
          <button class="btn-secondary" @click="deleteTarget = null">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.knowledge-browser { padding: 1.5rem; max-width: 1100px; }
.kb-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem; gap: 1rem; flex-wrap: wrap; }
.kb-header h2 { display: flex; align-items: center; gap: 0.5rem; font-size: 1.25rem; }
.kb-header-actions { display: flex; gap: 0.5rem; align-items: center; }
.search-box { display: flex; align-items: center; gap: 0.4rem; padding: 0.4rem 0.65rem; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-card); color: var(--text-secondary); }
.search-input { border: none; outline: none; font-size: 0.8rem; background: transparent; width: 180px; }

.kb-stats { display: flex; gap: 1rem; margin-bottom: 1.25rem; }
.stat-card { flex: 1; background: var(--bg-card); border: 1px solid var(--border-light); border-radius: var(--radius); padding: 1rem; text-align: center; box-shadow: var(--shadow-sm); }
.stat-number { display: block; font-size: 1.5rem; font-weight: 700; color: var(--accent); }
.stat-label-text { font-size: 0.75rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600; }

.kb-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 1rem; }
.motif-card { cursor: pointer; transition: all 0.15s ease; }
.motif-card.expanded { border-color: var(--accent-cyan); }
.motif-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem; }
.motif-card-left { display: flex; align-items: center; gap: 0.5rem; }
.motif-card-left h4 { font-size: 0.95rem; }
.motif-card-right { display: flex; align-items: center; gap: 0.5rem; color: var(--text-secondary); }
.organism { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.motif-ice-plane { color: var(--accent-cyan); font-weight: 600; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.3rem; }

.motif-activity { display: flex; flex-direction: column; gap: 0.35rem; }
.activity-row { display: flex; align-items: center; gap: 0.5rem; }
.activity-label { font-size: 0.65rem; font-weight: 700; color: var(--text-secondary); width: 24px; text-transform: uppercase; }
.activity-bar-track { flex: 1; height: 6px; background: var(--bg-secondary); border-radius: 3px; overflow: hidden; }
.activity-bar { height: 100%; border-radius: 3px; transition: width 0.3s ease; }
.activity-bar.th { background: linear-gradient(90deg, var(--accent), var(--accent-cyan)); }
.activity-bar.iri { background: linear-gradient(90deg, #22d3ee, #06b6d4); }
.activity-val { font-size: 0.75rem; font-weight: 600; font-family: var(--font-mono); color: var(--text-primary); min-width: 60px; text-align: right; }

.motif-rules { margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid var(--border-light); }
.rules-title { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--accent-cyan); margin-bottom: 0.4rem; }
.motif-rules ul { list-style: none; padding: 0; }
.motif-rules li { font-size: 0.78rem; color: var(--text-secondary); padding: 0.25rem 0; padding-left: 1rem; position: relative; }
.motif-rules li::before { content: '◆'; position: absolute; left: 0; color: var(--accent-cyan); font-size: 0.5rem; top: 0.45rem; }

.empty-state { grid-column: 1 / -1; display: flex; flex-direction: column; align-items: center; padding: 3rem; gap: 0.5rem; }
.empty-icon { opacity: 0.2; color: var(--text-secondary); }
.kb-loading { text-align: center; padding: 3rem; }

.btn-mini { font-size: 0.65rem; font-weight: 600; padding: 0.15rem 0.5rem; border-radius: 4px; border: 1px solid var(--border); background: var(--bg-card); color: var(--accent); cursor: pointer; }
.btn-mini:hover { background: var(--accent-light); }
.btn-mini-del { color: #dc2626; border-color: #fecaca; background: #fef2f2; }
.btn-mini-del:hover { background: #fee2e2; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-card { background: #fff; border-radius: 12px; padding: 1.5rem 2rem; max-width: 420px; width: 90%; box-shadow: 0 8px 30px rgba(0,0,0,0.15); }
.modal-wide { max-width: 560px; }
.modal-card h3 { font-size: 1.1rem; margin: 0 0 0.75rem; color: #1a202c; }
.modal-card p { font-size: 0.85rem; color: #4a5568; margin: 0 0 1.25rem; }
.modal-actions { display: flex; gap: 0.6rem; justify-content: flex-end; margin-top: 1rem; }

.edit-form { display: flex; flex-direction: column; gap: 0.6rem; }
.edit-form label { font-size: 0.78rem; font-weight: 600; color: #4a5568; display: flex; flex-direction: column; gap: 0.2rem; }
.edit-form input { font-size: 0.8rem; padding: 0.35rem 0.5rem; border: 1px solid #dce1e8; border-radius: 4px; }
.edit-form textarea { font-size: 0.78rem; padding: 0.4rem; border: 1px solid #dce1e8; border-radius: 4px; font-family: var(--font-mono); }
.form-row { display: flex; gap: 0.75rem; }
.form-row label { flex: 1; }

.btn-primary { background: var(--accent); color: #fff; border: none; padding: 0.4rem 1rem; border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer; }
.btn-secondary { background: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border); padding: 0.4rem 1rem; border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer; }
.btn-danger { background: #dc2626; color: #fff; border: none; padding: 0.4rem 1rem; border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer; }
.btn-danger:hover { background: #b91c1c; }
.btn-sm { font-size: 0.75rem; padding: 0.35rem 0.75rem; }
</style>
