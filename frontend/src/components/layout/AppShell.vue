<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '@/stores/appStore'
import SvgIcon from '@/components/common/SvgIcon.vue'
import DesignLab from '@/components/design/DesignLab.vue'
import KnowledgeBrowser from '@/components/knowledge/KnowledgeBrowser.vue'
import DesignHistory from '@/components/history/DesignHistory.vue'
import SkillsView from '@/components/skills/SkillsView.vue'
import ResultsView from '@/components/results/ResultsView.vue'

const store = useAppStore()

const tabs = [
  { id: 'design',    label: 'Design Lab',     icon: 'flask' },
  { id: 'results',   label: 'Results',         icon: 'chart' },
  { id: 'knowledge', label: 'Knowledge Base',  icon: 'book' },
  { id: 'skills',    label: 'Skills',          icon: 'brain' },
  { id: 'history',   label: 'Design History',  icon: 'history' },
]

const activeTabComponent = computed(() => {
  const map: Record<string, any> = {
    design: DesignLab,
    knowledge: KnowledgeBrowser,
    history: DesignHistory,
    skills: SkillsView,
    results: ResultsView,
  }
  return map[store.activeTab] || DesignLab
})

</script>

<template>
  <div class="app-shell">
    <!-- ========== LEFT SIDEBAR ========== -->
    <aside class="sidebar">
      <!-- Brand -->
      <div class="sidebar-brand">
        <SvgIcon name="snowflake" :size="36" class="sidebar-logo" />
        <div class="sidebar-title">
          <h1>EvoAgent-AFP</h1>
          <span>Antifreeze Protein Design</span>
        </div>
      </div>

      <!-- Navigation Tabs -->
      <nav class="sidebar-nav">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :class="['nav-item', { active: store.activeTab === tab.id }]"
          @click="store.setTab(tab.id)"
        >
          <SvgIcon :name="tab.icon" :size="18" class="nav-icon" />
          <span class="nav-label">{{ tab.label }}</span>
        </button>
      </nav>

      <!-- Memory Stats -->
      <div class="sidebar-section" v-if="store.memoryStats">
        <div class="section-label">Design Memory</div>
        <div class="stat-mini">
          <div class="stat-row">
            <span class="stat-dot red"></span>
            <span>{{ store.memoryStats.forbidden_zones }} forbidden zones</span>
          </div>
          <div class="stat-row">
            <span class="stat-dot amber"></span>
            <span>{{ store.memoryStats.total_mutations_applied }} mutations</span>
          </div>
        </div>
      </div>

    </aside>

    <!-- ========== MAIN CONTENT ========== -->
    <main class="main-content">
      <component :is="activeTabComponent" />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
  width: 100%;
}

/* ===== SIDEBAR ===== */
.sidebar {
  width: 210px;
  min-width: 210px;
  background: var(--bg-sidebar);
  color: var(--text-sidebar);
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow-y: auto;
  position: sticky;
  top: 0;
  height: 100vh;
  z-index: 10;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.25rem 1.25rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.sidebar-logo {
  flex-shrink: 0;
  filter: drop-shadow(0 0 6px rgba(59, 130, 246, 0.5));
}

.sidebar-title h1 {
  font-size: 1.15rem;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.01em;
  line-height: 1.2;
}

.sidebar-title span {
  font-size: 0.65rem;
  color: var(--text-sidebar);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

/* Navigation */
.sidebar-nav {
  padding: 0.75rem 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.55rem 0.75rem;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-sidebar);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
  width: 100%;
  text-align: left;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #ffffff;
}

.nav-item.active {
  background: rgba(59, 130, 246, 0.2);
  color: var(--text-sidebar-active);
  font-weight: 600;
}

.nav-item.active .nav-icon {
  filter: brightness(1.3);
}

/* Sections */
.sidebar-section {
  padding: 0.75rem 1.25rem;
}

.section-label {
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: rgba(208, 221, 240, 0.5);
  margin-bottom: 0.5rem;
}

.project-select {
  width: 100%;
  padding: 0.45rem 0.65rem;
  font-size: 0.8rem;
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-sidebar);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-sm);
  cursor: pointer;
  outline: none;
}

.project-select:focus {
  border-color: var(--accent);
}

.project-select option {
  background: var(--bg-sidebar);
  color: #fff;
}

/* Mini Stats */
.stat-mini {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.stat-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.78rem;
}

.stat-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.stat-dot.blue  { background: var(--accent); }
.stat-dot.cyan  { background: var(--accent-cyan); }
.stat-dot.green { background: var(--success); }
.stat-dot.red   { background: var(--danger); }
.stat-dot.amber { background: var(--warning); }

/* ===== MAIN CONTENT ===== */
.main-content {
  flex: 1;
  background: var(--bg-primary);
  overflow-y: auto;
  min-height: 100vh;
}
</style>
