import { reactive } from 'vue'
import { analysisApi } from '../api'

// 全局批次状态：默认展示最新一次导入的评估结果，所有页面共享
const state = reactive({
  batches: [],
  currentBatchId: null,
  loaded: false,
  error: null,
  // 数据版本号：每次批次列表变化或切换批次时自增，供各页面 watch 触发重新加载
  version: 0
})

/**
 * 加载历次评估批次列表，默认选中最新一次（后端按 import_time 倒序返回）
 * 失败时不抛错、不阻塞，仅标记 error 状态
 */
async function loadBatches() {
  state.error = null
  try {
    const list = await analysisApi.getBatches()
    const arr = Array.isArray(list) ? list : []
    // 按 import_time 倒序排列（最新在前），确保 batches[0] 始终是最新导入
    state.batches = arr.sort((a, b) => new Date(b.import_time || 0) - new Date(a.import_time || 0))
    // 仅在用户未手动选择过时才自动选中最新
    if (!state.currentBatchId && state.batches.length) {
      state.currentBatchId = state.batches[0].id
    }
  } catch (e) {
    // 批次接口不可用时静默降级，不影响数据加载
    state.batches = []
    state.error = e.response?.data?.detail || String(e)
    console.warn('[batch store] 历次评估加载不可用（将显示全部数据）', e.message || e)
  }
  state.loaded = true
  // 通知各页面重新加载（导入新数据、重新进入页面都会触发）
  state.version++
}

/** 选中指定批次（通常为最新一次导入），并通知页面刷新 */
function setCurrentBatch(id) {
  state.currentBatchId = id
  state.version++
}

/** 取最新一次导入的批次（按 import_time 倒序，取第一个；兼容排序异常） */
function latestBatchId() {
  if (!state.batches.length) return null
  const sorted = [...state.batches].sort(
    (a, b) => new Date(b.import_time || 0) - new Date(a.import_time || 0)
  )
  return sorted[0].id
}

/** 清除当前选择（用于重新自动选中最新） */
function clearCurrentBatch() {
  state.currentBatchId = null
}

export function useBatchStore() {
  return { state, loadBatches, setCurrentBatch, clearCurrentBatch, latestBatchId }
}
