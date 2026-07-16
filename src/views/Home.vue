<template>
  <div class="home-container">
    <div class="section-header">
      <div class="header-left">
        <h2>📊 评估结果</h2>
        <p class="header-desc">基于 RECIST 1.1 标准的病灶评估数据汇总与对比分析</p>
      </div>
      <div class="history-wrap">
        <el-popover
          :width="380"
          trigger="hover"
          placement="bottom-end"
          popper-class="history-popover"
          :show-arrow="false"
        >
          <template #reference>
            <el-button class="history-btn">
              <span class="history-btn-label">{{ currentBatchLabel || '历次评估' }}</span>
              <el-icon class="caret"><ArrowDown /></el-icon>
            </el-button>
          </template>
          <div class="history-panel">
            <div class="history-panel-header">
              <span class="history-title">历史记录</span>
              <el-button v-if="displayBatches.length" link type="danger" size="small" :icon="Delete" @click="clearAll">一键清空</el-button>
            </div>
            <div v-if="displayBatches.length === 0" class="history-empty">暂无历史记录</div>
            <div v-else class="history-list">
              <div v-for="b in displayBatches" :key="b.id" class="history-item" :class="{ active: b.id === state.currentBatchId }" @click="selectBatch(b)">
                <el-icon v-if="b.id === state.currentBatchId" class="item-check"><Check /></el-icon>
                <span v-else class="item-radio" />
                <div class="item-main">
                  <div class="item-time">{{ formatTime(b.import_time) }}</div>
                  <div class="item-name" :title="b.filename">{{ b.filename }}</div>
                </div>
                <span class="item-count">{{ b.total_assessments }}条</span>
                <el-button class="item-del" link type="danger" :icon="Delete" size="small" title="删除该记录" @click.stop="deleteBatch(b)" />
              </div>
            </div>
          </div>
        </el-popover>
      </div>
    </div>

    <div v-if="loading" class="loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <div v-else-if="isEmpty" class="empty-state">
      <el-empty :description="emptyText" />
      <div v-if="state.batches.length === 0" class="empty-action">
        <el-button type="primary" @click="goUpload">去导入数据</el-button>
      </div>
    </div>

    <template v-else>
      <div class="stats-row">
        <div class="stat-box clickable" @click="goToStatDetail('match')">
          <div class="stat-icon-wrap">
            <span class="stat-icon">✅</span>
          </div>
          <div class="stat-content">
            <div class="stat-value match">{{ statistics?.match_count || 0 }}</div>
            <div class="stat-label">自动 ↔ 人工一致</div>
          </div>
        </div>
        <div class="stat-box clickable" @click="goToStatDetail('mismatch')">
          <div class="stat-icon-wrap">
            <span class="stat-icon">❌</span>
          </div>
          <div class="stat-content">
            <div class="stat-value mismatch">{{ statistics?.mismatch_count || 0 }}</div>
            <div class="stat-label">不一致</div>
          </div>
        </div>
        <div class="stat-box clickable" @click="goToStatDetail('no_human')">
          <div class="stat-icon-wrap">
            <span class="stat-icon">ℹ️</span>
          </div>
          <div class="stat-content">
            <div class="stat-value no-human">{{ statistics?.no_human_count || 0 }}</div>
            <div class="stat-label">无人工数据</div>
          </div>
        </div>
        <div class="stat-box clickable highlight" @click="goToStatDetail('rate')">
          <div class="stat-icon-wrap">
            <span class="stat-icon">📊</span>
          </div>
          <div class="stat-content">
            <div class="stat-value rate" :class="rateClass">{{ matchRateText }}</div>
            <div class="stat-label">一致率</div>
          </div>
        </div>
      </div>

      <div class="tabs-bar">
        <div class="tabs-left">
          <div v-for="tab in tabs" :key="tab.key" class="tab-item" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">
            <span class="tab-icon">{{ tab.icon }}</span>
            <span>{{ tab.label }}</span>
          </div>
        </div>
        <div class="tabs-right">
          <el-select v-model="searchQuery" placeholder="输入或选择受试者编号搜索" filterable clearable size="small" style="width: 220px" @clear="searchQuery = ''">
            <el-option v-for="opt in subjectOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <el-select v-model="filterStatus" placeholder="筛选" clearable size="small" style="width: 140px">
            <el-option label="全部" value="" />
            <el-option label="一致" value="match" />
            <el-option label="不一致" value="mismatch" />
            <el-option label="无人工数据" value="no_human" />
          </el-select>
          <ExportMenu :rows="exportRows" :type="exportType" :filename="exportFilename" :title="exportTitle" />
        </div>
      </div>

      <div v-show="activeTab === 'overview'" class="tab-panel">
        <div v-if="pagedSubjects.length === 0" class="empty">
          <el-empty description="暂无评估数据" />
        </div>
        <div v-else class="subject-grid">
          <div v-for="row in pagedSubjects" :key="row.subject_db_id" class="subject-card" :class="getCardClass(row)" @click="goToSubject(row.subject_db_id)">
            <div class="card-header">
              <span class="subject-id">{{ row.subject_id }}</span>
              <span class="card-tag" :class="getCardClass(row)">{{ getCardTag(row) }}</span>
            </div>
            <div class="card-body">
              <div v-for="tp in row.timepoints" :key="tp.id" class="compare-row">
                <div class="timepoint-label">{{ tp.timepoint || `周期${tp.cycle_number}` }}</div>
                <div class="compare-cell">
                  <div class="labeled-badge">
                    <span class="source-label">程序</span>
                    <span class="badge auto" :class="badgeClass(tp.overall_status)">{{ shortStatus(tp.overall_status) }}</span>
                  </div>
                  <span class="arrow">↔</span>
                  <div class="labeled-badge" v-if="tp.manual_overall_status">
                    <span class="source-label">人工</span>
                    <span class="badge human" :class="badgeClass(tp.manual_overall_status)">{{ shortStatus(tp.manual_overall_status) }}</span>
                  </div>
                  <span v-if="tp.overall_match === true" class="match-icon yes">✓</span>
                  <span v-else-if="tp.overall_match === false" class="match-icon no">✗</span>
                </div>
              </div>
              <div v-if="!row.timepoints.length" class="no-assessment-hint">尚未添加评估/病灶数据</div>
            </div>
            <div class="card-footer">
              <span class="card-hint">点击查看详情</span>
              <el-icon class="card-arrow"><ArrowRight /></el-icon>
            </div>
          </div>
        </div>
        <el-pagination v-if="filteredSubjectRows.length > pageSizeOverview" class="pager" background layout="total, sizes, prev, pager, next" :total="filteredSubjectRows.length" :page-size="pageSizeOverview" :page-sizes="[8, 12, 16, 24]" v-model:current-page="pageOverview" @size-change="(s) => { pageSizeOverview = s; pageOverview = 1 }" />
      </div>

      <div v-show="activeTab === 'detail'" class="tab-panel">
        <el-table :data="pagedDetail" border stripe size="small" style="width: 100%">
          <el-table-column prop="subject_id" label="受试者编号" width="110" align="center" />
          <el-table-column prop="timepoint" label="时间点" width="150" align="center" />
          <el-table-column width="170" align="center">
            <template #header>
              <div class="multi-header">靶病灶评估</div>
              <div class="multi-header-sub">程序 ↔ 人工</div>
            </template>
            <template #default="scope">
              <div class="compare-pair">
                <div class="labeled-badge">
                  <span class="source-label">程序</span>
                  <span class="badge auto" :class="badgeClass(scope.row.target_status)">{{ shortStatus(scope.row.target_status) }}</span>
                </div>
                <span class="arrow">↔</span>
                <div class="labeled-badge" v-if="scope.row.manual_target_status">
                  <span class="source-label">人工</span>
                  <span class="badge human" :class="badgeClass(scope.row.manual_target_status)">{{ shortStatus(scope.row.manual_target_status) }}</span>
                </div>
                <span v-else class="no-data">-</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column width="180" align="center">
            <template #header>
              <div class="multi-header">非靶病灶评估</div>
              <div class="multi-header-sub">程序 ↔ 人工</div>
            </template>
            <template #default="scope">
              <div class="compare-pair">
                <div class="labeled-badge">
                  <span class="source-label">程序</span>
                  <span class="badge auto" :class="badgeClass(scope.row.non_target_status)">{{ shortStatus(scope.row.non_target_status) }}</span>
                </div>
                <span class="arrow">↔</span>
                <div class="labeled-badge" v-if="scope.row.manual_non_target_status">
                  <span class="source-label">人工</span>
                  <span class="badge human" :class="badgeClass(scope.row.manual_non_target_status)">{{ shortStatus(scope.row.manual_non_target_status) }}</span>
                </div>
                <span v-else class="no-data">-</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column width="140" align="center">
            <template #header>
              <div class="multi-header">新病灶</div>
              <div class="multi-header-sub">程序 ↔ 人工</div>
            </template>
            <template #default="scope">
              <div class="compare-pair">
                <div class="labeled-badge">
                  <span class="source-label">程序</span>
                  <span>{{ scope.row.has_new_lesion ? '有' : '无' }}</span>
                </div>
                <span class="arrow">↔</span>
                <div class="labeled-badge" v-if="scope.row.has_manual_data">
                  <span class="source-label">人工</span>
                  <span>{{ scope.row.manual_has_new_lesion ? '有' : '无' }}</span>
                </div>
                <span v-else class="no-data">-</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column width="170" align="center">
            <template #header>
              <div class="multi-header">总体疗效评估</div>
              <div class="multi-header-sub">程序 ↔ 人工</div>
            </template>
            <template #default="scope">
              <div class="compare-pair">
                <div class="labeled-badge">
                  <span class="source-label">程序</span>
                  <span class="badge auto" :class="badgeClass(scope.row.overall_status)">{{ shortStatus(scope.row.overall_status) }}</span>
                </div>
                <span class="arrow">↔</span>
                <div class="labeled-badge" v-if="scope.row.manual_overall_status">
                  <span class="source-label">人工</span>
                  <span class="badge human" :class="badgeClass(scope.row.manual_overall_status)">{{ shortStatus(scope.row.manual_overall_status) }}</span>
                </div>
                <span v-else class="no-data">-</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="overall_reason" label="程序判定理由" min-width="300">
            <template #default="scope">
              <div class="reason-text">{{ scope.row.overall_reason }}</div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" align="center" fixed="right">
            <template #default="scope">
              <el-button type="primary" size="small" @click="goToSubject(scope.row.subject_db_id)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination v-if="filteredTable.length > pageSizeDetail" class="pager" background layout="total, sizes, prev, pager, next" :total="filteredTable.length" :page-size="pageSizeDetail" :page-sizes="[10, 20, 50, 100]" v-model:current-page="pageDetail" @size-change="(s) => { pageSizeDetail = s; pageDetail = 1 }" />
      </div>

      <div v-show="activeTab === 'mismatch'" class="tab-panel">
        <div v-if="filteredMismatch.length === 0" class="empty">
          <el-empty description="暂无不一致记录" />
        </div>
        <div v-else>
          <el-table :data="pagedMismatch" border stripe size="small" style="width: 100%">
            <el-table-column prop="subject_id" label="受试者编号" width="110" align="center" />
            <el-table-column prop="timepoint" label="时间点" width="150" align="center" />
            <el-table-column width="170" align="center">
              <template #header>
                <div class="multi-header">靶病灶评估</div>
                <div class="multi-header-sub">程序 ↔ 人工</div>
              </template>
              <template #default="scope">
                <div class="compare-pair">
                  <div class="labeled-badge">
                    <span class="source-label">程序</span>
                    <span class="badge auto" :class="badgeClass(scope.row.target_status)">{{ shortStatus(scope.row.target_status) }}</span>
                  </div>
                  <span class="arrow">↔</span>
                  <div class="labeled-badge">
                    <span class="source-label">人工</span>
                    <span class="badge human" :class="badgeClass(scope.row.manual_target_status)">{{ shortStatus(scope.row.manual_target_status) }}</span>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column width="180" align="center">
              <template #header>
                <div class="multi-header">非靶病灶评估</div>
                <div class="multi-header-sub">程序 ↔ 人工</div>
              </template>
              <template #default="scope">
                <div class="compare-pair">
                  <div class="labeled-badge">
                    <span class="source-label">程序</span>
                    <span class="badge auto" :class="badgeClass(scope.row.non_target_status)">{{ shortStatus(scope.row.non_target_status) }}</span>
                  </div>
                  <span class="arrow">↔</span>
                  <div class="labeled-badge">
                    <span class="source-label">人工</span>
                    <span class="badge human" :class="badgeClass(scope.row.manual_non_target_status)">{{ shortStatus(scope.row.manual_non_target_status) }}</span>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column width="170" align="center">
              <template #header>
                <div class="multi-header">总体疗效评估</div>
                <div class="multi-header-sub">程序 ↔ 人工</div>
              </template>
              <template #default="scope">
                <div class="compare-pair">
                  <div class="labeled-badge">
                    <span class="source-label">程序</span>
                    <span class="badge auto" :class="badgeClass(scope.row.overall_status)">{{ shortStatus(scope.row.overall_status) }}</span>
                  </div>
                  <span class="arrow">↔</span>
                  <div class="labeled-badge">
                    <span class="source-label">人工</span>
                    <span class="badge human" :class="badgeClass(scope.row.manual_overall_status)">{{ shortStatus(scope.row.manual_overall_status) }}</span>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="overall_reason" label="程序判定理由" min-width="300">
              <template #default="scope">
                <div class="reason-text">{{ scope.row.overall_reason }}</div>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" align="center" fixed="right">
              <template #default="scope">
                <el-button type="primary" size="small" @click="goToSubject(scope.row.subject_db_id)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination v-if="filteredMismatch.length > pageSizeMismatch" class="pager" background layout="total, sizes, prev, pager, next" :total="filteredMismatch.length" :page-size="pageSizeMismatch" :page-sizes="[10, 20, 50, 100]" v-model:current-page="pageMismatch" @size-change="(s) => { pageSizeMismatch = s; pageMismatch = 1 }" />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, Delete, Check, ArrowRight, Loading } from '@element-plus/icons-vue'
import { analysisApi } from '../api'
import { getStatusText } from '../utils/recist'
import { useBatchStore } from '../store/batch'
import ExportMenu from '../components/ExportMenu.vue'

const router = useRouter()
const loading = ref(false)
const statistics = ref(null)
const activeTab = ref('overview')
const searchQuery = ref('')
const filterStatus = ref('')
const { state, loadBatches, setCurrentBatch } = useBatchStore()

const pageOverview = ref(1)
const pageSizeOverview = ref(12)
const pageDetail = ref(1)
const pageSizeDetail = ref(10)
const pageMismatch = ref(1)
const pageSizeMismatch = ref(10)

const tabs = [
  { key: 'overview', label: '受试者概览', icon: '👥' },
  { key: 'detail', label: '详细数据', icon: '📋' },
  { key: 'mismatch', label: '不一致汇总', icon: '⚠️' }
]

const parseLocal = (t) => {
  if (!t) return null
  const s = String(t).replace('T', ' ').replace('Z', '')
  const m = s.match(/(\d{4})-(\d{1,2})-(\d{1,2})[ ](\d{1,2}):(\d{1,2})(?::(\d{1,2}))?/)
  if (!m) {
    const d = new Date(t)
    return isNaN(d.getTime()) ? null : d
  }
  return new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0))
}

const formatBatchLabel = (b) => {
  if (!b.import_time) return b.filename
  const d = parseLocal(b.import_time)
  if (!d) return b.filename
  const pad = (n) => String(n).padStart(2, '0')
  const dateStr = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  return `${dateStr} | ${b.filename}`
}

const formatTime = (t) => {
  if (!t) return ''
  const d = parseLocal(t)
  if (!d) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

const currentBatch = computed(() => state.batches.find(b => b.id === state.currentBatchId) || null)
const currentBatchLabel = computed(() => currentBatch.value ? formatBatchLabel(currentBatch.value) : '')
const displayBatches = computed(() => [...state.batches].filter(b => !b.filename.includes('（系统）') && !b.filename.includes('(系统)')).sort((a, b) => new Date(b.import_time || 0) - new Date(a.import_time || 0)))

const selectBatch = (b) => {
  setCurrentBatch(b.id)
  loadData()
}

const deleteBatch = async (b) => {
  try {
    await ElMessageBox.confirm(`确定删除「${b.filename}」这条导入记录吗？\n删除后将同时移除该批次下的全部评估数据，且不可恢复。`, '删除历史记录', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' })
  } catch { return }
  try {
    await analysisApi.deleteBatch(b.id)
    ElMessage.success('已删除该历史记录')
    await refreshAfterDelete(b.id)
  } catch (e) {
    console.error(e)
    ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  }
}

const clearAll = async () => {
  try {
    await ElMessageBox.confirm('确定清空全部历史记录吗？\n此操作将删除所有导入批次及其评估数据，且不可恢复！', '一键清空', { type: 'warning', confirmButtonText: '清空', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' })
  } catch { return }
  try {
    await analysisApi.clearBatches()
    ElMessage.success('已清空全部历史记录')
    await refreshAfterDelete(null)
  } catch (e) {
    console.error(e)
    ElMessage.error('清空失败：' + (e.response?.data?.detail || e.message))
  }
}

const refreshAfterDelete = async (deletedId) => {
  const prev = state.currentBatchId
  await loadBatches()
  if ((deletedId !== null && prev === deletedId) || !state.batches.find(b => b.id === prev)) {
    setCurrentBatch(state.batches.length ? state.batches[0].id : null)
  }
  loadData()
}

const loadData = async () => {
  loading.value = true
  try {
    statistics.value = await analysisApi.getStatistics(state.currentBatchId || undefined)
  } catch (e) {
    console.error('[Home] 统计数据加载失败', e)
    statistics.value = null
    if (e.response?.status !== 404 && e.response?.status !== 422) {
      ElMessage.warning('加载数据失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}

const isEmpty = computed(() => !loading.value && (!statistics.value || (statistics.value.total_assessments === 0 && statistics.value.total_subjects === 0)))
const emptyText = computed(() => {
  if (state.batches.length > 0) return '该次评估暂无数据，请选择其他历次评估或导入数据'
  return '请导入数据后查看评估结果'
})
const goUpload = () => router.push('/upload')

watch(() => state.version, () => {
  if (state.currentBatchId || statistics.value) loadData()
})

onMounted(async () => { await loadBatches() })
onActivated(async () => { await loadBatches() })

const assessmentTable = computed(() => statistics.value?.assessment_table || [])
const subjectOptions = computed(() => {
  const map = new Map()
  assessmentTable.value.filter(r => !r.no_assessment).forEach(r => {
    if (r.subject_db_id && !map.has(r.subject_db_id)) {
      map.set(r.subject_db_id, { value: r.subject_id, label: r.subject_id })
    }
  })
  return Array.from(map.values())
})

const filteredTable = computed(() => {
  let rows = assessmentTable.value.filter(r => !r.no_assessment)
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    rows = rows.filter(r => r.subject_id?.toLowerCase().includes(q))
  }
  if (filterStatus.value === 'match') rows = rows.filter(r => r.overall_match === true)
  else if (filterStatus.value === 'mismatch') rows = rows.filter(r => r.overall_match === false)
  else if (filterStatus.value === 'no_human') rows = rows.filter(r => !r.manual_overall_status)
  return rows
})

const filteredMismatch = computed(() => {
  let rows = assessmentTable.value.filter(row => row.overall_match === false)
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    rows = rows.filter(r => r.subject_id?.toLowerCase().includes(q))
  }
  return rows
})

// 共享筛选：按受试者搜索 + 筛选状态（一致/不一致/无人工数据）过滤
// 应用于概览展示、详细数据、导出；无筛选时返回全量
const filterRows = (rows) => {
  let r = rows
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    r = r.filter(row => row.subject_id?.toLowerCase().includes(q))
  }
  if (filterStatus.value === 'match') r = r.filter(row => row.overall_match === true)
  else if (filterStatus.value === 'mismatch') r = r.filter(row => row.overall_match === false)
  else if (filterStatus.value === 'no_human') r = r.filter(row => !row.manual_overall_status)
  return r
}

const filteredSubjectRows = computed(() => {
  // 概览展示同样遵循右侧搜索/筛选；no_assessment（未评估）行在「全部/无人工数据/搜索命中」时保留
  const rows = filterRows(assessmentTable.value)
  const grouped = {}
  rows.forEach(row => {
    const key = row.subject_db_id || row.subject_id
    if (!grouped[key]) {
      grouped[key] = { subject_id: row.subject_id, subject_db_id: row.subject_db_id, subject_name: row.subject_name, timepoints: [], no_assessment: false }
    }
    if (row.no_assessment) {
      grouped[key].no_assessment = true
    } else {
      grouped[key].timepoints.push(row)
    }
  })
  return Object.values(grouped).map(g => {
    if (g.timepoints.length === 0) return { ...g, timepoints: [] }
    g.timepoints.sort((a, b) => (a.cycle_number || 0) - (b.cycle_number || 0))
    return { ...g, timepoints: [g.timepoints[g.timepoints.length - 1]] }
  })
})

const pagedSubjects = computed(() => {
  const start = (pageOverview.value - 1) * pageSizeOverview.value
  return filteredSubjectRows.value.slice(start, start + pageSizeOverview.value)
})
const pagedDetail = computed(() => {
  const start = (pageDetail.value - 1) * pageSizeDetail.value
  return filteredTable.value.slice(start, start + pageSizeDetail.value)
})
const pagedMismatch = computed(() => {
  const start = (pageMismatch.value - 1) * pageSizeMismatch.value
  return filteredMismatch.value.slice(start, start + pageSizeMismatch.value)
})

watch([searchQuery, filterStatus, activeTab], () => {
  pageOverview.value = 1
  pageDetail.value = 1
  pageMismatch.value = 1
})

const matchRateText = computed(() => {
  const rate = statistics.value?.match_rate
  return rate !== undefined ? `${rate}%` : '0.0%'
})

const rateClass = computed(() => {
  const rate = statistics.value?.match_rate || 0
  if (rate >= 90) return 'rate-high'
  if (rate >= 70) return 'rate-medium'
  return 'rate-low'
})

const shortStatus = (s) => {
  const map = {
    '完全缓解': 'CR', '部分缓解': 'PR', '疾病稳定': 'SD', '疾病进展': 'PD',
    '无法评估': 'NE', '非完全缓解/非疾病进展': '非完全缓解(Non-CR)/非疾病进展(Non-PD)', 'Non-CR/Non-PD': '非完全缓解(Non-CR)/非疾病进展(Non-PD)', '不适用': 'N/A'
  }
  return map[getStatusText(s)] || s || 'NE'
}

const badgeClass = (status) => {
  const map = { CR: 'badge-cr', PR: 'badge-pr', SD: 'badge-sd', PD: 'badge-pd', NE: 'badge-ne', 'Non-CR/Non-PD': 'badge-ncnp', '非完全缓解(Non-CR)/非疾病进展(Non-PD)': 'badge-ncnp', '不适用': 'badge-na' }
  return map[status] || 'badge-ne'
}

const getCardClass = (row) => {
  if (row.no_assessment) return 'no-human'
  if (row.timepoints.some(tp => tp.overall_match === false)) return 'mismatch'
  if (row.timepoints.some(tp => tp.overall_match === true)) return 'match'
  return 'no-human'
}

const getCardTag = (row) => {
  if (row.no_assessment) return '未评估'
  if (row.timepoints.some(tp => tp.overall_match === false)) return '不一致'
  if (row.timepoints.some(tp => tp.overall_match === true)) return '一致'
  return '无人工'
}

const goToSubject = (subjectDbId) => {
  router.push({ path: `/report/${subjectDbId}`, query: { batch: state.currentBatchId } })
}

const goToStatDetail = (type) => {
  if (isEmpty.value) return
  router.push({ path: `/stat-detail/${type}`, query: { batch: state.currentBatchId } })
}

// 受试者概览导出：依据当前搜索/筛选状态过滤后按受试者分组（取最新时间点）
// 导出不含「未评估」占位行；无任何搜索与筛选时返回全量
const subjectExportRows = computed(() => {
  const rows = filterRows(assessmentTable.value).filter(r => !r.no_assessment)
  const grouped = {}
  rows.forEach(row => {
    const key = row.subject_db_id || row.subject_id
    if (!grouped[key]) {
      grouped[key] = { subject_id: row.subject_id, subject_db_id: row.subject_db_id, subject_name: row.subject_name, timepoints: [] }
    }
    grouped[key].timepoints.push(row)
  })
  return Object.values(grouped).map(g => {
    if (g.timepoints.length === 0) return { ...g, timepoints: [] }
    g.timepoints.sort((a, b) => (a.cycle_number || 0) - (b.cycle_number || 0))
    return { ...g, timepoints: [g.timepoints[g.timepoints.length - 1]] }
  })
})

const exportRows = computed(() => {
  if (activeTab.value === 'overview') return subjectExportRows.value
  if (activeTab.value === 'mismatch') return filteredMismatch.value
  return filteredTable.value
})

const exportType = computed(() => activeTab.value === 'overview' ? 'subjects' : 'assessments')

// 导出文件名包含的筛选后缀：有搜索/筛选时附加，便于保存后区分
const exportFilterSuffix = computed(() => {
  const parts = []
  if (searchQuery.value) parts.push(`搜索${searchQuery.value}`)
  if (filterStatus.value) {
    const m = { match: '一致', mismatch: '不一致', no_human: '无人工数据' }
    parts.push(`筛选${m[filterStatus.value] || filterStatus.value}`)
  }
  return parts.length ? `_${parts.join('_')}` : ''
})

const exportFilename = computed(() => {
  const map = { overview: '受试者概览', detail: '详细数据', mismatch: '不一致汇总' }
  return (map[activeTab.value] || '评估数据') + exportFilterSuffix.value
})

const exportTitle = computed(() => {
  const map = { overview: '受试者概览', detail: '评估详细数据', mismatch: '不一致汇总' }
  return (map[activeTab.value] || '评估报告') + exportFilterSuffix.value
})
</script>

<style scoped>
.home-container {
  max-width: 1400px;
  margin: 0 auto;
  padding-bottom: 40px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-xl);
  animation: slideIn 0.4s ease;
}

.header-left h2 {
  font-size: 28px;
  color: var(--text-primary);
  margin: 0;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.header-desc {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 8px 0 0;
  line-height: 1.6;
}

.history-wrap {
  display: flex;
  gap: 8px;
  position: relative;
}

.fade-enter-active, .fade-leave-active { transition: opacity var(--transition-normal); }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.history-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 360px;
  height: 40px;
  border-radius: var(--radius-md);
  padding: 0 20px;
  color: var(--primary-color);
  background: white;
  border: 1px solid var(--primary-color);
  transition: all var(--transition-normal);
}

.history-btn:hover {
  background: var(--primary-light);
  border-color: var(--primary-color);
}

.history-btn-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.history-panel {
  display: flex;
  flex-direction: column;
  max-height: 60vh;
}

.history-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 14px;
  margin-bottom: 10px;
  border-bottom: 1px solid var(--border-light);
}

.history-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.history-empty {
  padding: 40px 0;
  text-align: center;
  color: var(--text-placeholder);
  font-size: 13px;
}

.history-list {
  overflow-y: auto;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.history-item:hover { background: var(--bg-color); }
.history-item.active { background: var(--primary-light); }

.item-check { color: var(--primary-color); font-size: 16px; flex-shrink: 0; }
.item-radio { width: 14px; height: 14px; border-radius: 50%; border: 2px solid var(--border-color); flex-shrink: 0; }
.history-item.active .item-radio { border-color: var(--primary-color); background: var(--primary-color); }

.item-main { flex: 1; min-width: 0; }
.item-time { font-size: 12px; color: var(--text-secondary); line-height: 1.4; }
.item-name { font-size: 13px; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-count { font-size: 12px; color: var(--text-secondary); flex-shrink: 0; padding: 2px 8px; background: var(--bg-color); border-radius: 4px; }
.item-del { flex-shrink: 0; font-size: 14px; }

.empty-state { text-align: center; padding: 100px 0; }
.empty-action { margin-top: 24px; }

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.stat-box {
  background: var(--card-bg);
  padding: var(--spacing-xl);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  border: 1px solid var(--border-light);
}

.stat-box::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 4px;
  background: var(--primary-gradient);
}

.stat-box.highlight::before {
  background: var(--primary-gradient);
}

.stat-box.clickable { cursor: pointer; }
.stat-box.clickable:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-xl);
  border-color: var(--border-color);
}

.stat-icon-wrap {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-color);
  border-radius: var(--radius-lg);
  flex-shrink: 0;
  transition: all var(--transition-normal);
}

.stat-box:hover .stat-icon-wrap {
  transform: scale(1.1);
}

.stat-icon { font-size: 28px; }
.stat-content { flex: 1; }
.stat-value { font-size: 32px; font-weight: 700; margin-bottom: 4px; }
.stat-value.total { color: var(--primary-color); }
.stat-value.match { color: var(--success-color); }
.stat-value.mismatch { color: var(--danger-color); }
.stat-value.no-human { color: var(--info-color); }
.stat-value.rate-high { color: var(--success-color); }
.stat-value.rate-medium { color: var(--warning-color); }
.stat-value.rate-low { color: var(--danger-color); }
.stat-label { font-size: 13px; color: var(--text-secondary); }

.tabs-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  border-bottom: 2px solid var(--border-color);
  margin-bottom: var(--spacing-xl);
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.tabs-left { display: flex; gap: var(--spacing-xl); }

.tab-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 0;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 15px;
  border-bottom: 3px solid transparent;
  transition: all var(--transition-normal);
  font-weight: 500;
}

.tab-item:hover { color: var(--primary-color); }
.tab-item.active { color: var(--primary-color); border-bottom-color: var(--primary-color); }

.tab-icon { font-size: 16px; }

.tabs-right {
  display: flex;
  gap: var(--spacing-md);
  padding-bottom: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.tab-panel { margin-bottom: var(--spacing-xl); }

.pager { margin-top: var(--spacing-md); justify-content: flex-end; }

.subject-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-lg);
}

.subject-card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: var(--spacing-xl);
  cursor: pointer;
  transition: all var(--transition-normal);
  border-left: 4px solid var(--border-color);
  position: relative;
  overflow: hidden;
  border: 1px solid var(--border-light);
}

.subject-card::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: var(--primary-gradient);
  opacity: 0;
  transition: opacity var(--transition-normal);
}

.subject-card:hover {
  transform: translateY(-6px);
  box-shadow: var(--shadow-xl);
  border-color: var(--border-color);
}

.subject-card:hover::after {
  opacity: 1;
}

.subject-card.match { border-left-color: var(--success-color); }
.subject-card.mismatch { border-left-color: var(--danger-color); }
.subject-card.no-human { border-left-color: var(--border-color); }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.subject-id { font-weight: 700; color: var(--text-primary); font-size: 16px; }

.card-tag {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 12px;
  color: white;
  font-weight: 600;
}

.card-tag.match { background: var(--success-color); }
.card-tag.mismatch { background: var(--danger-color); }
.card-tag.no-human { background: var(--info-color); }

.card-body {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.compare-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-light);
}

.compare-row:last-child { border-bottom: none; }

.no-assessment-hint {
  padding: 16px 0;
  text-align: center;
  font-size: 13px;
  color: var(--text-placeholder);
  background: var(--bg-color);
  border-radius: 8px;
}

.timepoint-label { font-size: 13px; color: var(--text-secondary); font-weight: 500; }

.compare-cell { display: flex; align-items: center; gap: 6px; }
.compare-pair { display: flex; align-items: center; justify-content: center; gap: 6px; }

.labeled-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.source-label { font-size: 10px; color: var(--text-secondary); line-height: 1; }

.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  color: white;
}

.badge-cr { background: var(--success-color); }
.badge-pr { background: var(--primary-color); }
.badge-sd { background: var(--warning-color); }
.badge-pd { background: #f5f7fa; color: var(--danger-color); border: 1px solid var(--danger-color); }
.badge-ne { background: var(--info-color); }
.badge-ncnp { background: #9ca3af; }
.badge-na { background: var(--text-placeholder); }

.arrow { color: var(--text-secondary); font-size: 13px; }

.match-icon { font-size: 14px; font-weight: 700; }
.match-icon.yes { color: var(--success-color); }
.match-icon.no { color: var(--danger-color); }

.no-data { color: var(--text-placeholder); font-size: 12px; }

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
  opacity: 0;
  transition: opacity var(--transition-normal);
}

.subject-card:hover .card-footer {
  opacity: 1;
}

.card-hint { font-size: 12px; color: var(--text-secondary); }
.card-arrow { font-size: 14px; color: var(--primary-color); }

.multi-header { font-weight: 600; font-size: 13px; line-height: 1.4; }
.multi-header-sub { font-size: 11px; color: var(--text-secondary); font-weight: 400; line-height: 1.4; }

.reason-text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
  font-size: 13px;
  color: var(--text-regular);
}

.loading, .empty {
  text-align: center;
  padding: 80px;
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}

@media (max-width: 1200px) {
  .stats-row { grid-template-columns: repeat(3, 1fr); }
  .subject-grid { grid-template-columns: repeat(3, 1fr); }
}

@media (max-width: 768px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .subject-grid { grid-template-columns: 1fr; }
  .section-header { flex-direction: column; gap: 16px; }
}
</style>

<style>
.history-popover {
  border-radius: var(--radius-lg) !important;
  border: 1px solid var(--primary-color) !important;
  z-index: 1000 !important;
  box-shadow: var(--shadow-xl);
}
</style>