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
      <span class="result-count">共 {{ filteredRows.length }} 位受试者</span>
    </div>

    <!-- 数据表格 -->
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="filteredRows.length === 0" class="empty">
      <el-empty description="暂无数据" />
    </div>
    <div v-else>
      <el-table :data="pagedRows" border stripe size="small" style="width: 100%">
        <el-table-column prop="subject_id" label="受试者编号" width="140" align="center" />
        <el-table-column width="170" align="center">
          <template #header>
            <div class="multi-header">最新总体疗效</div>
            <div class="multi-header-sub">程序 ↔ 人工</div>
          </template>
          <template #default="scope">
            <div class="compare-pair">
              <div class="labeled-badge">
                <span class="source-label">程序</span>
                <span class="badge auto" :class="badgeClass(scope.row.effective_status)">{{ shortStatus(scope.row.effective_status) }}</span>
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
        <el-table-column label="操作" width="90" align="center" fixed="right">
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
const page = ref(1)
const pageSize = ref(10)
const { state, loadBatches } = useBatchStore()

// 优先使用来源页传入的批次，未指定时回退到当前（最新）批次
const batchId = computed(() => route.query.batch || state.currentBatchId)

const pageTitle = computed(() => {
  const cnt = statistics.value?.batches?.find(b => b.id === batchId.value)?.subjects_count
  return cnt != null ? `受试者明细（共 ${cnt} 人）` : '受试者明细'
})

// 按受试者聚合：取 cycle_number 最大（最新）的一条作为「最新总体疗效」
const subjectRows = computed(() => {
  const table = statistics.value?.assessment_table || []
  const map = new Map()
  for (const r of table) {
    if (!r.subject_db_id) continue
    const cur = map.get(r.subject_db_id)
    if (!cur || (r.cycle_number || 0) >= (cur.cycle_number || 0)) {
      map.set(r.subject_db_id, r)
    }
  }
  return Array.from(map.values())
})

const filteredRows = computed(() => {
  let rows = subjectRows.value
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    rows = rows.filter(r => r.subject_id?.toLowerCase().includes(q))
  }
  return rows
})

// 搜索下拉选项（按受试者编号）
const subjectOptions = computed(() => {
  return subjectRows.value.map(r => ({ value: r.subject_id, label: r.subject_id }))
})

const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredRows.value.slice(start, start + pageSize.value)
})

watch(searchQuery, () => { page.value = 1 })

const shortStatus = (s) => {
  const map = {
    '完全缓解': 'CR', '部分缓解': 'PR', '疾病稳定': 'SD', '疾病进展': 'PD',
    '无法评估': 'NE', '非完全缓解/非疾病进展': 'Non-CR/Non-PD', 'Non-CR/Non-PD': 'Non-CR/Non-PD', '不适用': 'N/A'
  }
  return map[getStatusText(s)] || s || 'NE'
}

const badgeClass = (status) => {
  const map = {
    CR: 'badge-cr', PR: 'badge-pr', SD: 'badge-sd', PD: 'badge-pd',
    NE: 'badge-ne', 'Non-CR/Non-PD': 'badge-ncnp', '不适用': 'badge-na'
  }
  return map[status] || 'badge-ne'
}

const goToSubject = (subjectDbId) => {
  router.push({ path: `/subjects/${subjectDbId}`, query: batchId.value ? { batch: batchId.value } : {} })
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
