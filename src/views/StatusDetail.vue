<template>
  <div class="status-detail-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <el-button text @click="$router.push('/analysis')" class="back-btn">
        <span class="back-arrow">←</span> 返回
      </el-button>
      <h2>{{ pageTitle }}（共 {{ filteredRows.length }} 条记录）</h2>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input v-model="searchText" placeholder="输入或选择受试者编号搜索" clearable style="width:280px" />
      <el-select v-model="selectedStatusFilter" placeholder="筛选状态" clearable style="width:180px; margin-left:12px">
        <template v-for="opt in statusFilterOptions" :key="opt.value">
          <el-option :label="opt.label" :value="opt.value" />
        </template>
      </el-select>
    </div>

    <!-- 数据表格 -->
    <div class="table-wrapper">
      <el-table :data="pagedRows" border stripe size="small" v-loading="loading">
        <el-table-column prop="subject_id" label="受试者编号" width="130" align="center" fixed />
        <el-table-column label="时点" width="120" align="center">
          <template #default="{ row }">
            {{ formatTimepoint(row) }}
          </template>
        </el-table-column>
        <el-table-column label="靶病灶评估" width="150" align="center">
          <template #default="{ row }">
            <div class="dual-badge">
              <span class="mini-badge auto" :class="badgeClass(row.target_status)">{{ shortStatus(row.target_status) }}</span>
              <span class="badge-arrow">→</span>
              <span class="mini-badge manual" :class="badgeClass(row.manual_target_status)">{{ shortManual(row.manual_target_status) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="非靶病灶评估" width="160" align="center">
          <template #default="{ row }">
            <div class="dual-badge">
              <span class="mini-badge auto" :class="badgeClass(row.non_target_status)">{{ shortStatus(row.non_target_status) }}</span>
              <span class="badge-arrow">→</span>
              <span class="mini-badge manual" :class="badgeClass(row.manual_non_target_status)">{{ shortManual(row.manual_non_target_status) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="新病灶" width="110" align="center">
          <template #default="{ row }">
            <div class="dual-badge">
              <el-tag :type="row.has_new_lesion ? 'danger' : 'success'" size="small">{{ row.has_new_lesion ? '有' : '无' }}</el-tag>
              <span v-if="row.manual_has_new_lesion !== undefined && row.has_manual_data" class="badge-arrow">→</span>
              <el-tag v-if="row.manual_has_new_lesion !== undefined && row.has_manual_data" :type="row.manual_has_new_lesion ? 'danger' : 'success'" size="small">{{ row.manual_has_new_lesion ? '有' : '无' }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="总体疗效评估" width="160" align="center">
          <template #default="{ row }">
            <div class="dual-badge">
              <span class="mini-badge auto" :class="overallBadgeClass(row.overall_status)">
                <el-tag :type="getStatusTagType(row.overall_status)" size="small">{{ shortStatus(row.overall_status) }}</el-tag>
              </span>
              <span class="badge-arrow">→</span>
              <span class="mini-badge manual" :class="overallBadgeClass(row.manual_overall_status)">
                <el-tag :type="getStatusTagType(row.manual_overall_status)" size="small">{{ shortManual(row.manual_overall_status) }}</el-tag>
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="overall_reason" label="程序判定理由" min-width="260">
          <template #default="{ row }"><div class="reason-text">{{ row.overall_reason }}</div></template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="goToSubject(row.subject_db_id)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="filteredRows.length > pageSize"
        background layout="total, sizes, prev, pager, next"
        :total="filteredRows.length"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        v-model:current-page="currentPage"
        @size-change="(s) => { pageSize = s; currentPage = 1 }"
        style="margin-top:16px; justify-content:flex-end"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { analysisApi } from '../api'
import { getStatusTagType } from '../utils/recist'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const statistics = ref(null)

// 路由参数
const dimType = computed(() => route.params.dimType || 'target')     // target | nonTarget | newLesion
const statusValue = computed(() => {
  const v = route.params.statusValue || ''
  // newLesion 的 statusValue 是 'true'/'false' 字符串
  if (v === 'true') return true
  if (v === 'false') return false
  return v
})

// 搜索与分页
const searchText = ref('')
const selectedStatusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

// 维度名称映射
const dimNames = { target: '靶病灶', nonTarget: '非靶病灶', newLesion: '新病灶' }

// 状态元标签映射
const STATUS_META = {
  'CR': { label: '完全缓解', cls: 'cr' },
  'PR': { label: '部分缓解', cls: 'pr' },
  'SD': { label: '疾病稳定', cls: 'sd' },
  'PD': { label: '疾病进展', cls: 'pd' },
  'NE': { label: '无法评估', cls: 'ne' },
  'Non-CR/Non-PD': { label: '非CR/非PD', cls: 'ncnp' }
}

// 筛选状态下拉选项 —— 根据当前维度生成
const statusFilterOptions = computed(() => {
  if (!statistics.value) return []
  const counts = dimType.value === 'target'
    ? (statistics.value.target_status_counts || {})
    : dimType.value === 'nonTarget'
      ? (statistics.value.non_target_status_counts || {})
      : {}
  const options = Object.keys(counts).map(k => ({
    label: `${STATUS_META[k]?.label || k} (${counts[k]})`,
    value: k
  }))
  // 如果是 newLesion 维度，加两个布尔选项
  if (dimType.value === 'newLesion') {
    const nc = statistics.value.new_lesion_count || 0
    const total = statistics.value.total_assessments || 0
    options.unshift(
      { label: `检出新病灶 (${nc})`, value: true },
      { label: `未检出新病灶 (${total - nc})`, value: false }
    )
  }
  return options
})

// 页面标题
const pageTitle = computed(() => {
  const dim = dimNames[dimType.value] || dimType.value
  let valLabel = ''
  if (typeof statusValue.value === 'boolean') {
    valLabel = statusValue.value ? '检出新病灶' : '未检出新病灶'
  } else {
    valLabel = STATUS_META[statusValue.value]?.label || statusValue.value
  }
  return `${valLabel} (${statusValue.value}) - 详细信息`
})

// 原始评估表数据
const assessmentTable = computed(() => statistics.value?.assessment_table || [])

// 按维度过滤的行
const dimFilteredRows = computed(() => {
  let rows = [...assessmentTable.value]
  const dt = dimType.value
  const sv = statusValue.value

  if (dt === 'target') {
    rows = rows.filter(r => (r.target_status || 'NE') === sv)
  } else if (dt === 'nonTarget') {
    rows = rows.filter(r => (r.non_target_status || 'NE') === sv)
  } else if (dt === 'newLesion') {
    rows = rows.filter(r => !!r.has_new_lesion === !!sv)
  }
  return rows
})

// 再按搜索 + 二次状态筛选
const filteredRows = computed(() => {
  let rows = dimFilteredRows.value
  if (searchText.value) {
    const q = searchText.value.toLowerCase()
    rows = rows.filter(r => r.subject_id?.toLowerCase().includes(q))
  }
  if (selectedStatusFilter.value) {
    rows = rows.filter(r => r.overall_status === selectedStatusFilter.value)
  }
  return rows
})

// 分页后数据
const pagedRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredRows.value.slice(start, start + pageSize.value)
})

// ========== 工具函数 ==========

const shortStatus = (s) => {
  const map = {
    '完全缓解': 'CR', '部分缓解': 'PR', '疾病稳定': 'SD', '疾病进展': 'PD',
    '无法评估': 'NE', 'Non-CR/Non-PD': '非CR/非PD', '不适用': 'N/A'
  }
  return map[s] || s || '-'
}

const shortManual = (s) => {
  if (!s) return '-'
  return shortStatus(s)
}

const badgeClass = (status) => {
  const map = {
    CR: 'badge-cr', PR: 'badge-pr', SD: 'badge-sd', PD: 'badge-pd',
    NE: 'badge-ne', 'Non-CR/Non-PD': 'badge-ncnp', '不适用': 'badge-na'
  }
  return map[status] || 'badge-ne'
}

const overallBadgeClass = (status) => {
  return '' // 用 el-tag 自带颜色，不再叠加 mini-badge 背景
}

const formatTimepoint = (row) => {
  if (row.timepoint) return row.timepoint
  if (row.assessment_date) {
    try {
      const d = new Date(row.assessment_date)
      if (!isNaN(d.getTime())) {
        return `第${d.getMonth() + 1}周±${d.getDate()}天`
      }
    } catch (_) {}
  }
  if (row.cycle_number != null) return `周期${row.cycle_number}`
  return '-'
}

const goToSubject = (dbId) => {
  router.push({ path: `/subjects/${dbId}` })
}

// ========== 数据加载 ==========

onMounted(async () => {
  loading.value = true
  try {
    const res = await analysisApi.getStatistics()
    statistics.value = res.data || res
  } catch (e) {
    console.error('加载统计数据失败:', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.status-detail-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}
.page-header h2 {
  font-size: 22px;
  color: var(--text-primary);
  margin: 0;
}
.back-btn {
  font-size: 15px;
  color: #409eff;
  cursor: pointer;
  padding: 4px 8px;
}
.back-btn:hover {
  background-color: rgba(64, 158, 255, 0.08);
}
.back-arrow {
  font-weight: bold;
  margin-right: 4px;
}

.filter-bar {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.table-wrapper {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

/* 双 badge 行内布局 */
.dual-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.badge-arrow {
  color: #999;
  font-size: 11px;
  user-select: none;
}

/* Mini badge */
.mini-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  color: white;
}
.mini-badge.auto { opacity: 0.95; }
.mini-badge.manual { opacity: 0.85; }

.badge-cr { background: #67c23a; }
.badge-pr { background: #409eff; }
.badge-sd { background: #e6a23c; }
.badge-pd { background: #f56c6c; }
.badge-ne { background: #909399; }
.badge-ncnp { background: #909399; }
.badge-na { background: #c0c4cc; }

/* 理由文本 */
.reason-text {
  line-height: 1.5;
  word-break: break-word;
  font-size: 13px;
  color: #606266;
}
</style>
