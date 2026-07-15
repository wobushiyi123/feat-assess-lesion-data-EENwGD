<template>
  <div class="stat-detail-container">
    <div class="page-header">
      <el-button @click="$router.back()" :icon="ArrowLeft">返回</el-button>
      <h2>{{ pageTitle }}</h2>
    </div>

    <!-- 筛选和搜索 -->
    <div class="filter-bar">
      <el-select
        v-model="searchQuery"
        placeholder="输入或选择受试者编号搜索"
        filterable
        clearable
        size="default"
        style="width: 240px"
        @clear="searchQuery = ''"
      >
        <el-option
          v-for="opt in subjectOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
      <el-select v-model="filterStatus" placeholder="筛选状态" clearable size="default" style="width: 160px">
        <el-option label="全部" value="" />
        <el-option label="CR" value="CR" />
        <el-option label="PR" value="PR" />
        <el-option label="SD" value="SD" />
        <el-option label="PD" value="PD" />
        <el-option label="NE" value="NE" />
      </el-select>
      <span class="result-count">共 {{ filteredRows.length }} 条记录</span>
    </div>

    <!-- 数据表格 -->
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="filteredRows.length === 0" class="empty">
      <el-empty description="暂无数据" />
    </div>
    <div v-else>
      <el-table :data="pagedRows" border stripe size="small" style="width: 100%">
        <el-table-column prop="subject_id" label="受试者编号" width="130" align="center" />
        <el-table-column prop="timepoint" label="时间点" width="140" align="center" />
        <el-table-column width="150" align="center">
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
        <el-table-column width="150" align="center">
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
        <el-table-column width="120" align="center">
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
        <el-table-column width="150" align="center">
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
        <el-table-column prop="overall_reason" label="程序判定理由" min-width="280">
          <template #default="scope">
            <div class="reason-text">{{ scope.row.overall_reason }}</div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center" fixed="right">
          <template #default="scope">
            <el-button type="primary" size="small" link @click="goToSubject(scope.row.subject_db_id)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-if="filteredRows.length > pageSize"
        class="pager"
        background
        layout="total, sizes, prev, pager, next"
        :total="filteredRows.length"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        v-model:current-page="page"
        @size-change="(s) => { pageSize = s; page = 1 }"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { analysisApi } from '../api'
import { getStatusText } from '../utils/recist'
import { useBatchStore } from '../store/batch'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const statistics = ref(null)
const searchQuery = ref('')
const filterStatus = ref('')
const page = ref(1)
const pageSize = ref(10)
const { state, loadBatches } = useBatchStore()

const statType = computed(() => route.params.type)
// 优先使用首页传入的批次，未指定时回退到当前（最新）批次
const batchId = computed(() => route.query.batch || state.currentBatchId)

const pageTitle = computed(() => {
  const titles = {
    'total': '总评估次数 - 详细信息',
    'match': '自动 ↔ 人工一致 - 详细信息',
    'mismatch': '不一致记录 - 详细信息',
    'no_human': '无人工数据 - 详细信息',
    'rate': '一致率 - 详细信息',
    'CR': '完全缓解 (CR) - 详细信息',
    'PR': '部分缓解 (PR) - 详细信息',
    'SD': '疾病稳定 (SD) - 详细信息',
    'PD': '疾病进展 (PD) - 详细信息',
    'NE': '无法评估 (NE) - 详细信息',
    'Non-CR/Non-PD': '非CR/非PD - 详细信息'
  }
  return titles[statType.value] || '详细信息'
})

const allRows = computed(() => {
  const table = statistics.value?.assessment_table || []
  const type = statType.value

  if (type === 'total' || type === 'rate') {
    return table
  } else if (type === 'match') {
    return table.filter(r => r.overall_match === true)
  } else if (type === 'mismatch') {
    return table.filter(r => r.overall_match === false)
  } else if (type === 'no_human') {
    return table.filter(r => !r.manual_overall_status)
  } else {
    // Status filter (CR/PR/SD/PD/NE/Non-CR/Non-PD) —— 使用有效状态(人工/程序)
    return table.filter(r => r.effective_status === type)
  }
})

const filteredRows = computed(() => {
  let rows = allRows.value
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    rows = rows.filter(r => r.subject_id?.toLowerCase().includes(q))
  }
  if (filterStatus.value) {
    rows = rows.filter(r => r.effective_status === filterStatus.value)
  }
  return rows
})

// 组合框选项（去重）
const subjectOptions = computed(() => {
  const map = new Map()
  allRows.value.forEach(r => {
    if (r.subject_db_id && !map.has(r.subject_db_id)) {
      map.set(r.subject_db_id, { value: r.subject_id, label: r.subject_id })
    }
  })
  return Array.from(map.values())
})

const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredRows.value.slice(start, start + pageSize.value)
})

watch(searchQuery, () => { page.value = 1 })
watch(filterStatus, () => { page.value = 1 })

const shortStatus = (s) => {
  const map = {
    '完全缓解': 'CR', '部分缓解': 'PR', '疾病稳定': 'SD', '疾病进展': 'PD',
    '无法评估': 'NE', '非完全缓解/非疾病进展': '非完全缓解(Non-CR)/非疾病进展(Non-PD)', 'Non-CR/Non-PD': '非完全缓解(Non-CR)/非疾病进展(Non-PD)', '不适用': 'N/A'
  }
  return map[getStatusText(s)] || s || 'NE'
}

const badgeClass = (status) => {
  const map = {
    CR: 'badge-cr', PR: 'badge-pr', SD: 'badge-sd', PD: 'badge-pd',
    NE: 'badge-ne', 'Non-CR/Non-PD': 'badge-ncnp', '非完全缓解(Non-CR)/非疾病进展(Non-PD)': 'badge-ncnp', '不适用': 'badge-na'
  }
  return map[status] || 'badge-ne'
}

const goToSubject = (subjectDbId) => {
  router.push({ path: `/report/${subjectDbId}`, query: { batch: batchId.value } })
}

const loadData = async () => {
  loading.value = true
  try {
    statistics.value = await analysisApi.getStatistics(batchId.value || undefined)
  } catch (e) {
    console.error(e)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadBatches()
  loadData()
})

onActivated(() => {
  loadData()
})

// 导入新数据 / 批次刷新后重新加载
watch(() => state.version, () => {
  loadData()
})
</script>

<style scoped>
.stat-detail-container {
  max-width: 1400px;
  margin: 0 auto;
  padding-bottom: 40px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 22px;
  color: #303133;
  margin: 0;
}

.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.result-count {
  font-size: 14px;
  color: #909399;
}

.pager {
  margin-top: 16px;
  justify-content: flex-end;
}

.loading, .empty {
  text-align: center;
  padding: 60px;
  color: #909399;
}

.multi-header {
  font-weight: 600;
  font-size: 13px;
  line-height: 1.4;
}

.multi-header-sub {
  font-size: 11px;
  color: #909399;
  font-weight: 400;
  line-height: 1.4;
}

.reason-text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
  font-size: 13px;
  color: #606266;
}

.compare-pair {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.labeled-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.source-label {
  font-size: 10px;
  color: #909399;
  line-height: 1;
}

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

.badge-cr { background: #67c23a; }
.badge-pr { background: #409eff; }
.badge-sd { background: #e6a23c; }
.badge-pd { background: #f56c6c; }
.badge-ne { background: #909399; }
.badge-ncnp { background: #9ca3af; }
.badge-na { background: #c0c4cc; }

.arrow {
  color: #909399;
  font-size: 13px;
}

.no-data {
  color: #c0c4cc;
  font-size: 12px;
}
</style>
