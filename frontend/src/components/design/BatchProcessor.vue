<script setup lang="ts">
import { ref } from 'vue'
import { useApi } from '@/composables/useApi'
import SvgIcon from '@/components/common/SvgIcon.vue'

const api = useApi()

// Props
const props = defineProps<{
  availableModels: Array<{ id: string; label: string; model: string }>
}>()

// State
const showPanel = ref(false)
const batchInput = ref('')
const batchProcessing = ref(false)
const batchProgress = ref(0)
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
const selectedModel = ref('deepseek')
const analysisType = ref<'quick' | 'comprehensive'>('comprehensive')
const concurrentLimit = ref(5)

function parseBatchInput(): Array<{ sequence_id: string; sequence: string }> {
  const lines = batchInput.value.split('\n').filter(l => l.trim())
  const sequences: Array<{ sequence_id: string; sequence: string }> = []
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (line.startsWith('>')) {
      // FASTA format
      const header = line.substring(1).trim()
      const seq = lines[i + 1]?.trim() || ''
      if (seq) {
        sequences.push({
          sequence_id: header || `seq_${sequences.length + 1}`,
          sequence: seq,
        })
        i++ // Skip next line (sequence)
      }
    } else if (line.includes(',') || line.includes('\t')) {
      // CSV format: id,sequence
      const parts = line.split(/[,\t]/).map(p => p.trim())
      if (parts.length >= 2) {
        sequences.push({
          sequence_id: parts[0],
          sequence: parts[1],
        })
      }
    } else {
      // Plain sequence (one per line)
      sequences.push({
        sequence_id: `seq_${sequences.length + 1}`,
        sequence: line,
      })
    }
  }
  
  return sequences
}

async function startBatchProcessing() {
  const sequences = parseBatchInput()
  if (sequences.length === 0) {
    alert('请输入至少一条AFP序列')
    return
  }

  if (sequences.length > 500) {
    alert('最多支持500条序列，请分批处理')
    return
  }

  batchProcessing.value = true
  batchProgress.value = 0
  batchResults.value = []
  batchId.value = null

  try {
    const result = await api.batchProcessSequences(
      sequences,
      selectedModel.value,
      analysisType.value,
      concurrentLimit.value
    )

    batchId.value = result.batch_id
    batchResults.value = result.results
    batchProgress.value = 100

    alert(`✅ 批量处理完成！\n\n总序列数: ${result.total_sequences}\n成功: ${result.successful}\n失败: ${result.failed}`)
  } catch (error: any) {
    alert(`❌ 批量处理失败: ${error.message}`)
  } finally {
    batchProcessing.value = false
  }
}

function exportBatchResults(format: 'csv' | 'json' = 'csv') {
  if (!batchId.value) return
  api.exportBatchResults(batchId.value, format)
}

function clearAll() {
  batchInput.value = ''
  batchResults.value = []
  batchId.value = null
  batchProgress.value = 0
}

function loadExample() {
  batchInput.value = `>AFP_001
DTASDAAAAAALTAANAAAAAKLTADNAAAAAAATAR
>AFP_002
CEETNCPISACTESGACPTQAKTFSARNDYSERIDPRHLC
>AFP_003
AVLLPAGELGAATCTANPACETWCPVTT`
}
</script>

<template>
  <div class="batch-processor">
    <!-- Toggle Button -->
    <button 
      class="btn-toggle-batch" 
      @click="showPanel = !showPanel"
      :class="{ active: showPanel }"
    >
      <SvgIcon name="list" :size="16" />
      {{ showPanel ? '关闭' : '批量处理' }}
    </button>

    <!-- Batch Panel -->
    <div v-if="showPanel" class="batch-panel card">
      <div class="batch-header">
        <h3>🧬 AFP批量序列分析</h3>
        <span class="batch-badge">{{ parseBatchInput().length }} 条序列</span>
      </div>

      <!-- Configuration -->
      <div class="batch-config">
        <div class="config-row">
          <label>模型选择:</label>
          <select v-model="selectedModel" :disabled="batchProcessing">
            <option v-for="m in availableModels" :key="m.id" :value="m.id">
              {{ m.label }} ({{ m.model }})
            </option>
          </select>
        </div>
        <div class="config-row">
          <label>分析类型:</label>
          <select v-model="analysisType" :disabled="batchProcessing">
            <option value="quick">快速分析 (基础特征)</option>
            <option value="comprehensive">全面分析 (详细报告)</option>
          </select>
        </div>
        <div class="config-row">
          <label>并发数:</label>
          <input 
            type="number" 
            v-model.number="concurrentLimit" 
            min="1" 
            max="20"
            :disabled="batchProcessing"
          />
        </div>
      </div>

      <!-- Input Area -->
      <div class="batch-input-section">
        <div class="input-actions">
          <button class="btn-example" @click="loadExample" :disabled="batchProcessing">
            📋 加载示例
          </button>
          <button class="btn-clear" @click="clearAll" :disabled="batchProcessing">
            🗑️ 清空
          </button>
        </div>
        <textarea
          v-model="batchInput"
          placeholder="粘贴AFP序列（支持FASTA/CSV/纯文本格式）...

示例格式:
>AFP_001
DTASDAAAAAALTAANAAAAAKLTADNAAAAAAATAR
>AFP_002
CEETNCPISACTESGACPTQAKTFSARNDYSERIDPRHLC

或:
AFP_001,DTASDAAAAAALTAANAAAAAKLTADNAAAAAAATAR
AFP_002,CEETNCPISACTESGACPTQAKTFSARNDYSERIDPRHLC"
          rows="10"
          class="batch-textarea"
          :disabled="batchProcessing"
        ></textarea>
      </div>

      <!-- Progress Bar -->
      <div v-if="batchProcessing || batchProgress > 0" class="progress-section">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: batchProgress + '%' }"></div>
        </div>
        <div class="progress-text">
          进度: {{ batchProgress }}%
          <span v-if="batchProcessing">(正在处理中...)</span>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="batch-actions">
        <button 
          class="btn-start-batch" 
          @click="startBatchProcessing"
          :disabled="batchProcessing || !batchInput.trim()"
        >
          <SvgIcon name="play" :size="14" />
          {{ batchProcessing ? '处理中...' : '开始批量分析' }}
        </button>
        
        <button 
          v-if="batchId && batchProgress === 100"
          class="btn-export"
          @click="exportBatchResults('csv')"
        >
          📊 导出CSV
        </button>
        
        <button 
          v-if="batchId && batchProgress === 100"
          class="btn-export"
          @click="exportBatchResults('json')"
        >
          📄 导出JSON
        </button>
      </div>

      <!-- Results Preview -->
      <div v-if="batchResults.length > 0" class="results-preview">
        <h4>结果预览 (前3条)</h4>
        <div 
          v-for="(result, idx) in batchResults.slice(0, 3)" 
          :key="idx"
          class="result-item"
          :class="{ 'result-error': !result.success }"
        >
          <div class="result-header">
            <strong>{{ result.sequence_id }}</strong>
            <span class="result-status">
              {{ result.success ? '✅' : '❌' }}
              {{ result.processing_time_ms ? `${result.processing_time_ms}ms` : '' }}
            </span>
          </div>
          <div class="result-sequence">{{ result.sequence.substring(0, 50) }}...</div>
          <div v-if="result.success" class="result-analysis">
            {{ result.analysis.substring(0, 150) }}...
          </div>
          <div v-else class="result-error-msg">
            {{ result.error_message }}
          </div>
        </div>
        <div v-if="batchResults.length > 3" class="more-results">
          ... 还有 {{ batchResults.length - 3 }} 条结果，请导出查看完整数据
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.batch-processor {
  margin-bottom: 1rem;
}

.btn-toggle-batch {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-toggle-batch:hover {
  background: linear-gradient(135deg, #059669, #047857);
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
  transform: translateY(-1px);
}

.batch-panel {
  margin-top: 1rem;
  padding: 1.5rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.batch-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.batch-header h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.batch-badge {
  background: #dbeafe;
  color: #1e40af;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.batch-config {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.config-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.config-row label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.config-row select,
.config-row input {
  padding: 0.4rem 0.6rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.8rem;
}

.config-row input {
  width: 60px;
}

.batch-input-section {
  margin-bottom: 1rem;
}

.input-actions {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.btn-example,
.btn-clear {
  padding: 0.3rem 0.8rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  background: white;
  transition: all 0.2s ease;
}

.btn-example:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
}

.btn-clear:hover {
  background: #fee2e2;
  border-color: #ef4444;
  color: #dc2626;
}

.batch-textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  resize: vertical;
  transition: border-color 0.2s ease;
}

.batch-textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.progress-section {
  margin-bottom: 1rem;
}

.progress-bar {
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #059669);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.8rem;
  color: var(--text-secondary);
  text-align: center;
}

.batch-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.btn-start-batch {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.6rem 1.2rem;
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-start-batch:hover:not(:disabled) {
  background: linear-gradient(135deg, #059669, #047857);
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
  transform: translateY(-1px);
}

.btn-start-batch:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-export {
  padding: 0.6rem 1rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-export:hover {
  background: #2563eb;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.results-preview {
  border-top: 1px solid #e5e7eb;
  padding-top: 1rem;
}

.results-preview h4 {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.75rem;
}

.result-item {
  padding: 0.75rem;
  background: #f9fafb;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  border-left: 3px solid #10b981;
}

.result-item.result-error {
  border-left-color: #ef4444;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.result-header strong {
  font-size: 0.85rem;
  color: var(--text-primary);
}

.result-status {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.result-sequence {
  font-family: 'Courier New', monospace;
  font-size: 0.8rem;
  color: #6b7280;
  margin-bottom: 0.5rem;
}

.result-analysis {
  font-size: 0.8rem;
  color: var(--text-primary);
  line-height: 1.5;
}

.result-error-msg {
  font-size: 0.8rem;
  color: #dc2626;
}

.more-results {
  text-align: center;
  font-size: 0.8rem;
  color: var(--text-secondary);
  padding: 0.5rem;
}
</style>
