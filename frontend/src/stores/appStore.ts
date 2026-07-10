import { defineStore } from 'pinia'
import type {
  Project,
  DesignRound,
  IceBindingResult,
  KnowledgeSummary,
  MemoryStats,
  DesignSkill,
  ChatMessage,
  KnowledgeMotif,
} from '@/types/api'

export const useAppStore = defineStore('afp', {
  state: () => ({
    activeTab: 'design' as string,
    activeProjectId: null as string | null,
    projects: [] as Project[],
    currentSequence: '',
    applicationScenario: 'general',
    designTarget: '',
    designRounds: [] as DesignRound[],
    isDesignRunning: false,
    lastSimResult: null as IceBindingResult | null,
    knowledgeSummary: null as KnowledgeSummary | null,
    memoryStats: null as MemoryStats | null,
    skills: [] as DesignSkill[],
    motifs: [] as KnowledgeMotif[],
    chatMessages: [] as ChatMessage[],
    sequenceAnalysis: null as any,
  }),

  getters: {
    activeProject: (state) =>
      state.projects.find((p) => p.id === state.activeProjectId) ?? null,

    currentRound: (state) =>
      state.designRounds.length > 0
        ? state.designRounds[state.designRounds.length - 1]
        : null,

    totalMutations: (state) =>
      state.designRounds.reduce(
        (sum, r) => sum + r.mutations.length,
        0
      ),

    sortedSkills: (state) =>
      [...state.skills].sort((a, b) => b.confidence - a.confidence),
  },

  actions: {
    setTab(tab: string) {
      this.activeTab = tab
    },

    setActiveProject(id: string | null) {
      this.activeProjectId = id
    },

    addProject(project: Project) {
      this.projects.push(project)
      this.activeProjectId = project.id
    },

    setSequence(seq: string) {
      this.currentSequence = seq
    },

    setDesignTarget(target: string) {
      this.designTarget = target
    },

    setScenario(scenario: string) {
      this.applicationScenario = scenario
    },

    addDesignRound(round: DesignRound) {
      this.designRounds.push(round)
    },

    updateLastRound(updates: Partial<DesignRound>) {
      if (this.designRounds.length > 0) {
        const last = this.designRounds[this.designRounds.length - 1]
        Object.assign(last, updates)
      }
    },

    setDesignRunning(running: boolean) {
      this.isDesignRunning = running
    },

    setSimResult(result: IceBindingResult) {
      this.lastSimResult = result
    },

    setKnowledgeSummary(summary: KnowledgeSummary) {
      this.knowledgeSummary = summary
    },

    setMemoryStats(stats: MemoryStats) {
      this.memoryStats = stats
    },

    setSkills(skills: DesignSkill[]) {
      this.skills = skills
    },

    setMotifs(motifs: KnowledgeMotif[]) {
      this.motifs = motifs
    },

    setSequenceAnalysis(analysis: any) {
      this.sequenceAnalysis = analysis
    },

    addChatMessage(msg: ChatMessage) {
      this.chatMessages.push(msg)
    },

    updateChatMessage(id: string, updates: Partial<ChatMessage>) {
      const idx = this.chatMessages.findIndex((m) => m.id === id)
      if (idx !== -1) {
        this.chatMessages.splice(idx, 1, { ...this.chatMessages[idx], ...updates })
      }
    },

    removeChatMessage(id: string) {
      const idx = this.chatMessages.findIndex((m) => m.id === id)
      if (idx !== -1) {
        this.chatMessages.splice(idx, 1)
      }
    },

    clearChat() {
      this.chatMessages = []
    },

    clearDesignRounds() {
      this.designRounds = []
      this.lastSimResult = null
      this.sequenceAnalysis = null
    },

    resetAll() {
      this.activeTab = 'design'
      this.activeProjectId = null
      this.currentSequence = ''
      this.designTarget = ''
      this.designRounds = []
      this.isDesignRunning = false
      this.lastSimResult = null
      this.memoryStats = null
      this.chatMessages = []
      this.sequenceAnalysis = null
    },
  },
})
