<template>
  <div class="console-container">
    <!-- 面包屑 -->
    <div class="crumb-bar">
      <el-breadcrumb separator="/" class="crumb">
        <el-breadcrumb-item :to="{ path: '/subjects' }">受试者管理</el-breadcrumb-item>
        <el-breadcrumb-item>受试者详情 ({{ subject?.subject_id || '...' }})</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- PD 建议出组提示 -->
    <el-alert
      v-if="showDiscontinueHint"
      type="warning"
      :closable="false"
      show-icon
      class="discontinue-hint"
      title="最新评估为疾病进展（PD），建议出组"
      :description="`该受试者（${subject?.subject_id}）最近一次疗效评价为 PD，当前治疗方案可能已失效，建议触发出组流程。`"
    />

    <div v-if="loading" class="loading-box">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <el-empty v-else-if="!subject || !sortedAssessments.length" description="该受试者暂无评估数据" />

    <div v-else class="console-layout">
      <!-- 左侧：生命周期时间轴 -->
      <aside class="console-left">
        <h4 class="left-title">生命周期时间轴</h4>
        <el-timeline>
          <el-timeline-item
            v-for="(a, idx) in sortedAssessments"
            :key="a.id"
            :timestamp="formatDate(a.assessment_date)"
            :type="a.id === selectedId ? 'primary' : 'info'"
            :hollow="a.id !== selectedId"
            @click="selectAssessment(a.id)"
          >
            <div class="tl-label" :class="{ active: a.id === selectedId }">
              {{ nodeLabel(a, idx) }}
              <span v-if="idx === sortedAssessments.length - 1" class="tl-latest">[最新]</span>
            </div>
          </el-timeline-item>
        </el-timeline>
      </aside>

      <!-- 右侧：动态数据标签页 -->
      <main class="console-right">
        <el-tabs v-model="activeTab" class="console-tabs">
          <!-- 标签页二：详情 -->
          <el-tab-pane label="详情" name="detail">
            <section class="block">
              <h3 class="block-title">靶病灶列表</h3>
              <el-table :data="targetLesions" border size="small" empty-text="无靶病灶" @row-click="(row) => openLesionEdit('target', row)">
                <el-table-column prop="lesion_id" label="编号" width="100" />
                <el-table-column label="位置" min-width="140">
                  <template #default="s"><span class="lesion-cell-text">{{ s.row.location || '-' }}</span></template>
                </el-table-column>
                <el-table-column label="器官/淋巴结" min-width="120">
                  <template #default="s">
                    <span class="lesion-cell-text">
                      {{ s.row.organ || s.row.location || '-' }}
                      <span v-if="s.row.isLymphNode" class="ln-tag">淋</span>
                    </span>
                  </template>
                </el-table-column>
                <el-table-column label="基线长径(mm)" width="120" align="center">
                  <template #default="s">{{ fmtNum(s.row.baselineSize) }}</template>
                </el-table-column>
                <el-table-column label="当前长径(mm)" width="120" align="center">
                  <template #default="s">{{ fmtNum(s.row.currentSize) }}</template>
                </el-table-column>
                <el-table-column label="变化" width="110" align="center">
                  <template #default="s">
                    <span :style="{ color: changeColor(lesionChangePct(s.row)) }">{{ lesionChangePct(s.row) }}</span>
                  </template>
                </el-table-column>
              </el-table>

            </section>

            <section class="block">
              <h3 class="block-title">非靶病灶列表</h3>
              <el-table :data="nonTargetLesions" border size="small" empty-text="无非靶病灶" @row-click="(row) => openLesionEdit('nonTarget', row)">
                <el-table-column prop="lesion_id" label="编号" width="100" />
                <el-table-column label="位置" min-width="140">
                  <template #default="s"><span class="lesion-cell-text">{{ s.row.location || '-' }}</span></template>
                </el-table-column>
                <el-table-column label="器官/淋巴结" min-width="120">
                  <template #default="s">
                    <span class="lesion-cell-text">
                      {{ s.row.organ || s.row.location || '-' }}
                      <span v-if="s.row.isLymphNode" class="ln-tag">淋</span>
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="baseline_status" label="基线状态" width="120" align="center" />
                <el-table-column label="当前状态" width="120" align="center">
                  <template #default="s">
                    <span :class="ntlStatusClass(s.row.status)">{{ s.row.status || '-' }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </section>

            <section class="block">
              <h3 class="block-title">新病灶列表</h3>
              <el-table v-if="newLesions.length" :data="newLesions" border size="small" @row-click="(row) => openLesionEdit('newLesion', row)">
                <el-table-column prop="lesion_id" label="编号" width="100" />
                <el-table-column label="位置" min-width="140">
                  <template #default="s"><span class="lesion-cell-text">{{ s.row.location || '-' }}</span></template>
                </el-table-column>
                <el-table-column label="器官" min-width="120">
                  <template #default="s"><span class="lesion-cell-text">{{ s.row.organ || s.row.location || '-' }}</span></template>
                </el-table-column>
                <el-table-column prop="exam_date" label="检查日期" width="140" align="center" />
                <el-table-column prop="exam_method" label="检查方法" width="140" align="center" />
              </el-table>
              <el-empty v-else description="本评估期未检出新病灶" :image-size="60" />
            </section>
          </el-tab-pane>

          <!-- 标签页一：总览 -->
          <el-tab-pane label="总览" name="overview">
            <el-alert
              v-if="pdByNewLesion"
              type="error"
              :closable="false"
              show-icon
              class="pd-new-lesion-banner"
              title="新病灶触发 PD"
              description="检出新病灶，整体疗效自动判定为疾病进展（PD）。依据 RECIST 1.1：任何新病灶均一票否决为 PD。"
            />
            <div class="sod-cards">
              <div class="sod-card">
                <div class="sod-label">基线 SOD</div>
                <div class="sod-value">{{ fmtNum(selectedAssessment.baseline_sum) }} mm</div>
                <div class="sod-desc">终身基准值（不变）</div>
              </div>
              <div class="sod-card">
                <div class="sod-label">当前 SOD</div>
                <div class="sod-value" :style="{ color: changeColor(overallChangePercent) }">{{ fmtNum(selectedAssessment.current_sum) }} mm</div>
                <div class="sod-desc">较基线 {{ overallChangePercent }}</div>
              </div>
              <div class="sod-card">
                <div class="sod-label">Nadir SOD</div>
                <div class="sod-value">{{ fmtNum(selectedAssessment.nadir_sum) }} mm</div>
                <div class="sod-desc">历史最低点</div>
              </div>
            </div>

            <section class="block">
              <h3 class="block-title">靶病灶直径和（SLD）趋势<small class="sod-sub">SLD = Σ最长直径(非淋巴结)/最短直径(淋巴结) = 所有靶病灶直径和</small></h3>
              <div ref="chartRef" class="sod-chart"></div>
            </section>

            <section class="block">
              <h3 class="block-title">系统自动评价</h3>
              <div class="result-cards">
                <div class="result-card">
                  <div class="rc-label">靶病灶评估</div>
                  <span class="badge" :class="badgeClass(shortStatus(selectedAssessment.target_status))">{{ shortStatus(selectedAssessment.target_status) }}</span>
                </div>
                <div class="result-card">
                  <div class="rc-label">非靶病灶评估</div>
                  <span class="badge" :class="badgeClass(shortStatus(selectedAssessment.non_target_status))">{{ shortStatus(selectedAssessment.non_target_status) }}</span>
                </div>
                <div class="result-card">
                  <div class="rc-label">新病灶</div>
                  <span class="badge" :class="selectedAssessment.has_new_lesion ? 'badge-pd' : 'badge-cr'">{{ selectedAssessment.has_new_lesion ? '有' : '无' }}</span>
                </div>
                <div class="result-card overall">
                  <div class="rc-label">整体评价 (Overall Response)</div>
                  <span class="badge big" :class="badgeClass(shortStatus(selectedAssessment.overall_status))">{{ shortStatus(selectedAssessment.overall_status) }}</span>
                </div>
              </div>
            </section>
          </el-tab-pane>

          <!-- 标签页三：EDC 数据稽查核对 -->
          <el-tab-pane label="EDC数据稽查" name="verify">
            <section class="block">
              <h3 class="block-title">系统计算 vs 医生人工填写</h3>
              <div class="verify-grid">
                <div class="verify-head">
                  <div class="vh-item">评价维度</div>
                  <div class="vh-item">系统计算（规则引擎）</div>
                  <div class="vh-item">人工填写（EDC）</div>
                  <div class="vh-item">一致性</div>
                </div>
                <div v-for="row in verifyRows" :key="row.key" class="verify-row" :class="{ mismatch: row.hasMan && !row.match }">
                  <div class="vh-item">{{ row.label }}</div>
                  <div class="vh-item">
                    <span class="badge" :class="row.sysBadge">{{ row.sysText }}</span>
                  </div>
                  <div class="vh-item">
                    <span v-if="row.hasMan" class="badge" :class="row.manBadge">{{ row.manText }}</span>
                    <span v-else class="text-muted">无人工录入</span>
                  </div>
                  <div class="vh-item">
                    <span v-if="!row.hasMan" class="text-muted">—</span>
                    <span v-else :class="row.match ? 'flag-ok' : 'flag-bad'">{{ row.match ? '✓ 一致' : '✗ 不一致' }}</span>
                  </div>
                </div>
              </div>

              <div class="query-bar">
                <el-button
                  type="warning"
                  :disabled="!hasMismatch"
                  @click="sendQuery"
                >
                  一键下发疑问 (Query)
                </el-button>
                <span class="query-tip">
                  {{ hasMismatch ? '存在系统计算与人工录入不一致项，可下发数据质疑' : '系统计算与人工录入一致，无需质疑' }}
                </span>
              </div>
            </section>
          </el-tab-pane>
        </el-tabs>
      </main>

      <LesionEditDialog
        v-model="lesionEditDialog.visible"
        :type="lesionEditDialog.type"
        :is-add="lesionEditDialog.isAdd"
        :lesion="lesionEditDialog.lesion"
        :assessment-id="lesionEditDialog.assessmentId"
        :is-baseline="lesionEditIsBaseline"
        @saved="onLesionEditSaved"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { subjectApi } from '../api'
import LesionEditDialog from '../components/LesionEditDialog.vue'

const route = useRoute()

const subject = ref(null)
const loading = ref(false)
const selectedId = ref(null)
const activeTab = ref('overview')
const chartRef = ref(null)
let chartInstance = null

const loadSubject = async () => {
  // keep-alive 下从详情导航到列表（/subjects，无 id 参数）时 route.params.id 为 undefined，
  // 此时不发起请求，避免 GET /api/subjects/undefined 触发 422 报错弹窗。
  if (!route.params.id) {
    loading.value = false
    return
  }
  loading.value = true
  try {
    subject.value = await subjectApi.get(route.params.id)
    if (sortedAssessments.value.length) {
      selectedId.value = sortedAssessments.value[sortedAssessments.value.length - 1].id
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载受试者详情失败')
  } finally {
    loading.value = false
  }
}

// 评估按日期升序（时间轴）
const sortedAssessments = computed(() => {
  if (!subject.value?.assessments) return []
  return [...subject.value.assessments].sort((a, b) => {
    const da = new Date(a.assessment_date || 0).getTime()
    const db = new Date(b.assessment_date || 0).getTime()
    if (da !== db) return da - db
    return (a.id || 0) - (b.id || 0)
  })
})

const selectedAssessment = computed(() => {
  const list = sortedAssessments.value
  if (!list.length) return {}
  return list.find(a => a.id === selectedId.value) || list[list.length - 1]
})

const selectAssessment = (id) => {
  selectedId.value = id
}

// ===== 行点击编辑病灶（LesionEditDialog）=====
const lesionEditDialog = reactive({
  visible: false,
  type: '',
  isAdd: false,
  lesion: {},
  assessmentId: null
})
// 基线期 = 评估的 cycle_number === 1（真正的基线，而非“时间轴第一条/唯一一条”）。
// 修复：只有一条随访评估(cycle>1)的受试者曾被误判为基线，导致编辑时“当前信息”无法编辑。
const lesionEditIsBaseline = computed(() => {
  const a = sortedAssessments.value.find(x => x.id === selectedId.value)
  if (!a) return false
  return a.cycle_number === 1
})
const openLesionEdit = (type, row) => {
  const listKey = type === 'target' ? 'target_lesions'
    : type === 'nonTarget' ? 'non_target_lesions' : 'new_lesions'
  const raw = (selectedAssessment.value[listKey] || []).find(l => l.id === row.id) || row
  lesionEditDialog.type = type
  lesionEditDialog.isAdd = false
  lesionEditDialog.lesion = raw
  lesionEditDialog.assessmentId = selectedId.value
  lesionEditDialog.visible = true
}
const onLesionEditSaved = async () => {
  await loadSubject()
}

// 时间轴节点标签：优先使用 EDC 原始访视名称（如"肿瘤疗效评估（RECIST1.1）#2（第8周±7天）"），
// 没有则 fallback 到"周期N"
const nodeLabel = (assessment, idx) => {
  const name = assessment?.visit_name
  if (name && typeof name === 'string' && name.trim()) return name.trim()
  return `周期${idx + 1}`
}

// ===== 病灶数据映射（snake_case -> camelCase，复用 Assessment 逻辑）=====
const mapTargetLesion = (t) => ({
  id: t.id,
  lesion_id: t.lesion_id || '',
  name: t.name || '',
  location: t.location || '',
  organ: t.organ || '',
  isLymphNode: !!t.is_lymph_node,
  baselineSize: t.baseline_size ?? 0,
  currentSize: t.current_size ?? 0
})
const mapNonTargetLesion = (t) => ({
  id: t.id,
  lesion_id: t.lesion_id || '',
  name: t.name || '',
  location: t.location || '',
  organ: t.organ || '',
  isLymphNode: !!t.is_lymph_node,
  baseline_status: t.baseline_status ?? '持续存在',
  status: t.status || '持续存在'
})
const mapNewLesion = (t) => ({
  id: t.id,
  lesion_id: t.lesion_id || '',
  name: t.name || '',
  location: t.location || '',
  organ: t.organ || '',
  exam_date: t.exam_date || '',
  exam_method: t.exam_method || ''
})

const targetLesions = computed(() => (selectedAssessment.value.target_lesions || []).map(mapTargetLesion))
const nonTargetLesions = computed(() => (selectedAssessment.value.non_target_lesions || []).map(mapNonTargetLesion))
const newLesions = computed(() => (selectedAssessment.value.new_lesions || []).map(mapNewLesion))

// SOD 汇总
const baselineSum = computed(() => selectedAssessment.value.baseline_sum || 0)
const currentSum = computed(() => selectedAssessment.value.current_sum || 0)
const overallChangePercent = computed(() => {
  if (!baselineSum.value) return '0.0%'
  const p = ((currentSum.value - baselineSum.value) / baselineSum.value) * 100
  return (p > 0 ? '+' : '') + p.toFixed(1) + '%'
})

// ===== 工具函数 =====
const formatDate = (dt) => (dt ? new Date(dt).toLocaleDateString('zh-CN') : '-')
const fmtNum = (v) => (v !== null && v !== undefined && v !== '') ? Number(v).toFixed(1) : '-'

const shortStatus = (s) => {
  const map = {
    '完全缓解': 'CR', '部分缓解': 'PR', '疾病稳定': 'SD', '疾病进展': 'PD',
    '无法评估': 'NE', '非完全缓解/非疾病进展': '非完全缓解(Non-CR)/非疾病进展(Non-PD)', 'Non-CR/Non-PD': '非完全缓解(Non-CR)/非疾病进展(Non-PD)', '不适用': 'N/A'
  }
  return map[s] || s || 'NE'
}
const badgeClass = (status) => {
  const map = { CR: 'badge-cr', PR: 'badge-pr', SD: 'badge-sd', PD: 'badge-pd', NE: 'badge-ne', 'Non-CR/Non-PD': 'badge-ncnp', '非完全缓解(Non-CR)/非疾病进展(Non-PD)': 'badge-ncnp', '不适用': 'badge-na' }
  return map[status] || 'badge-ne'
}
const changeColor = (pctText) => {
  const p = parseFloat(pctText)
  if (isNaN(p)) return ''
  if (p <= -30) return '#67c23a'
  if (p >= 20) return '#f56c6c'
  return '#e6a23c'
}
const lesionChangePct = (row) => {
  const b = Number(row.baselineSize) || 0
  const c = Number(row.currentSize) || 0
  if (!b) return '0.0%'
  const pct = ((c - b) / b) * 100
  return (pct > 0 ? '+' : '') + pct.toFixed(1) + '%'
}
const ntlStatusClass = (status) => {
  if (status === '消失') return 'ntl-gone'
  if (status === '进展') return 'ntl-prog'
  return 'ntl-persist'
}

// ===== 状态机提示：最新评估 PD -> 建议出组 =====
const showDiscontinueHint = computed(() => {
  const list = sortedAssessments.value
  if (!list.length) return false
  const latest = list[list.length - 1]
  return latest.overall_status === '疾病进展' || latest.overall_status === 'PD'
})

// 新病灶触发 PD 的联动高亮（当前查看的评估）
const pdByNewLesion = computed(() => {
  const a = selectedAssessment.value
  if (!a) return false
  const overall = a.overall_status
  return (overall === 'PD' || overall === '疾病进展') && a.has_new_lesion
})

// ===== EDC 稽查对比 =====
const verifyRows = computed(() => {
  const a = selectedAssessment.value
  if (!a) return []
  const build = (label, sysVal, manVal, sysIsNew) => {
    const sysText = sysIsNew ? (sysVal ? '有' : '无') : shortStatus(sysVal)
    const manText = sysIsNew ? (manVal ? '有' : '无') : shortStatus(manVal)
    const sysBadge = sysIsNew
      ? (sysVal ? 'badge-pd' : 'badge-cr')
      : badgeClass(shortStatus(sysVal))
    const manBadge = sysIsNew
      ? (manVal ? 'badge-pd' : 'badge-cr')
      : badgeClass(shortStatus(manVal))
    const hasMan = manVal !== null && manVal !== undefined && manVal !== ''
    return { label, sysText, manText, sysBadge, manBadge, hasMan, match: hasMan ? sysText === manText : null }
  }
  return [
    build('靶病灶评估', a.target_status, a.manual_target_status, false),
    build('非靶病灶评估', a.non_target_status, a.manual_non_target_status, false),
    build('新病灶', a.has_new_lesion, a.manual_has_new_lesion, true),
    build('整体评价', a.overall_status, a.manual_overall_status, false)
  ]
})
const hasMismatch = computed(() => verifyRows.value.some(r => r.hasMan && !r.match))

// 一键下发疑问（前端模拟，预留后端接口）
const sendQuery = async () => {
  try {
    await ElMessageBox.confirm(
      '将向临床中心发送数据质疑（Query）：系统计算结果与医生人工录入不一致，请核实。',
      '下发数据疑问',
      { type: 'warning', confirmButtonText: '确认下发', cancelButtonText: '取消' }
    )
    // TODO: 后端接口就绪后替换为真实调用，例如：
    // await api.post(`/api/subjects/${subject.value.id}/queries`, { items: mismatchedRows })
    ElMessage.success('已向临床中心下发数据质疑（模拟）')
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
}

// ===== 折线图 =====
const initChart = () => {
  const el = chartRef.value
  if (!el) return false
  if (!chartInstance) chartInstance = echarts.init(el)
  const labels = sortedAssessments.value.map((a, i) => nodeLabel(a, i))
  const currentValues = sortedAssessments.value.map(a => a.current_sum ?? 0)
  const baselineVal = sortedAssessments.value[0]?.baseline_sum ?? 0
  const baselineValues = labels.map(() => baselineVal)
  chartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const idx = params[0].dataIndex
        let html = `<strong>${labels[idx]}</strong><br/>`
        params.forEach(p => {
          if (p.value != null) {
            const suffix = p.seriesName.includes('SLD') ? ' mm' : ''
            html += `${p.marker} ${p.seriesName}: <b>${Number(p.value).toFixed(1)}</b>${suffix}<br/>`
          }
        })
        // 基线 SLD 参照值
        if (baselineVal != null) {
          html += `─────────<br/>基线 SLD: <b>${Number(baselineVal).toFixed(1)}</b> mm`
        }
        return html
      }
    },
    legend: { data: ['当前SLD', '基线SLD'], bottom: 0 },
    grid: { left: 50, right: 20, top: 30, bottom: 50 },
    xAxis: { type: 'category', data: labels, axisLabel: { interval: 0, rotate: labels.some(l => l.length > 6) ? 15 : 0 } },
    yAxis: { type: 'value', name: 'SLD (mm)' },
    series: [
      {
        name: '当前SLD',
        type: 'line',
        data: currentValues,
        smooth: true,
        symbolSize: 8,
        lineStyle: { width: 3 },
        itemStyle: { color: '#409eff' }
      },
      {
        name: '基线SLD',
        type: 'line',
        data: baselineValues,
        symbol: 'none',
        lineStyle: { type: 'dashed', width: 2, color: '#909399' },
        itemStyle: { color: '#909399' }
      }
    ]
  })
  // 确保容器尺寸正确（解决 keep-alive / display:hidden 后尺寸为0的问题）
  setTimeout(() => chartInstance?.resize(), 50)
  return true
}

// 带重试的图表初始化：等待 DOM 就绪后画图
const scheduleChart = async () => {
  await nextTick()
  if (initChart()) return
  // 首次 nextTick 后 chartRef 可能还没渲染（v-else 条件块），等一帧再试
  await nextTick()
  if (initChart()) return
  // 最后兜底：等浏览器绘制完成
  setTimeout(() => initChart(), 100)
}

const onResize = () => chartInstance && chartInstance.resize()

// 三重依赖：activeTab 切换 / 时间轴选中变化 / 数据加载完成（sortedAssessments 长度从 0 变 N）
// immediate:true 确保挂载即检查（数据可能已由 keep-alive 缓存）
watch(
  [activeTab, selectedId, () => sortedAssessments.value.length],
  async () => {
    if (activeTab.value === 'overview' && sortedAssessments.value.length) {
      scheduleChart()
    }
  },
  { immediate: true }
)

onMounted(() => {
  loadSubject()
  window.addEventListener('resize', onResize)
})

// 路由参数变化（切换不同受试者）时强制重新加载，避免 Vue Router 复用组件导致显示旧受试者数据
watch(() => route.params.id, (id) => {
  if (id) loadSubject()
})
onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  chartInstance && chartInstance.dispose()
  chartInstance = null
})
</script>

<style scoped>
.console-container {
  padding: 4px 8px 24px;
}
.crumb {
  margin: 0;
  flex: 1;
}
.crumb-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin: 8px 0 16px;
}
.sod-sub {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-secondary);
  margin-left: 8px;
}
.ln-tag {
  display: inline-block;
  margin-left: 4px;
  padding: 0 4px;
  font-size: 11px;
  line-height: 16px;
  color: #fff;
  background: #909399;
  border-radius: 3px;
  vertical-align: middle;
}
.discontinue-hint {
  margin-bottom: 16px;
}
.loading-box {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 80px 0;
  color: var(--text-secondary);
}
.console-layout {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}
.console-left {
  width: 260px;
  flex-shrink: 0;
  background: #fafafa;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
  position: sticky;
  top: 16px;
}
.left-title {
  font-size: 15px;
  margin: 0 0 12px;
  color: var(--text-primary);
}
.tl-label {
  cursor: pointer;
  font-weight: 600;
  color: var(--text-regular);
}
.tl-label.active {
  color: var(--primary-color);
}
.tl-latest {
  color: #f56c6c;
  font-size: 12px;
  margin-left: 4px;
}
.tl-sub {
  font-size: 12px;
  color: var(--text-secondary);
}
.console-right {
  flex: 1;
  min-width: 0;
}
.block {
  margin-bottom: 24px;
}
.block-title {
  font-size: 16px;
  margin: 0 0 12px;
  color: var(--text-primary);
  border-left: 3px solid var(--primary-color);
  padding-left: 8px;
}
.lesion-cell-text {
  display: inline-block;
  width: 100%;
  white-space: normal;
  word-break: break-word;
  line-height: 1.5;
  text-align: left;
}

/* SOD 汇总卡片 */
.sod-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 16px;
}
.sod-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 14px 16px;
  background: #fff;
}
.sod-label {
  font-size: 13px;
  color: var(--text-secondary);
}
.sod-value {
  font-size: 22px;
  font-weight: 700;
  margin: 6px 0 2px;
  color: var(--text-primary);
}
.sod-desc {
  font-size: 12px;
  color: var(--text-secondary);
}

/* 折线图 */
.sod-chart {
  width: 100%;
  height: 320px;
}

/* 疗效大字卡片 */
.result-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.result-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: #fff;
}
.result-card.overall {
  grid-column: 1 / -1;
  background: #f5f7fa;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}
.rc-label {
  font-size: 14px;
  color: var(--text-secondary);
}
.badge {
  display: inline-block;
  padding: 2px 12px;
  border-radius: 12px;
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.6;
  width: fit-content;
}
.badge.big {
  font-size: 20px;
  padding: 6px 22px;
}
.badge-cr { background: #67c23a; }
.badge-pr { background: #409eff; }
.badge-sd { background: #e6a23c; }
.badge-pd { background: #f5f7fa; color: #f56c6c; border: 1px solid #f56c6c; }
.badge-ne { background: #909399; }
.badge-ncnp { background: #9ca3af; }
.badge-na { background: #c0c4cc; }

.ntl-gone { color: #67c23a; }
.ntl-persist { color: #e6a23c; }
.ntl-prog { color: #f56c6c; }

/* EDC 稽查 */
.verify-grid {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
}
.verify-head, .verify-row {
  display: grid;
  grid-template-columns: 1.2fr 1.4fr 1.4fr 1fr;
  align-items: center;
}
.verify-head {
  background: #f5f7fa;
  font-weight: 600;
  font-size: 13px;
  color: var(--text-secondary);
}
.verify-row {
  border-top: 1px solid #ebeef5;
  background: #fff;
}
.verify-row.mismatch {
  background: #fef0f0;
}
.vh-item {
  padding: 12px 14px;
  font-size: 14px;
}
.text-muted {
  color: var(--text-secondary);
  font-size: 13px;
}
.flag-ok { color: #67c23a; font-weight: 600; }
.flag-bad { color: #f56c6c; font-weight: 600; }
.query-bar {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
}
.query-tip {
  font-size: 13px;
  color: var(--text-secondary);
}

.pd-new-lesion-banner {
  margin-bottom: 16px;
}

.visit-select {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.visit-label {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
}

.row-hint {
  font-size: 12px;
  color: var(--primary-color);
  font-weight: 400;
  margin-left: 8px;
}

/* 布局：左侧时间轴 + 右侧内容 */
.console-layout {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}
.console-left {
  width: 200px;
  min-width: 180px;
  flex-shrink: 0;
}
.left-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--text-primary);
}

/* 时间轴节点标签 */
.tl-label {
  cursor: pointer;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-all;
  transition: color 0.2s;
}
.tl-label.active {
  color: #409eff;
  font-weight: 600;
}
.tl-latest {
  color: #f56c6c;
  font-size: 11px;
  margin-left: 4px;
}
/* 时间轴内容区（右侧）自动撑满剩余空间 */
.console-layout > :last-child {
  flex: 1;
  min-width: 0;
}
</style>
