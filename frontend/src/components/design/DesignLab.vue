<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useAppStore } from '@/stores/appStore'
import { useApi } from '@/composables/useApi'
import { marked } from 'marked'
import SvgIcon from '@/components/common/SvgIcon.vue'
import BatchProcessor from './BatchProcessor.vue'
import type { ChatMessage, DesignRound } from '@/types/api'

const store = useAppStore()
const api = useApi()

const chatInput = ref('')
const chatMsgs = ref<HTMLElement | null>(null)
const chatSessionId = ref<string | null>(null)
const chatLoading = ref(false)
const chatModels = ref<Array<{ id: string; label: string; model: string; ready: boolean }>>([])
let chatAbort: (() => void) | null = null
const selectedModel = ref('deepseek')
const currentSessionId = ref('')
const sessionInput = ref('')

// Multi-model comparison state
const showComparison = ref(false)
const comparingModels = ref(false)
const comparisonResults = ref<Array<{
  model_key: string
  model_name: string
  provider: string
  response: string
  success: boolean
  error_message: string | null
  latency_ms: number | null
}>>([])

// Batch processing state
const showBatchPanel = ref(false)
const batchInput = ref('')
const batchProcessing = ref(false)
const batchProgress = ref(0)
const batchStatus = ref<any>(null)
const batchResults = ref<Array<{
  sequence_id: string
  sequence: string
  analysis: string
  success: boolean
  error_message: string | null
  processing_time_ms: number | null
  model_used: string | null
}>>([])
const batchId = ref<string | null>(null)
const batchModelKey = ref('deepseek')
const batchAnalysisType = ref<'quick' | 'comprehensive'>('comprehensive')
const batchConcurrentLimit = ref(5)

async function loadSession(sid: string) {
  if (!sid.trim()) return
  try {
    const data = await api.getSession(sid.trim())
    store.clearChat()

    // Restore sequence
    const seq = (data.analysis as any)?.sequence || (data.rounds as any)?.original_sequence || ''
    if (seq) {
      store.setSequence(seq)
      resetPipeline()
    }

    // Restore design target as user message
    const target = (data.rounds as any)?.design_target || (data.summary as any)?.design_target || ''
    if (target) {
      store.addChatMessage({
        id: Date.now().toString(),
        role: 'user',
        content: target.length > 200 ? target.slice(0, 200) + '...' : target,
        timestamp: new Date().toISOString(),
      })
    }

    // Restore chat log as ONE continuous assistant message (same as real-time streaming)
    const chatLog = (data as any).chat_log as string | undefined
    if (chatLog) {
      store.addChatMessage({
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: chatLog.trim() || '(空)',
        timestamp: new Date().toISOString(),
      })
    } else {
      // No chat log — show summary from rounds
      store.addChatMessage({
        id: Date.now().toString(),
        role: 'system',
        content: `📂 已加载会话 \`${sid}\` — 无聊天记录（旧版本生成）`,
        timestamp: new Date().toISOString(),
      })
      const rounds = (data.rounds as any)?.rounds as Array<any> | undefined
      if (rounds && rounds.length > 0) {
        let summary = '### 历史设计轮次\n\n'
        for (const r of rounds) {
          const muts = (r.mutations as string[])?.join(', ') || '—'
          summary += `- **Round ${r.round}**: ${muts} | ${r.verdict || '?'} | TH: ${r.th_change_pct || 0}% | IRI: ${r.iri_change_pct || 0}%\n`
        }
        store.addChatMessage({
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: summary,
          timestamp: new Date().toISOString(),
        })
      }
    }

    currentSessionId.value = sid
    sessionInput.value = sid
  } catch {
    store.addChatMessage({
      id: Date.now().toString(),
      role: 'error',
      content: `会话 \`${sid}\` 不存在`,
      timestamp: new Date().toISOString(),
    })
  }
}

// Listen for session load requests from Results page
window.addEventListener('load-session', ((e: CustomEvent) => {
  const sid = e.detail
  if (sid) {
    sessionInput.value = sid
    loadSession(sid)
  }
}) as EventListener)

async function loadChatModels() {
  try {
    const res = await api.listChatModels()
    chatModels.value = res.models
    selectedModel.value = res.default
  } catch {
    // keep defaults
  }
}

// Load models on mount
loadChatModels()

// Pipeline state: 0=idle, 1=analyze, 2=mutate, 3=evaluate, 4=simulate, 5=final_evaluate
const pipelineStep = ref(0)
const pipelineSteps = [
  { index: 1, key: 'analyze',  label: 'Analyze',     icon: 'search' },
  { index: 2, key: 'mutate',   label: 'Mutate',      icon: 'dna' },
  { index: 3, key: 'evaluate', label: 'Evaluate',    icon: 'shield' },
  { index: 4, key: 'simulate', label: 'Simulate',    icon: 'ice' },
  { index: 5, key: 'finalize', label: 'Finalize',    icon: 'target' },
]
function advancePipeline(step: number) { pipelineStep.value = step }
function resetPipeline() { pipelineStep.value = 0 }

const scenarioOptions = [
  { value: 'general', label: 'General Purpose' },
  { value: 'ice_cream', label: 'Ice Cream' },
  { value: 'cell_cryopreservation', label: 'Cell Cryopreservation' },
  { value: 'organ_preservation', label: 'Organ Preservation' },
  { value: 'anti_ice_coating', label: 'Anti-Ice Coating' },
]

// Configure marked for GFM tables, code blocks, etc.
marked.setOptions({
  gfm: true,
  breaks: true,
})

function renderMD(text: string): string {
  // Pre-process: wrap round headers for highlighting
  let processed = text.replace(
    /^(.*Round\s+\d+\/\d+.*)$/gm,
    '<div class="round-header-line">$1</div>'
  )
  // Pre-process: wrap separator lines
  processed = processed.replace(
    /^(={3,}|-{3,})$/gm,
    '<hr class="section-divider">'
  )

  // Detect JSON blocks using string-aware brace counting
  const lines = processed.split('\n')
  const result: string[] = []
  let inJson = false
  let braceDepth = 0
  let jsonLines: string[] = []

  // Count braces in a line, ignoring those inside JSON strings
  function countBraces(s: string): number {
    let delta = 0
    let inStr = false
    let escape = false
    for (const ch of s) {
      if (escape) { escape = false; continue }
      if (ch === '\\') { escape = true; continue }
      if (ch === '"') { inStr = !inStr; continue }
      if (inStr) continue
      if (ch === '{' || ch === '[') delta++
      if (ch === '}' || ch === ']') delta--
    }
    return delta
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()

    // Inline JSON after labels like "📥 参数:" or "✅ 结果:"
    const hasInlineJson = !inJson && /\{.*"[\w]+"\s*:/.test(trimmed) && !/^[{\[]/.test(trimmed)
    if (hasInlineJson) {
      const jsonStart = trimmed.indexOf('{')
      if (jsonStart > 0) {
        result.push(trimmed.substring(0, jsonStart))
        result.push('<pre class="json-block"><code>' + formatJson(trimmed.substring(jsonStart)) + '</code></pre>')
        continue
      }
    }

    // JSON start: line starts with { or [
    if (/^[{\[]/.test(trimmed) && !inJson) {
      inJson = true
      braceDepth = 0
      jsonLines = [line]
      braceDepth += countBraces(line)
      if (braceDepth <= 0) {
        result.push('<pre class="json-block"><code>' + formatJson(jsonLines.join('\n')) + '</code></pre>')
        inJson = false
        jsonLines = []
      }
      continue
    }

    if (inJson) {
      jsonLines.push(line)
      braceDepth += countBraces(line)
      if (braceDepth <= 0 && jsonLines.length >= 1) {
        result.push('<pre class="json-block"><code>' + formatJson(jsonLines.join('\n')) + '</code></pre>')
        inJson = false
        braceDepth = 0
        jsonLines = []
      }
    } else {
      result.push(line)
    }
  }
  // Flush partial JSON
  if (inJson && jsonLines.length > 0) {
    result.push('<pre class="json-block"><code>' + formatJson(jsonLines.join('\n')) + '</code></pre>')
  }

  return marked.parse(result.join('\n'), { async: false }) as string
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function formatJson(raw: string): string {
  try {
    const formatted = JSON.stringify(JSON.parse(raw), null, 2)
    return highlightJson(formatted)
  } catch {
    return escapeHtml(raw)
  }
}

// JSON syntax highlighting — colorizes keys, strings, numbers, booleans, null
function highlightJson(json: string): string {
  return json.replace(
    /("(?:\\.|[^"\\])*")\s*:/g,                                          // keys
    '<span class="json-key">$1</span>:'
  ).replace(
    /:\s*("(?:\\.|[^"\\])*")/g,                                          // string values
    ': <span class="json-string">$1</span>'
  ).replace(
    /:\s*(-?\d+\.?\d*(?:[eE][+-]?\d+)?)/g,                              // number values
    ': <span class="json-number">$1</span>'
  ).replace(
    /:\s*(true|false)/g,                                                  // boolean values
    ': <span class="json-bool">$1</span>'
  ).replace(
    /:\s*(null)/g,                                                        // null values
    ': <span class="json-null">$1</span>'
  )
}

function isThinkingContent(content: string): boolean {
  return content === '推理中...'
}

async function analyzeSequence() {
  if (!store.currentSequence) return
  advancePipeline(1)
  try {
    const res = await api.simulateIceBinding(store.currentSequence)
    store.setSimResult(res.result)
    store.addChatMessage({
      id: Date.now().toString(),
      role: 'assistant',
      content: `**Sequence Analysis**\n\n- Geometry Score: \`${res.result.geometryScore?.toFixed(3)}\`\n- TH Estimate: \`${res.result.thEstimate?.toFixed(2)}°C\`\n- IRI Estimate: \`${res.result.iriEstimate?.toFixed(2)}µM\`\n\n${res.result.activityAssessment}`,
      timestamp: new Date().toISOString(),
    })
    advancePipeline(2)
  } catch (e: any) {
    resetPipeline()
    store.addChatMessage({
      id: Date.now().toString(),
      role: 'error',
      content: `Analysis failed: ${e.message}`,
      timestamp: new Date().toISOString(),
    })
  }
}

async function runDesign() {
  if (!store.currentSequence || store.isDesignRunning) return
  store.setDesignRunning(true)
  store.clearDesignRounds()
  advancePipeline(1)

  store.addChatMessage({
    id: Date.now().toString(),
    role: 'system',
    content: `Starting AFP design for ${store.currentSequence.length}aa sequence with target: "${store.designTarget || 'improve TH activity'}"`,
    timestamp: new Date().toISOString(),
  })

  try {
    const res = await api.runDesign({
      sequence: store.currentSequence,
      designTarget: store.designTarget || 'improve TH activity',
      applicationScenario: store.applicationScenario,
      maxIterations: 5,
    })

    // Add a simulated first round for demo
    advancePipeline(2)
    const round1: DesignRound = {
      roundNumber: 1,
      status: 'in_progress',
      mutations: [
        { position: 2, from: 'T', to: 'N', rationale: 'Enhance ice plane matching at position 2' },
        { position: 5, from: 'D', to: 'E', rationale: 'Improve solubility while maintaining charge' },
      ],
      evaluation: null,
      iceBindingSim: null,
    }
    store.addDesignRound(round1)

    store.addChatMessage({
      id: Date.now().toString(),
      role: 'assistant',
      content: `Design started. ID: \`${res.design_id}\`\n\n**Round 1 initiated** with 2 candidate mutations:\n- T2N: Enhance ice plane matching\n- D5E: Improve solubility`,
      timestamp: new Date().toISOString(),
    })

    // Simulate ice binding for the first round
    advancePipeline(3)
    try {
      const simRes = await api.simulateIceBinding(store.currentSequence)
      store.setSimResult(simRes.result)
      store.updateLastRound({ iceBindingSim: simRes.result, status: 'completed' })
      advancePipeline(4)
      store.addChatMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: `**Round 1 Ice Binding Simulation**\n\n- Geometry Score: \`${simRes.result.geometryScore?.toFixed(3)}\`\n- TH Activity: \`${simRes.result.thEstimate?.toFixed(2)}°C\`\n- IRI Activity: \`${simRes.result.iriEstimate?.toFixed(2)}µM\``,
        timestamp: new Date().toISOString(),
      })
      advancePipeline(5)
    } catch {
      // sim not available
    }
  } catch (e: any) {
    resetPipeline()
    store.addChatMessage({
      id: Date.now().toString(),
      role: 'error',
      content: `Design failed: ${e.message}`,
      timestamp: new Date().toISOString(),
    })
  } finally {
    store.setDesignRunning(false)
  }
}

function stopChat() {
  if (chatAbort) {
    chatAbort()
    chatAbort = null
  }
  chatLoading.value = false
  const msgs = store.chatMessages
  const lastMsg = msgs[msgs.length - 1]
  if (lastMsg && isThinkingContent(lastMsg.content)) {
    store.updateChatMessage(lastMsg.id, { content: '⏹ 已停止', role: 'system' })
  }
}

async function sendChat() {
  const text = chatInput.value.trim()
  if (!text || chatLoading.value) return

  // Abort any previous streaming request
  if (chatAbort) {
    chatAbort()
    chatAbort = null
  }

  // Add user message FIRST
  const userMsgId = Date.now().toString()
  store.addChatMessage({
    id: userMsgId,
    role: 'user',
    content: text,
    timestamp: new Date().toISOString(),
  })
  chatInput.value = ''
  chatLoading.value = true

  // Immediately show "Thinking" placeholder with animated dots
  const thinkingId = (Date.now() + 1).toString()
  store.addChatMessage({
    id: thinkingId,
    role: 'assistant',
    content: '推理中...',
    timestamp: new Date().toISOString(),
  })
  await nextTick()
  scrollChat()

  // Always use AFP agent for Design Assistant
  const hasSequence = store.currentSequence && store.currentSequence.trim().length >= 10

  try {
    // Ensure we have a valid session - create one if needed
    let sessionId = chatSessionId.value
    if (!sessionId || sessionId === 'default') {
      // Create a new session
      const newSession = await api.createChatSession('AFP Design Chat')
      sessionId = newSession.id
      chatSessionId.value = sessionId
    }

    // Use selected model for chat
    const { abort, readChunks } = api.streamChatMessage(
      sessionId,
      text,
      selectedModel.value
    )
    chatAbort = abort
    let fullContent = ''

    for await (const event of readChunks()) {
      switch (event.type) {
        case 'chunk':
          if (event.content) {
            fullContent += event.content
            // Update with nextTick to avoid blocking DOM rendering
            await nextTick()
            store.updateChatMessage(thinkingId, { content: fullContent, role: 'assistant' })
            await nextTick()
            scrollChat()
          }
          break
        case 'done':
          fullContent += '\n\n---\n✅ **设计运行完成**'
          store.updateChatMessage(thinkingId, { content: fullContent, role: 'assistant' })
          advancePipeline(5)
          break
        case 'error':
          await nextTick()
          store.updateChatMessage(thinkingId, { content: fullContent + '\n\n❌ ' + (event.message || ''), role: 'error' })
          break
      }
    }
  } catch (e: any) {
    const msg = store.chatMessages.find(m => m.id === thinkingId)
    if (msg && isThinkingContent(msg.content)) {
      store.updateChatMessage(thinkingId, { content: '连接中断: ' + (e.message || '请重试'), role: 'error' })
    }
  } finally {
    chatLoading.value = false
    chatAbort = null
  }
}

async function runMultiModelComparison() {
  const text = chatInput.value.trim()
  if (!text || comparingModels.value) return

  // Add user message
  const userMsgId = Date.now().toString()
  store.addChatMessage({
    id: userMsgId,
    role: 'user',
    content: `[ 多模型对比] ${text}`,
    timestamp: new Date().toISOString(),
  })
  chatInput.value = ''
  comparingModels.value = true

  // Show loading message
  const loadingId = (Date.now() + 1).toString()
  store.addChatMessage({
    id: loadingId,
    role: 'system',
    content: ' 正在调用所有7个模型进行对比分析，请稍候...',
    timestamp: new Date().toISOString(),
  })
  await nextTick()
  scrollChat()

  try {
    // Call the compare API
    const result = await api.compareModels(text)
    
    // Remove loading message
    store.removeChatMessage(loadingId)
    
    // Store results
    comparisonResults.value = result.results
    showComparison.value = true
    
    // Add summary message
    const successCount = result.successful
    const failCount = result.failed
    const summary = `## 🔬 多模型对比结果\n\n- **总模型数**: ${result.total_models}\n- **成功**: ${successCount} ✅\n- **失败**: ${failCount} ❌\n\n请在下方查看各模型的详细回复。`
    
    store.addChatMessage({
      id: (Date.now() + 2).toString(),
      role: 'assistant',
      content: summary,
      timestamp: new Date().toISOString(),
    })
  } catch (e: any) {
    store.removeChatMessage(loadingId)
    store.addChatMessage({
      id: (Date.now() + 2).toString(),
      role: 'error',
      content: `❌ 多模型对比失败: ${e.message}`,
      timestamp: new Date().toISOString(),
    })
  } finally {
    comparingModels.value = false
  }
}
function scrollChat() {
  nextTick(() => {
    if (chatMsgs.value) {
      chatMsgs.value.scrollTop = chatMsgs.value.scrollHeight
    }
  })
}

const DEMO_SEQUENCE = 'DTASDAAAAAALTAANAAAAAKLTADNAAAAAAATAR'
function loadDemoSequence() {
  store.setSequence(DEMO_SEQUENCE)
  store.setDesignTarget('Enhance TH activity while maintaining IRI')
  resetPipeline()
  newChatSession()
}

function newChatSession() {
  currentSessionId.value = ''
  sessionInput.value = ''
  store.clearChat()
}

// When user manually edits the sequence, start a fresh session
watch(() => store.currentSequence, (newVal, oldVal) => {
  if (oldVal && newVal !== oldVal && currentSessionId.value) {
    currentSessionId.value = ''
    sessionInput.value = ''
    store.clearChat()
  }
})

// When session input is cleared, reset to fresh session
watch(sessionInput, (val) => {
  if (!val && currentSessionId.value) {
    currentSessionId.value = ''
    store.clearChat()
  }
})

// Sequence viewer hidden — sequence shown directly in input box above

watch(() => store.chatMessages.length, scrollChat)
</script>

<template>
  <div class="design-lab">
    <!-- ===== DESIGN PIPELINE ===== -->
    <div class="pipeline-bar">
      <div class="pipeline-track">
        <template v-for="(step, i) in pipelineSteps" :key="step.key">
          <div
            v-if="i > 0"
            :class="['pipeline-connector', { filled: pipelineStep > step.index, active: pipelineStep === step.index }]"
          ></div>
          <div
            :class="[
              'pipeline-node',
              { active: pipelineStep === step.index },
              { done: pipelineStep > step.index },
            ]"
          >
            <div class="node-circle">
              <SvgIcon v-if="pipelineStep > step.index" name="check" :size="13" />
              <SvgIcon v-else :name="step.icon" :size="14" />
            </div>
            <span class="node-label">{{ step.label }}</span>
          </div>
        </template>
      </div>
      <div class="pipeline-status">
        <span v-if="pipelineStep === 0" class="status-text idle">
          <span class="status-icon">⏳</span> AI 驱动的抗冻蛋白一站式设计平台 — 序列分析 · 智能突变 · 活性评估 · 迭代优化
        </span>
        <span v-else-if="pipelineStep === 1" class="status-text active-step">
          <span class="pulse-dot"></span> Analyzing sequence motifs &amp; ice-binding surface...
        </span>
        <span v-else-if="pipelineStep === 2" class="status-text active-step">
          <span class="pulse-dot"></span> Applying targeted mutations to enhance activity...
        </span>
        <span v-else-if="pipelineStep === 3" class="status-text active-step">
          <span class="pulse-dot"></span> Evaluating structural &amp; functional impact...
        </span>
        <span v-else-if="pipelineStep === 4" class="status-text active-step">
          <span class="pulse-dot"></span> Simulating ice-binding geometry &amp; affinity...
        </span>
        <span v-else-if="pipelineStep === 5" class="status-text done">
          <span class="done-icon">✓</span> Design cycle complete — review results below
        </span>
      </div>
    </div>

    <!-- ===== AFP Sequence Input ===== -->
    <div class="lab-topbar">
      <div class="sequence-area card">
        <div class="label-row">
          <label class="input-label">AFP Sequence <span class="label-hint">— 输入需要智能设计的抗冻蛋白序列</span></label>
          <button class="btn-demo" @click="loadDemoSequence">
            <SvgIcon name="flask" :size="12" /> Demo
          </button>
        </div>
        <textarea
          :value="store.currentSequence"
          @input="store.setSequence(($event.target as HTMLTextAreaElement).value)"
          placeholder="DTASDAAAAAALTAANAAAAAKLTADNAAAAAAATAR"
          rows="1"
          class="seq-input"
        ></textarea>
      </div>
    </div>



    <!-- ===== Batch Processor ===== -->
    <BatchProcessor :available-models="chatModels" />

    <!-- ===== AFP Design Agent Chat (full width, below pipeline) ===== -->
    <div class="afp-chat-area">
      <div class="card chat-compact">
        <div class="chat-header-row">
          <h3>
            <SvgIcon name="send" :size="14" />
            AFP Design Agent
          </h3>
          <div class="chat-header-right">
            <select
              v-model="selectedModel"
              class="model-selector"
              :disabled="chatLoading"
            >
              <option
                v-for="m in chatModels"
                :key="m.id"
                :value="m.id"
              >
                {{ m.label }} ({{ m.model }})
              </option>
            </select>
            <input
              v-model="sessionInput"
              @keyup.enter="loadSession(sessionInput)"
              placeholder="输入会话ID..."
              class="session-id-input"
            />
            <span class="afp-mode-badge">🧬 AFP Agent</span>
          </div>
        </div>
        <div class="chat-messages" ref="chatMsgs">
          <div
            v-for="msg in store.chatMessages"
            :key="msg.id"
            :class="['msg-row', msg.role]"
          >
            <div v-if="msg.role === 'assistant' || msg.role === 'system' || msg.role === 'error'" :class="['msg-avatar assistant-avatar', { 'avatar-running': chatLoading && msg.id === store.chatMessages[store.chatMessages.length - 1]?.id && msg.role === 'assistant' }]">
              <SvgIcon name="snowflake" :size="22" />
            </div>
            <div :class="['msg', msg.role]">
              <div class="msg-content" :class="{ thinking: isThinkingContent(msg.content) }">
                <template v-if="isThinkingContent(msg.content)">
                  <span class="thinking-text">推理中</span>
                  <span class="thinking-dots"><i>.</i><i>.</i><i>.</i></span>
                </template>
                <div v-else v-html="renderMD(msg.content)"></div>
              </div>
              <div v-if="!isThinkingContent(msg.content)" class="msg-time text-xs text-muted">
                {{ new Date(msg.timestamp).toLocaleTimeString() }}
              </div>
            </div>
            <div v-if="msg.role === 'user'" class="msg-avatar user-avatar">
              <svg viewBox="0 0 24 24" fill="currentColor" stroke="none">
                <path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v1.2c0 .66.54 1.2 1.2 1.2h16.8c.66 0 1.2-.54 1.2-1.2v-1.2c0-3.2-6.4-4.8-9.6-4.8z"/>
              </svg>
            </div>
          </div>
          <div v-if="!store.chatMessages.length" class="msg-row assistant">
            <div class="msg-avatar assistant-avatar">
              <SvgIcon name="snowflake" :size="22" />
            </div>
            <div class="chat-welcome">
              <template v-if="store.currentSequence">
                <p class="welcome-text">
                  🧬 <strong>AFP Design Agent</strong> 已就绪，当前序列 {{ store.currentSequence.length }} aa。试试: "分析这个序列的冰结合基序" / "设计突变提升TH活性" / "运行10轮完整设计"
                </p>
              </template>
              <template v-else>
                <p class="welcome-text">
                  你好！我是 <strong>AFP Design Agent</strong>。我可以：分析AFP序列 &amp; 预测冰结合面 / 推荐智能突变提升 TH / IRI 活性 / 对比不同序列变体的模拟结果 / 解释设计原理、基序 &amp; 禁区规则。粘贴序列到上方输入框，解锁完整 AFP 设计能力 →
                </p>
              </template>
            </div>
          </div>
        </div>
        
        <!-- Multi-Model Comparison Results -->
        <div v-if="showComparison" class="comparison-results">
          <div class="comparison-header">
            <h3>🔬 多模型对比结果</h3>
            <button class="btn-close-comparison" @click="showComparison = false">✕ 关闭</button>
          </div>
          <div class="comparison-grid">
            <div 
              v-for="result in comparisonResults" 
              :key="result.model_key"
              class="comparison-card"
              :class="{ 'card-success': result.success, 'card-error': !result.success }"
            >
              <div class="card-header">
                <div class="model-info">
                  <span class="model-name">{{ result.model_name }}</span>
                  <span class="model-key">({{ result.model_key }})</span>
                </div>
                <div class="model-stats">
                  <span v-if="result.latency_ms" class="latency-badge">⏱ {{ result.latency_ms }}ms</span>
                  <span v-if="result.success" class="status-badge success">✅ 成功</span>
                  <span v-else class="status-badge error">❌ 失败</span>
                </div>
              </div>
              <div v-if="result.success" class="card-content">
                <div v-html="renderMD(result.response)"></div>
              </div>
              <div v-else class="card-error-content">
                <p><strong>错误信息:</strong></p>
                <pre>{{ result.error_message }}</pre>
              </div>
            </div>
          </div>
        </div>
        
        <div class="chat-input-row">
          <input
            v-model="chatInput"
            @keyup.enter="sendChat"
            :placeholder="store.currentSequence ? '输入设计目标，如：将TH活性提高3倍...' : '输入AFP相关问题或粘贴序列到上方输入框...'"
            class="chat-input"
            :disabled="chatLoading || comparingModels"
          />
          <button 
            v-if="!chatLoading && !comparingModels" 
            class="btn-compare" 
            @click="runMultiModelComparison"
            title="使用所有7个模型进行对比分析"
          >
            <SvgIcon name="flask" :size="14" />
            多模型对比
          </button>
          <button v-if="chatLoading" class="btn-danger" @click="stopChat">
            ■ 停止
          </button>
          <button v-else-if="!comparingModels" class="btn-primary" @click="sendChat">
            <SvgIcon name="send" :size="14" />
          </button>
        </div>
      </div>
    </div>

    <!-- ===== TWO COLUMN BODY: Sequence Viewer + Rounds | Sim Preview ===== -->
    <div class="lab-body">
      <!-- LEFT: Sequence Viewer + Mutation Rounds -->
      <div class="lab-left">
        <!-- Sequence / Structure Viewer -->
        <!-- Sequence viewer hidden — sequence is shown in the input box above -->

      </div>
    </div>
  </div>
</template>

<style scoped>
.design-lab {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

/* ===== Top Bar ===== */
.lab-topbar {
  padding: 0.5rem 1.5rem 0;
}

.sequence-area {
  padding: 0.5rem 1rem;
}

.label-hint {
  font-weight: 400;
  font-size: 0.7rem;
  color: #94a3b8;
  text-transform: none;
  letter-spacing: 0;
}

.label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.input-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
}

.btn-demo {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
  background: linear-gradient(135deg, var(--accent-light), #e0e7ff);
  color: var(--accent);
  border: 1px solid rgba(59, 130, 246, 0.2);
  transition: all 0.2s ease;
  gap: 0.3rem;
}

.btn-demo:hover {
  background: linear-gradient(135deg, #bfdbfe, #c7d2fe);
  border-color: var(--accent);
  box-shadow: 0 1px 4px rgba(59, 130, 246, 0.2);
}

.seq-input {
  width: 100%;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  line-height: 1.6;
  padding: 0.35rem 0.75rem;
}

.seq-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}

.seq-actions select {
  min-width: 180px;
}

.target-input {
  flex: 1;
  min-width: 200px;
}

/* ===== Two Column Body ===== */
/* ===== Full-width AFP Chat Area ===== */
.afp-chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0 1.5rem;
  margin-bottom: 0.5rem;
  min-height: 0;
}

.afp-chat-area .chat-compact {
  flex: 1;
  min-height: 300px;
  max-height: none;
}

.lab-body {
  display: flex;
  flex: 0 0 auto;
  overflow: hidden;
  padding: 0.5rem 1.5rem 1rem;
  gap: 1.25rem;
  max-height: 35vh;
}

.lab-left {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.lab-left::-webkit-scrollbar {
  width: 4px;
}

/* ===== Sequence / Structure Viewer ===== */
.viewer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.viewer-header h3 {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.95rem;
  margin: 0;
}

.viewer-tabs {
  display: flex;
  gap: 2px;
  background: var(--bg-secondary);
  border-radius: 6px;
  padding: 3px;
}

.tab-btn {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.3rem 0.65rem;
  border-radius: 4px;
  background: transparent;
  color: var(--text-secondary);
  gap: 0.3rem;
  transition: all 0.2s ease;
  border: none;
}

.tab-btn:hover {
  color: var(--text-primary);
  background: rgba(0, 0, 0, 0.04);
}

.tab-btn.active {
  background: var(--bg-card);
  color: var(--accent);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

/* ---- Sequence View ---- */
.seq-display {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  padding: 0.5rem 0;
}

/* ---- Structure View ---- */
.structure-view {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

/* ===== Empty State ===== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  text-align: center;
  gap: 0.5rem;
}

.empty-icon {
  opacity: 0.2;
  color: var(--text-secondary);
}

/* ===== Rounds ===== */
.mutation-rounds > h3 {
  font-size: 0.95rem;
  margin-bottom: 0.75rem;
}

.round-card {
  padding: 1rem;
  margin-bottom: 0.75rem;
}

.round-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.mutations-list {
  margin-bottom: 0.5rem;
}

.eval-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

/* ===== Sim Mini (in rounds) ===== */
.sim-mini {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-light);
}

.sim-metric-sm {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.metric-label-sm {
  font-size: 0.6rem;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--text-secondary);
  letter-spacing: 0.04em;
}

.metric-val-sm {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--accent-cyan);
  font-family: var(--font-mono);
}

/* ===== Chat ===== */
.chat-compact {
  display: flex;
  flex-direction: column;
  min-height: 220px;
  padding: 1rem 1rem;
}

.chat-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: -1rem -1rem 0.75rem -1rem;
  padding: 0.7rem 1rem;
  gap: 0.5rem;
  background: linear-gradient(135deg, #e8edf2 0%, #dce3ea 50%, #e3e9ef 100%);
  border-radius: var(--radius) var(--radius) 0 0;
}

.chat-header-row h3 {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.9rem;
  margin: 0;
  color: #2c3e6b;
}

.chat-header-right {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.session-id-input {
  width: 160px;
  font-size: 0.68rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  border: 1px solid rgba(255,255,255,0.4);
  background: rgba(255,255,255,0.85);
  color: #1a202c;
  outline: none;
}
.session-id-input::placeholder {
  color: #64748b;
}
.session-id-input:focus {
  border-color: rgba(255,255,255,0.8);
  background: #fff;
}

/* Images in chat — constrain to chat width */
.msg-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 6px;
  margin: 0.5rem 0;
}

.afp-mode-badge {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 10px;
  background: rgba(44, 62, 107, 0.1);
  color: #2c3e6b;
  letter-spacing: 0.02em;
}

.model-selector {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  border: 1px solid var(--border);
  cursor: pointer;
  max-width: 150px;
  outline: none;
}

.model-selector:focus {
  border-color: var(--accent);
}

.model-selector:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding-right: 0.15rem;
  margin-bottom: 0.75rem;
}

.chat-messages::-webkit-scrollbar {
  width: 3px;
}

.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 2px;
}

.chat-empty {
  text-align: center;
  padding: 2rem 0;
}

/* ── Welcome State ── */
.chat-welcome {
  padding: 0.55rem 0.7rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  border-bottom-left-radius: 2px;
  max-width: 85%;
  font-size: 0.8rem;
  line-height: 1.5;
}

.welcome-text {
  font-size: 0.8rem;
  color: var(--text-primary);
  line-height: 1.5;
  margin: 0;
}

/* ── Message Row (avatar + bubble) ── */
.msg-row {
  display: flex;
  align-items: flex-end;
  gap: 0.4rem;
}

.msg-row.assistant,
.msg-row.system,
.msg-row.error {
  justify-content: flex-start;
}

.msg-row.user {
  justify-content: flex-end;
}

/* ── Avatars ── */
.msg-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.assistant-avatar {
  background: linear-gradient(135deg, #1e3a5f, #3b82f6);
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(30, 58, 95, 0.25);
}

.avatar-running {
  animation: avatarPulse 1.2s ease-in-out infinite;
  box-shadow: 0 0 0 0 rgba(6, 182, 212, 0.8);
}

@keyframes avatarPulse {
  0%   { box-shadow: 0 0 0 0 rgba(6, 182, 212, 0.7); transform: scale(1); }
  30%  { box-shadow: 0 0 0 6px rgba(6, 182, 212, 0.4), 0 0 16px rgba(34, 211, 238, 0.5); transform: scale(1.06); }
  60%  { box-shadow: 0 0 0 12px rgba(6, 182, 212, 0); transform: scale(1.1); }
  100% { box-shadow: 0 0 0 0 rgba(6, 182, 212, 0); transform: scale(1); }
}

.user-avatar {
  background: linear-gradient(135deg, #6366f1, #a855f7);
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}

/* ── Message Bubbles ── */
.msg {
  padding: 0.55rem 0.7rem;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  line-height: 1.5;
  max-width: calc(100% - 40px);
  word-break: break-word;
}

.msg.user {
  background: var(--accent-light);
  border-bottom-right-radius: 2px;
}

.msg.assistant {
  background: var(--bg-secondary);
  border-bottom-left-radius: 2px;
}

.msg.system {
  background: #f0fdf4;
  max-width: 85%;
  font-size: 0.75rem;
  text-align: center;
  align-self: center;
}

.msg-row.system {
  justify-content: center;
}

.msg.error {
  background: #fee2e2;
  max-width: 85%;
  font-size: 0.75rem;
  color: var(--danger);
  align-self: center;
}

.msg-row.error {
  justify-content: center;
}

/* ── Animated Thinking Dots ── */
.msg-content.thinking {
  display: flex;
  align-items: center;
  gap: 0;
  color: var(--text-secondary);
  font-style: italic;
}

.thinking-text {
  font-size: 0.8rem;
}

.thinking-dots i {
  font-size: 0.9rem;
  font-weight: 700;
  font-style: normal;
  color: var(--accent);
  animation: dotPulse 1.4s ease-in-out infinite;
}

.thinking-dots i:nth-child(1) { animation-delay: 0s; }
.thinking-dots i:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots i:nth-child(3) { animation-delay: 0.4s; }

@keyframes dotPulse {
  0%, 80%, 100% { opacity: 0.15; transform: translateY(0); }
  40% { opacity: 1; transform: translateY(-3px); }
}

/* ── Markdown Content Styling ── */
.msg-content :deep(p) {
  margin: 0 0 0.35rem 0;
}
.msg-content :deep(p:last-child) {
  margin-bottom: 0;
}

/* Tables */
.msg-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.72rem;
  margin: 0.4rem 0;
}

.msg-content :deep(th) {
  text-align: left;
  padding: 0.35rem 0.5rem;
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-secondary);
  background: rgba(0,0,0,0.03);
  border-bottom: 2px solid var(--border);
}

.msg-content :deep(td) {
  padding: 0.3rem 0.5rem;
  border-bottom: 1px solid var(--border-light);
}

.msg-content :deep(tr:last-child td) {
  border-bottom: none;
}

/* Round header highlight */
.msg-content :deep(.round-header-line) {
  background: linear-gradient(135deg, #1e3a5f 0%, #2c5f8a 100%);
  color: #fff;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-weight: 700;
  font-size: 0.85rem;
  margin: 0.6rem 0 0.3rem 0;
  text-align: center;
  letter-spacing: 0.02em;
}

/* Section divider */
.msg-content :deep(.section-divider) {
  border: none;
  border-top: 2px solid #cbd5e1;
  margin: 0.6rem 0;
  opacity: 0.6;
}

/* JSON blocks — scrollable code display */
.msg-content :deep(pre.json-block) {
  background: #f8f9fa;
  padding: 0.6rem 0.75rem;
  border-radius: 6px;
  font-size: 0.72rem;
  margin: 0.4rem 0;
  border: 1px solid #e2e8f0;
  white-space: pre;
  overflow-x: auto;
  max-height: 360px;
  overflow-y: auto;
  font-family: var(--font-mono);
  line-height: 1.45;
  color: #334155;
}

.msg-content :deep(pre.json-block code) {
  background: none;
  padding: 0;
  border: none;
  font-size: 0.72rem;
  white-space: pre;
  font-family: var(--font-mono);
  color: #334155;
}

/* JSON syntax highlighting */
.msg-content :deep(.json-key)   { color: #0550ae; font-weight: 600; }
.msg-content :deep(.json-string){ color: #0a3069; }
.msg-content :deep(.json-number){ color: #0550ae; }
.msg-content :deep(.json-bool)  { color: #cf222e; font-weight: 600; }
.msg-content :deep(.json-null)  { color: #6e7781; font-style: italic; }

/* Code blocks */
.msg-content :deep(pre) {
  background: #f8f9fa;
  padding: 0.6rem 0.75rem;
  border-radius: 6px;
  font-size: 0.72rem;
  overflow-x: auto;
  margin: 0.4rem 0;
  border: 1px solid #e2e8f0;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 400px;
  overflow-y: auto;
}

.msg-content :deep(code) {
  font-family: var(--font-mono);
  font-size: 0.72rem;
}

.msg-content :deep(pre code) {
  background: none;
  padding: 0;
  border: none;
  font-size: 0.72rem;
  white-space: pre-wrap;
}

.msg-content :deep(:not(pre) > code) {
  background: rgba(0,0,0,0.06);
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  font-size: 0.72rem;
}

/* Tables */
.msg-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.74rem;
  margin: 0.5rem 0;
}
.msg-content :deep(th) {
  text-align: left;
  padding: 0.4rem 0.6rem;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: #4a5568;
  background: #f1f5f9;
  border-bottom: 2px solid #cbd5e1;
}
.msg-content :deep(td) {
  padding: 0.35rem 0.6rem;
  border-bottom: 1px solid #e2e8f0;
}
.msg-content :deep(tr:last-child td) {
  border-bottom: none;
}

/* Lists */
.msg-content :deep(ul), .msg-content :deep(ol) {
  margin: 0.25rem 0;
  padding-left: 1.2rem;
}

.msg-content :deep(li) {
  margin-bottom: 0.15rem;
  font-size: 0.78rem;
  line-height: 1.4;
}

/* Blockquote */
.msg-content :deep(blockquote) {
  border-left: 3px solid var(--accent);
  margin: 0.35rem 0;
  padding: 0.25rem 0.6rem;
  background: var(--accent-light);
  border-radius: 0 4px 4px 0;
  font-size: 0.78rem;
  color: var(--text-secondary);
}

/* Horizontal rule */
.msg-content :deep(hr) {
  border: none;
  border-top: 1px solid var(--border-light);
  margin: 0.5rem 0;
}

/* Bold / Italic */
.msg-content :deep(strong) {
  font-weight: 700;
  color: var(--text-primary);
}

.msg-content :deep(em) {
  font-style: italic;
}

.msg-time {
  margin-top: 0.2rem;
}

.chat-input-row {
  display: flex;
  gap: 0.5rem;
}

.chat-input {
  flex: 1;
  font-size: 0.8rem;
}

.btn-compare {
  background: linear-gradient(135deg, #8b5cf6, #a78bfa);
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  white-space: nowrap;
}

.btn-compare:hover:not(:disabled) {
  background: linear-gradient(135deg, #7c3aed, #8b5cf6);
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.3);
  transform: translateY(-1px);
}

.btn-compare:active:not(:disabled) {
  transform: translateY(0);
}

.btn-compare:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-spinner-small {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}

/* ===== Sim Preview ===== */
.sim-preview {
  padding: 1rem;
}

.sim-preview h4 {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
}

.sim-metrics {
  display: flex;
  justify-content: space-around;
  margin-bottom: 0.75rem;
}

.metric-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
}

.metric-val {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--accent-cyan);
  font-family: var(--font-mono);
}

.metric-label {
  font-size: 0.65rem;
  text-transform: uppercase;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.03em;
}

.sim-assessment {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
  padding: 0.5rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  line-height: 1.5;
}

/* ================================================
   Design Pipeline Stepper
   ================================================ */
.pipeline-bar {
  margin: 0.75rem 1.5rem 0;
  padding: 0.7rem 1.5rem 0.6rem;
  background: linear-gradient(180deg, #fafbfc 0%, #f5f7fa 100%);
  border: 1px solid #dce1e8;
  border-left: 3px solid #2c3e6b;
  border-radius: var(--radius);
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  position: relative;
  overflow: hidden;
}

/* ---- Track ---- */
.pipeline-track {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 0;
  padding-bottom: 0.15rem;
}

/* ---- Per-step color palette ---- */
/* Analyze: cyan-blue, Mutate: violet, Evaluate: amber, Simulate: teal, Finalize: emerald */
.pipeline-node:nth-child(1) .node-circle { border-color: #06b6d4; color: #06b6d4; }
.pipeline-node:nth-child(2) .node-circle { border-color: #8b5cf6; color: #8b5cf6; }
.pipeline-node:nth-child(3) .node-circle { border-color: #f59e0b; color: #f59e0b; }
.pipeline-node:nth-child(4) .node-circle { border-color: #14b8a6; color: #14b8a6; }
.pipeline-node:nth-child(5) .node-circle { border-color: #10b981; color: #10b981; }

.pipeline-node:nth-child(1) .node-label { color: #0891b2; }
.pipeline-node:nth-child(2) .node-label { color: #7c3aed; }
.pipeline-node:nth-child(3) .node-label { color: #d97706; }
.pipeline-node:nth-child(4) .node-label { color: #0d9488; }
.pipeline-node:nth-child(5) .node-label { color: #059669; }

/* ---- Node ---- */
.pipeline-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  flex-shrink: 0;
  cursor: default;
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.pipeline-node:hover {
  transform: scale(1.15);
}

.node-circle {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-family: var(--font-mono);
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
  background: #fff;
  border: 2.5px solid #dce1e8;
  color: #6b7c93;
}

.node-circle :deep(svg) {
  opacity: 0.65;
  transition: opacity 0.35s ease;
}

.node-label {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  white-space: nowrap;
  transition: all 0.3s ease;
  text-align: center;
  color: #4a5568;
}

/* ---- Connector ---- */
.pipeline-connector {
  width: 60px;
  height: 3px;
  background: #dce1e8;
  border-radius: 2px;
  flex-shrink: 0;
  margin-top: 16px;
  transition: all 0.4s ease;
}

.pipeline-connector.active {
  animation: connectorGlow 1.8s ease-in-out infinite;
}

.pipeline-connector.filled {
  background: #2c3e6b;
}

@keyframes connectorGlow {
  0%, 100% { opacity: 0.7; }
  50%      { opacity: 1; }
}

/* ---- Active State ---- */
.pipeline-node.active:nth-child(1) .node-circle {
  background: #ecfeff; border-color: #06b6d4; color: #06b6d4;
  box-shadow: 0 0 0 5px rgba(6,182,212,0.12), 0 0 20px rgba(6,182,212,0.2);
}
.pipeline-node.active:nth-child(2) .node-circle {
  background: #f5f3ff; border-color: #8b5cf6; color: #8b5cf6;
  box-shadow: 0 0 0 5px rgba(139,92,246,0.12), 0 0 20px rgba(139,92,246,0.2);
}
.pipeline-node.active:nth-child(3) .node-circle {
  background: #fffdf5; border-color: #f59e0b; color: #f59e0b;
  box-shadow: 0 0 0 5px rgba(245,158,11,0.12), 0 0 20px rgba(245,158,11,0.2);
}
.pipeline-node.active:nth-child(4) .node-circle {
  background: #f0fdfa; border-color: #14b8a6; color: #14b8a6;
  box-shadow: 0 0 0 5px rgba(20,184,166,0.12), 0 0 20px rgba(20,184,166,0.2);
}
.pipeline-node.active:nth-child(5) .node-circle {
  background: #ecfdf5; border-color: #10b981; color: #10b981;
  box-shadow: 0 0 0 5px rgba(16,185,129,0.12), 0 0 20px rgba(16,185,129,0.2);
}

.pipeline-node.active .node-circle {
  transform: scale(1.12);
  animation: nodePulse 2s ease-in-out infinite;
}

.pipeline-node.active .node-circle :deep(svg) { opacity: 1; }
.pipeline-node.active .node-label { font-weight: 800; }

@keyframes nodePulse {
  0%, 100% { transform: scale(1.12); }
  50%      { transform: scale(1.18); }
}

/* ---- Done State ---- */
.pipeline-node.done:nth-child(1) .node-circle {
  background: #06b6d4; border-color: #06b6d4; color: #fff;
  box-shadow: 0 2px 10px rgba(6,182,212,0.3);
}
.pipeline-node.done:nth-child(2) .node-circle {
  background: #8b5cf6; border-color: #8b5cf6; color: #fff;
  box-shadow: 0 2px 10px rgba(139,92,246,0.3);
}
.pipeline-node.done:nth-child(3) .node-circle {
  background: #f59e0b; border-color: #f59e0b; color: #fff;
  box-shadow: 0 2px 10px rgba(245,158,11,0.3);
}
.pipeline-node.done:nth-child(4) .node-circle {
  background: #14b8a6; border-color: #14b8a6; color: #fff;
  box-shadow: 0 2px 10px rgba(20,184,166,0.3);
}
.pipeline-node.done:nth-child(5) .node-circle {
  background: #10b981; border-color: #10b981; color: #fff;
  box-shadow: 0 2px 10px rgba(16,185,129,0.3);
}

.pipeline-node.done .node-circle :deep(svg) { opacity: 1; color: #fff; }
.pipeline-node.done .node-label { opacity: 0.7; }

/* ---- Status text ---- */
.pipeline-status {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 8px;
  padding-top: 7px;
  border-top: 1px solid var(--border-light);
}

.status-text {
  font-size: 0.78rem;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  animation: fadeIn 0.3s ease-out;
  color: #4a5568;
}

.status-text.idle {
  color: #718096;
  opacity: 1;
}

.status-icon {
  font-size: 0.9rem;
}

.status-text.active-step {
  color: #2c3e6b;
}

.pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #2c3e6b;
  animation: dotBlink 1.2s ease-in-out infinite;
  flex-shrink: 0;
}

@keyframes dotBlink {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%      { opacity: 0.3; transform: scale(0.65); }
}

.status-text.done {
  color: var(--success);
  font-weight: 600;
}

.done-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 19px;
  height: 19px;
  border-radius: 50%;
  background: var(--success);
  color: #ffffff;
  font-size: 0.65rem;
  font-weight: 700;
  flex-shrink: 0;
}

/* ---- Responsive ---- */
@media (max-width: 900px) {
  .pipeline-bar { padding: 0.9rem 0.75rem 0.8rem; }
  .pipeline-connector { width: 36px; margin-top: 15px; }
  .node-circle { width: 32px; height: 32px; }
  .node-label { font-size: 0.6rem; }
}

@media (max-width: 640px) {
  .pipeline-bar { margin: 0 0.75rem; padding: 0.75rem 0.4rem 0.65rem; }
  .pipeline-connector { width: 20px; margin-top: 12px; height: 2px; }
  .node-circle { width: 26px; height: 26px; }
  .node-label { font-size: 0.55rem; }
}

/* ===== Multi-Model Comparison Styles ===== */
.comparison-results {
  margin-top: 1rem;
  border-top: 2px solid var(--border);
  padding-top: 1rem;
  animation: fadeIn 0.3s ease-out;
}

.comparison-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.comparison-header h3 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.btn-close-comparison {
  background: transparent;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.btn-close-comparison:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.comparison-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
}

.comparison-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  background: white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease;
}

.comparison-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.comparison-card.card-success {
  border-left: 4px solid #10b981;
}

.comparison-card.card-error {
  border-left: 4px solid #ef4444;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, #f8fafc, #f1f5f9);
  border-bottom: 1px solid var(--border);
}

.model-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.model-name {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-primary);
}

.model-key {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.model-stats {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.25rem;
}

.latency-badge {
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
  background: #e0e7ff;
  color: #4f46e5;
  border-radius: 4px;
  font-weight: 500;
}

.status-badge {
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-weight: 500;
}

.status-badge.success {
  background: #d1fae5;
  color: #065f46;
}

.status-badge.error {
  background: #fee2e2;
  color: #991b1b;
}

.card-content {
  padding: 1rem;
  max-height: 400px;
  overflow-y: auto;
  font-size: 0.85rem;
  line-height: 1.6;
}

.card-error-content {
  padding: 1rem;
  background: #fef2f2;
}

.card-error-content pre {
  background: #fee2e2;
  padding: 0.75rem;
  border-radius: 4px;
  font-size: 0.75rem;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
  color: #991b1b;
  margin-top: 0.5rem;
}

@media (max-width: 768px) {
  .comparison-grid {
    grid-template-columns: 1fr;
  }
  
  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
  
  .model-stats {
    flex-direction: row;
    align-items: center;
  }
}
</style>
