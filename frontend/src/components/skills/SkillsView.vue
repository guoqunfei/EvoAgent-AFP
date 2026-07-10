<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useApi } from '@/composables/useApi'
import { marked } from 'marked'
import SvgIcon from '@/components/common/SvgIcon.vue'

const api = useApi()
const loading = ref(false)
const saving = ref(false)
const skills = ref<Array<{ name: string; description: string; version: string; path: string; content: string }>>([])
const expandedSkill = ref<string | null>(null)
const editingSkill = ref<string | null>(null)
const editContent = ref('')
const activeCategory = ref<string>('all')
const saveMsg = ref('')

const categories = ['all', 'design', 'mutation', 'optimization', 'evolution', 'general']

function toggleSkill(name: string) {
  if (editingSkill.value) return
  expandedSkill.value = expandedSkill.value === name ? null : name
}

async function loadSkills() {
  loading.value = true
  try {
    const res = await api.listSkillFiles()
    skills.value = res.skills || []
  } catch {
    skills.value = []
  } finally {
    loading.value = false
  }
}

function startEdit(skill: { name: string; content: string }) {
  editingSkill.value = skill.name
  editContent.value = skill.content
  expandedSkill.value = skill.name
}

function cancelEdit() {
  editingSkill.value = null
  editContent.value = ''
  saveMsg.value = ''
}

const deleteTarget = ref<string | null>(null)
const deleting = ref(false)

function confirmDelete(name: string) {
  deleteTarget.value = name
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await api.deleteSkillFile(deleteTarget.value)
    skills.value = skills.value.filter((s) => s.path !== deleteTarget.value)
    if (expandedSkill.value === deleteTarget.value) expandedSkill.value = null
    deleteTarget.value = null
  } catch {
    saveMsg.value = '删除失败'
  } finally {
    deleting.value = false
  }
}

function cancelDelete() {
  deleteTarget.value = null
}

async function saveEdit() {
  if (!editingSkill.value) return
  saving.value = true
  saveMsg.value = ''
  try {
    await api.updateSkillFile(editingSkill.value, editContent.value)
    const idx = skills.value.findIndex((s) => s.path === editingSkill.value)
    if (idx !== -1) skills.value[idx].content = editContent.value
    saveMsg.value = '已保存'
    setTimeout(() => { saveMsg.value = '' }, 2000)
    editingSkill.value = null
  } catch {
    saveMsg.value = '保存失败'
  } finally {
    saving.value = false
  }
}

function filteredSkills() {
  let list = skills.value
  if (activeCategory.value !== 'all') {
    list = list.filter((s) => s.path.includes(activeCategory.value) || s.description.includes(activeCategory.value))
  }
  return list
}

function renderMD(text: string): string {
  // Show only the body (after YAML frontmatter)
  let body = text
  if (body.startsWith('---')) {
    const parts = body.split('---', 3)
    body = parts.length >= 3 ? parts.slice(2).join('---') : body
  }
  return marked.parse(body, { async: false }) as string
}

function categoryBadge(path: string): string {
  if (path.includes('evolution')) return 'Evolution'
  if (path.includes('optimization')) return 'Optimization'
  if (path.includes('mutation')) return 'Mutation'
  if (path.includes('design')) return 'Design'
  return 'General'
}

onMounted(() => { loadSkills() })
</script>

<template>
  <div class="skills-view">
    <div class="sk-header">
      <div>
        <h2><SvgIcon name="brain" :size="20" /> Design Skills</h2>
        <p class="text-muted text-sm">AFP 智能体自学习技能库 — 基于 AgentSkills.io 标准，支持 Markdown 编辑</p>
      </div>
      <div class="sk-header-actions">
        <span v-if="saveMsg" class="save-msg">{{ saveMsg }}</span>
        <button class="btn-secondary" @click="loadSkills" :disabled="loading">
          <SvgIcon name="refresh" :size="14" /> {{ loading ? 'Loading...' : 'Refresh' }}
        </button>
      </div>
    </div>

    <div class="sk-stats-bar" v-if="skills.length">
      <div class="sk-stat"><span class="sk-stat-val">{{ skills.length }}</span><span class="sk-stat-label">Skills</span></div>
    </div>

    <div v-if="loading" class="sk-loading text-muted">Loading skills...</div>

    <div v-else class="sk-grid">
      <div
        v-for="skill in filteredSkills()"
        :key="skill.path"
        :class="['skill-card card', { expanded: expandedSkill === skill.path }]"
      >
        <div class="skill-card-top" @click="toggleSkill(skill.path)">
          <div class="skill-card-header">
            <SvgIcon name="brain" :size="18" class="skill-icon" />
            <div>
              <h4>{{ skill.name || skill.path }}</h4>
              <span class="badge badge-navy">{{ categoryBadge(skill.path) }}</span>
              <span class="text-xs text-muted" style="margin-left:0.5rem">v{{ skill.version || '1.0.0' }}</span>
            </div>
          </div>
          <div class="skill-actions" @click.stop>
            <button
              v-if="editingSkill !== skill.path"
              class="btn-mini btn-delete"
              @click="confirmDelete(skill.path)"
            >删除</button>
            <button
              v-if="editingSkill !== skill.path"
              class="btn-mini"
              @click="startEdit(skill)"
            >编辑</button>
          </div>
        </div>

        <p class="skill-desc text-sm">{{ skill.description }}</p>

        <!-- Editing mode -->
        <div v-if="editingSkill === skill.path" class="skill-editor fade-in">
          <textarea
            v-model="editContent"
            class="skill-textarea"
            rows="20"
          ></textarea>
          <div class="editor-actions">
            <button class="btn-primary btn-sm" @click="saveEdit" :disabled="saving">
              {{ saving ? 'Saving...' : '保存' }}
            </button>
            <button class="btn-secondary btn-sm" @click="cancelEdit">取消</button>
          </div>
        </div>

        <!-- Preview mode -->
        <div v-else-if="expandedSkill === skill.path" class="skill-preview fade-in">
          <div class="skill-md" v-html="renderMD(skill.content)"></div>
        </div>
      </div>

      <div v-if="!loading && filteredSkills().length === 0" class="empty-state">
        <SvgIcon name="brain" :size="36" class="empty-icon" />
        <p class="text-muted">No skills found.</p>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="deleteTarget" class="modal-overlay" @click.self="cancelDelete">
      <div class="modal-card">
        <h3>确认删除</h3>
        <p>确定要删除技能 <strong>{{ deleteTarget }}</strong> 吗？此操作不可恢复。</p>
        <div class="modal-actions">
          <button class="btn-danger" @click="doDelete" :disabled="deleting">{{ deleting ? '删除中...' : '确认删除' }}</button>
          <button class="btn-secondary" @click="cancelDelete">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.skills-view {
  padding: 1.5rem 2rem;
  max-width: 100%;
}

.sk-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  gap: 1rem;
}

.sk-header h2 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.25rem;
}

.sk-header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.save-msg {
  font-size: 0.75rem;
  color: var(--success);
  font-weight: 600;
}

.sk-stats-bar {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1rem;
  padding: 0.6rem 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
}

.sk-stat {
  display: flex;
  align-items: baseline;
  gap: 0.35rem;
}

.sk-stat-val {
  font-family: var(--font-mono);
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--accent-cyan);
}

.sk-stat-label {
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
}

.sk-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.skill-card {
  transition: all 0.15s ease;
}

.skill-card.expanded {
  border-color: var(--accent);
}

.skill-card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  cursor: pointer;
}

.skill-card-header {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.skill-card-header h4 {
  font-size: 0.9rem;
  margin-bottom: 0.2rem;
}

.skill-icon {
  color: var(--accent-cyan);
  margin-top: 2px;
  flex-shrink: 0;
}

.skill-desc {
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
  line-height: 1.5;
  margin-top: 0.5rem;
}

.skill-actions {
  flex-shrink: 0;
}

.btn-mini {
  font-size: 0.68rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--accent);
  cursor: pointer;
}
.btn-mini:hover {
  background: var(--accent-light);
}

/* Editor */
.skill-editor {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-light);
}

.skill-textarea {
  width: 100%;
  font-family: var(--font-mono);
  font-size: 0.78rem;
  line-height: 1.5;
  padding: 0.75rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: #fafbfc;
  resize: vertical;
  min-height: 300px;
}

.editor-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.btn-sm {
  font-size: 0.75rem;
  padding: 0.3rem 0.75rem;
}

/* Preview */
.skill-preview {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-light);
}

.skill-md {
  font-size: 0.82rem;
  line-height: 1.65;
  color: var(--text-primary);
}

.skill-md :deep(h1) { font-size: 1.2rem; margin: 0.75rem 0 0.5rem; }
.skill-md :deep(h2) { font-size: 1.05rem; margin: 0.6rem 0 0.4rem; color: #2c3e6b; }
.skill-md :deep(h3) { font-size: 0.9rem; margin: 0.5rem 0 0.3rem; }
.skill-md :deep(p) { margin: 0.35rem 0; }
.skill-md :deep(ul), .skill-md :deep(ol) { margin: 0.3rem 0; padding-left: 1.5rem; }
.skill-md :deep(li) { margin-bottom: 0.2rem; }
.skill-md :deep(code) {
  background: rgba(0,0,0,0.06);
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
}
.skill-md :deep(pre) {
  background: #f8f9fa;
  padding: 0.6rem;
  border-radius: 6px;
  overflow-x: auto;
  border: 1px solid #e2e8f0;
}
.skill-md :deep(pre code) { background: none; padding: 0; }
.skill-md :deep(blockquote) {
  border-left: 3px solid var(--accent);
  margin: 0.5rem 0;
  padding: 0.3rem 0.75rem;
  background: var(--accent-light);
  border-radius: 0 4px 4px 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem;
  gap: 0.5rem;
}

.empty-icon {
  opacity: 0.2;
  color: var(--text-secondary);
}

.sk-loading {
  text-align: center;
  padding: 3rem;
}

.btn-delete {
  color: #dc2626;
  border-color: #fecaca;
  background: #fef2f2;
}
.btn-delete:hover {
  background: #fee2e2;
  border-color: #fca5a5;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-card {
  background: #fff;
  border-radius: 12px;
  padding: 1.5rem 2rem;
  max-width: 420px;
  width: 90%;
  box-shadow: 0 8px 30px rgba(0,0,0,0.15);
}

.modal-card h3 {
  font-size: 1.1rem;
  margin: 0 0 0.5rem;
  color: #1a202c;
}

.modal-card p {
  font-size: 0.85rem;
  color: #4a5568;
  margin: 0 0 1.25rem;
  line-height: 1.5;
}

.modal-actions {
  display: flex;
  gap: 0.6rem;
  justify-content: flex-end;
}

.btn-danger {
  background: #dc2626;
  color: #fff;
  border: none;
  padding: 0.4rem 1rem;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
}
.btn-danger:hover { background: #b91c1c; }
.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
