<template>
  <div class="analysis-container">
    <div class="page-header">
      <h2>智能数据分析</h2>
      <p class="page-subtitle">基于 RECIST 1.1 标准的病灶评估结果汇总与趋势分析</p>
      <div class="header-actions">
        <el-button type="warning" :icon="Document" @click="showQueryDialog = true">一键下发质疑</el-button>
      </div>
    </div>

    <div v-if="loading" class="loading">
      <span>加载中...</span>
    </div>

    <div v-else-if="statistics" class="analysis-content">
      <!-- 顶部核心指标 -->
      <div class="stats-section">
        <div class="stat-card primary clickable" @click="goToSubjects">
          <div class="stat-icon">👥</div>
          <div class="stat-info">
            <div class="stat-value">{{ latestBatchSubjects }}</div>
            <div class="stat-label">受试者总数</div>
          </div>
        </div>
        <div class="stat-card primary">
          <div class="stat-icon">📊</div>
          <div class="stat-info">
            <div class="stat-value">{{ state.batches.length }}</div>
            <div class="stat-label">评估次数</div>
          </div>
        </div>
        <el-tooltip placement="top" :show-after="300">
          <template #content>
            <div class="orr-tooltip"><strong>客观缓解率 (ORR)</strong><br/>ORR = (CR + PR) 受试者数 ÷ 可评估受试者总数 × 100%<br/><br/><span class="tip-explain">指肿瘤达到完全缓解(CR)或部分缓解(PR)的受试者占比，反映抗肿瘤治疗使肿瘤缩小的有效性。点击卡片可查看完整计算过程与受试者明细。</span></div>
          </template>
          <div class="stat-card highlight clickable" @click="openRateDialog('ORR')">
            <div class="stat-icon">📈</div>
            <div class="stat-info">
              <div class="stat-value">{{ statistics.response_rate }}%</div>
              <div class="stat-label">客观缓解率 (ORR)</div>
            </div>
          </div>
        </el-tooltip>
        <el-tooltip placement="top" :show-after="300">
          <template #content>
            <div class="dcr-tooltip"><strong>疾病控制率 (DCR)</strong><br/>DCR = (CR + PR + SD) 受试者数 ÷ 可评估受试者总数 × 100%<br/><br/><span class="tip-explain">指肿瘤达到完全缓解(CR)、部分缓解(PR)或疾病稳定(SD)的受试者占比，反映治疗对肿瘤的整体控制情况。点击卡片可查看完整计算过程与受试者明细。</span></div>
          </template>
          <div class="stat-card highlight clickable" @click="openRateDialog('DCR')">
            <div class="stat-icon">📉</div>
            <div class="stat-info">
              <div class="stat-value">{{ statistics.disease_control_rate }}%</div>
              <div class="stat-label">疾病控制率 (DCR)</div>
            </div>
          </div>
        </el-tooltip>
      </div>

      <!-- 评估结果分布（卡片式，可点击） -->
      <div class="distribution-section">
        <h3>评估结果分布</h3>
        <div class="distribution-grid">
          <div class="distribution-card cr clickable" @click="goToDistribution('CR')">
            <div class="distribution-value">{{ statusCount('CR') }}</div>
            <div class="distribution-label">完全缓解</div>
          </div>
          <div class="distribution-card pr clickable" @click="goToDistribution('PR')">
            <div class="distribution-value">{{ statusCount('PR') }}</div>
            <div class="distribution-label">部分缓解</div>
          </div>
          <div class="distribution-card sd clickable" @click="goToDistribution('SD')">
            <div class="distribution-value">{{ statusCount('SD') }}</div>
            <div class="distribution-label">疾病稳定</div>
          </div>
          <div class="distribution-card ncnp clickable" @click="goToDistribution('Non-CR/Non-PD')">
            <div class="distribution-value">{{ statusCount('Non-CR/Non-PD') }}</div>
            <div class="distribution-label">非CR/非PD</div>
          </div>
          <div class="distribution-card pd clickable" @click="goToDistribution('PD')">
            <div class="distribution-value">{{ statusCount('PD') }}</div>
            <div class="distribution-label">疾病进展</div>
          </div>
          <div class="distribution-card ne clickable" @click="goToDistribution('NE')">
            <div class="distribution-value">{{ statusCount('NE') }}</div>
            <div class="distribution-label">无法评估</div>
          </div>
        </div>
      </div>

      <!-- 病灶评估分布（可切换：靶 / 非靶 / 新，默认靶病灶） -->
      <div class="distribution-section">
        <div class="distribution-tabs">
          <button
            v-for="tab in distributionTabs"
            :key="tab.key"
            type="button"
            class="dist-tab"
            :class="{ active: selectedDist === tab.key }"
            @click="selectedDist = tab.key"
          >{{ tab.label }}</button>
        </div>

        <!-- 靶病灶评估分布 -->
        <div v-show="selectedDist === 'target'" class="dist-panel">
          <h3>靶病灶评估分布 <span class="dist-sub">（人工评估 / 程序自动判定）</span></h3>
          <div class="distribution-grid">
            <div v-for="(count, status) in targetStatusCounts" :key="'t-'+status" class="distribution-card clickable" :class="statusCardClass(status)" @click="$router.push({ path: '/analysis/status/target/' + status })">
              <div class="distribution-value">{{ count }}</div>
              <div class="distribution-label">{{ statusLabel(status) }}</div>
            </div>
          </div>
        </div>

        <!-- 非靶病灶评估分布 -->
        <div v-show="selectedDist === 'nonTarget'" class="dist-panel">
          <h3>非靶病灶评估分布 <span class="dist-sub">（人工评估 / 程序自动判定）</span></h3>
          <div class="distribution-grid">
            <div v-for="(count, status) in nonTargetStatusCounts" :key="'nt-'+status" class="distribution-card clickable" :class="statusCardClass(status)" @click="$router.push({ path: '/analysis/status/nonTarget/' + status })">
              <div class="distribution-value">{{ count }}</div>
              <div class="distribution-label">{{ statusLabel(status) }}</div>
            </div>
          </div>
        </div>

        <!-- 新病灶分布 -->
        <div v-show="selectedDist === 'new'" class="dist-panel">
          <h3>新病灶分布</h3>
          <div class="distribution-grid">
            <div class="distribution-card clickable pd" @click="$router.push({ path: '/analysis/status/newLesion/true' })">
              <div class="distribution-value">{{ newLesionCount }}</div>
              <div class="distribution-label">检出新病灶</div>
            </div>
            <div class="distribution-card clickable cr" @click="$router.push({ path: '/analysis/status/newLesion/false' })">
              <div class="distribution-value">{{ totalAssessments - newLesionCount }}</div>
              <div class="distribution-label">未检出新病灶</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 受试者趋势分析 -->
      <div class="trend-section">
        <h3>受试者趋势分析</h3>
        <p class="trend-desc">选择受试者，系统基于历史疗效变化预测未来健康走向</p>
        <div class="trend-search">
          <el-select v-model="selectedSubjectId" placeholder="选择受试者" filterable clearable style="width: 300px">
            <el-option
              v-for="subject in subjects"
              :key="subject.id"
              :label="subject.subject_id"
              :value="subject.id"
            />
          </el-select>
          <el-button type="primary" @click="analyzeTrend" :loading="trendLoading">分析</el-button>
        </div>

        <div v-if="trendData" class="trend-content">
          <!-- 受试者信息 -->
          <div class="trend-subject-info">
            <span class="trend-subject-id">{{ trendData.subject_id }}</span>
          </div>

          <div class="trend-cards">
            <div class="trend-card">
              <div class="trend-label">趋势方向</div>
              <div class="trend-value" :class="getTrendClass(trendData.trend.trend_direction)">
                {{ getTrendText(trendData.trend.trend_direction) }}
              </div>
            </div>
            <div class="trend-card">
              <div class="trend-label">平均变化率</div>
              <div class="trend-value">{{ trendData.trend.avg_change_percent }}%</div>
            </div>
            <div class="trend-card">
              <div class="trend-label">预测下一周期</div>
              <div class="trend-value" v-if="trendData.prediction.predicted_status">
                <el-tag :type="getStatusTagType(trendData.prediction.predicted_status)" size="large">
                  {{ getStatusText(trendData.prediction.predicted_status) }}
                </el-tag>
                <div class="prediction-detail" v-if="trendData.prediction.predicted_change_percent !== undefined">
                  预测变化率: {{ trendData.prediction.predicted_change_percent.toFixed(1) }}%
                </div>
              </div>
              <div v-else class="trend-value no-prediction">数据不足</div>
            </div>
          </div>

          <!-- RECIST 标准分析 -->
          <div v-if="trendData.recist_analysis" class="recist-analysis">
            <h4>RECIST 1.1 标准趋势分析</h4>
            <div class="recist-analysis-content">
              <div v-for="(item, i) in trendData.recist_analysis" :key="i" class="recist-analysis-item">
                <span class="recist-icon">{{ item.icon }}</span>
                <span class="recist-text">{{ item.text }}</span>
              </div>
            </div>
          </div>

          <div v-if="trendData.historical_data?.length" class="trend-chart-wrapper">
            <h4>历史变化趋势</h4>
            <div ref="trendChartRef" class="trend-chart"></div>
          </div>

          <div v-if="trendData.recommendations?.length" class="recommendations">
            <h4>健康预测与智能建议</h4>
            <ul>
              <li v-for="(rec, i) in trendData.recommendations" :key="i">{{ rec }}</li>
            </ul>
          </div>

          <div v-if="trendData.anomalies?.length" class="anomalies">
            <h4>异常检测</h4>
            <el-alert
              v-for="(anomaly, i) in trendData.anomalies"
              :key="i"
              :title="anomaly.message"
              :type="anomaly.severity === 'high' ? 'error' : 'warning'"
              :closable="false"
              style="margin-bottom: 8px"
            />
          </div>
        </div>
      </div>

      <!-- 详细数据表格（按需求暂时隐藏，保留代码不删除） -->
      <div class="detail-section" v-if="false">
        <h3>详细评估数据</h3>
        <!-- ... 原有表格内容不变 ... -->
      </div>

      <!-- ===== 弹窗：ORR / DCR 详情 ===== -->
      <el-dialog v-model="showRateDialog" :title="rateDialogTitle" width="960px" top="5vh">
        <div class="rate-detail">
          <!-- 概念解释 -->
          <div class="rate-concept">
            <h4>📖 概念解释</h4>
            <div v-if="rateDialogType === 'ORR'" class="concept-text">
              <p><strong>客观缓解率（Objective Response Rate, ORR）</strong>是 RECIST 1.1 中衡量肿瘤治疗缓解效果的核心指标之一。</p>
              <p>定义为：达到<strong>完全缓解（CR）</strong>或<strong>部分缓解（PR）</strong>的受试者占所有可评估受试者的比例。它反映了肿瘤缩小的比例，是评价抗肿瘤药物疗效的重要终点指标。</p>
              <p><strong>判定标准（RECIST 1.1）</strong>：</p>
              <ul>
                <li><strong>CR（完全缓解）</strong>：所有靶病灶消失，且非靶病灶无进展，无新病灶出现。</li>
                <li><strong>PR（部分缓解）</strong>：靶病灶最长直径之和（SLD）较基线下降 ≥30%，且非靶病灶无明确进展，无新病灶。</li>
              </ul>
            </div>
            <div v-else class="concept-text">
              <p><strong>疾病控制率（Disease Control Rate, DCR）</strong>是 RECIST 1.1 中衡量肿瘤治疗整体控制效果的综合指标。</p>
              <p>定义为：达到<strong>完全缓解（CR）、部分缓解（PR）或疾病稳定（SD）</strong>的受试者占所有可评估受试者的比例。DCR 比 ORR 更宽泛，包含了肿瘤未增大也未缩小到 PR 标准的情况。</p>
              <p><strong>判定标准（RECIST 1.1）</strong>：</p>
              <ul>
                <li><strong>CR（完全缓解）</strong>：所有靶病灶消失。</li>
                <li><strong>PR（部分缓解）</strong>：靶病灶 SLD 较基线下降 ≥30%。</li>
                <li><strong>SD（疾病稳定）</strong>：未达 PR/PD 标准，即 SLD 较基线缩小不足 30%，且较研究期间最低值(nadir)增加不足 20% 或绝对值增加不足 5mm。</li>
              </ul>
            </div>
          </div>

          <!-- 计算过程 -->
          <div class="rate-calc">
            <h4>🧮 计算过程</h4>
            <div class="calc-formula">
              <span class="formula-label">{{ rateDialogType }} =</span>
              <span class="formula-expr">
                <template v-if="rateDialogType === 'ORR'">(CR + PR) 受试者数 ÷ 可评估总数 × 100%</template>
                <template v-else>(CR + PR + SD) 受试者数 ÷ 可评估总数 × 100%</template>
              </span>
              <span class="formula-eq">=</span>
              <span class="formula-num"><strong>{{ rateDialogType === 'ORR' ? orrNumerator : dcrNumerator }}</strong></span>
              <span class="formula-div">÷</span>
              <span class="formula-den">{{ rateDialogType === 'ORR' ? orrDenominator : dcrDenominator }}</span>
              <span class="formula-eq">=</span>
              <span class="formula-result"><strong>{{ rateDialogType === 'ORR' ? statistics.response_rate : statistics.disease_control_rate }}%</strong></span>
            </div>
          </div>

          <!-- 符合条件的受试者 -->
          <div class="rate-subjects">
            <h4>📋 符合条件的受试者明细（共 {{ rateSubjectRows.length }} 人）</h4>
            <el-table :data="pagedRateRows" border stripe size="small" max-height="40vh">
              <el-table-column prop="subject_id" label="受试者编号" width="130" align="center" />
              <el-table-column label="总体疗效" width="120" align="center">
                <template #default="{ row }">
                  <el-tag :type="getStatusTagType(row.overall_status)" size="small">{{ shortStatus(row.overall_status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="靶病灶评估" width="110" align="center">
                <template #default="{ row }">
                  <span class="mini-badge" :class="'badge-' + (row.target_status || 'ne').toLowerCase()">{{ shortStatus(row.target_status) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="变化率" width="100" align="right">
                <template #default="{ row }">{{ row.change_percent?.toFixed(1) ?? '-' }}%</template>
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
              v-if="rateSubjectRows.length > ratePageSize"
              background layout="total, prev, pager, next"
              :total="rateSubjectRows.length"
              :page-size="ratePageSize"
              v-model:current-page="ratePage"
              style="margin-top:12px;justify-content:flex-end"
            />
          </div>
        </div>
      </el-dialog>

      <!-- ===== 弹窗：一键下发质疑（程序/人工不一致数据） ===== -->
      <el-dialog v-model="showQueryDialog" title="数据质疑清单 (Data Query)" width="1100px" top="5vh">
        <div class="query-tip">
          以下为各受试者最新一次评估中<strong>总体疗效（程序）与总体疗效（人工）不一致</strong>的记录。可点击右下角「下载」导出 Excel 并选择保存位置。
        </div>
        <el-table :data="queryRows" border stripe size="small" max-height="46vh" empty-text="暂无不一致数据，无需质疑" :row-class-name="() => 'query-row'">
          <el-table-column prop="subject_id" label="受试者编号" width="120" align="center" />
          <el-table-column prop="visit" label="访视 / 周期" min-width="140" show-overflow-tooltip />
          <el-table-column label="总体疗效(程序)" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="getStatusTagType(row.overall_status)" size="small">{{ getStatusText(row.overall_status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="总体疗效(人工)" width="120" align="center">
            <template #default="{ row }">
              <span v-if="row.manual_overall_status">{{ getStatusText(row.manual_overall_status) }}</span>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="一致性" width="90" align="center">
            <template #default="{ row }">
              <span :class="row.overall_match === false ? 'flag-bad' : 'flag-ok'">{{ row.overall_match === false ? '✗ 不一致' : '✓ 一致' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="靶病灶(程序)" width="100" align="center">
            <template #default="{ row }">{{ row.target_status ? getStatusText(row.target_status) : '-' }}</template>
          </el-table-column>
          <el-table-column label="靶病灶(人工)" width="100" align="center">
            <template #default="{ row }"><span v-if="row.manual_target_status">{{ getStatusText(row.manual_target_status) }}</span><span v-else>-</span></template>
          </el-table-column>
          <el-table-column label="非靶(程序)" width="95" align="center">
            <template #default="{ row }">{{ row.non_target_status ? getStatusText(row.non_target_status) : '-' }}</template>
          </el-table-column>
          <el-table-column label="非靶(人工)" width="95" align="center">
            <template #default="{ row }"><span v-if="row.manual_non_target_status">{{ getStatusText(row.manual_non_target_status) }}</span><span v-else>-</span></template>
          </el-table-column>
          <el-table-column label="变化率" width="80" align="right">
            <template #default="{ row }">{{ row.change_percent != null ? Number(row.change_percent).toFixed(1) + '%' : '-' }}</template>
          </el-table-column>
          <el-table-column prop="overall_reason" label="程序判定理由" min-width="200">
            <template #default="{ row }"><div class="reason-text">{{ row.overall_reason }}</div></template>
          </el-table-column>
        </el-table>
        <template #footer>
          <el-button @click="showQueryDialog = false">关闭</el-button>
          <el-button type="success" :icon="Download" :loading="queryExporting" @click="exportQueryExcel">下载</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, onUnmounted, onActivated, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Document, Download } from '@element-plus/icons-vue'
import { analysisApi, subjectApi } from '../api'
import { getStatusText, getStatusTagType } from '../utils/recist'
import { useBatchStore } from '../store/batch'
import { exportToExcelWithPicker } from '../utils/export'
import * as echarts from 'echarts'

const router = useRouter()
const { state, loadBatches } = useBatchStore()

const loading = ref(false)
const trendLoading = ref(false)
const statistics = ref(null)
const subjects = ref([])
const selectedSubjectId = ref(null)
const trendData = ref(null)
const trendChartRef = ref(null)
const page = ref(1)
const pageSize = ref(10)
let trendChart = null

const statusOrder = ['CR', 'PR', 'SD', 'Non-CR/Non-PD', 'PD', 'NE']

const latestBatchSubjects = computed(() => {
  if (!statistics.value?.batches?.length) return 0
  // 优先取当前选中的 batch，否则取最新一次
  const batches = statistics.value.batches
  if (state.currentBatchId) {
    const current = batches.find(b => b.id === state.currentBatchId)
    if (current) return current.subjects_count || 0
  }
  return batches[0].subjects_count || 0
})

const loadData = async () => {
  loading.value = true
  try {
    const [stats, subs] = await Promise.all([
      analysisApi.getStatistics(state.currentBatchId),
      subjectApi.list({ limit: 1000, batch_id: state.currentBatchId })
    ])
    statistics.value = stats
    subjects.value = subs
  } catch (e) {
    console.error(e)
    ElMessage.error('加载统计数据失败')
  } finally {
    loading.value = false
  }
}

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

const statusCount = (status) => {
  return statistics.value?.status_counts?.[status] || 0
}

// 状态元信息：中文标签 + 卡片配色
const STATUS_META = {
  'CR': { label: '完全缓解', cls: 'cr' },
  'PR': { label: '部分缓解', cls: 'pr' },
  'SD': { label: '疾病稳定', cls: 'sd' },
  'PD': { label: '疾病进展', cls: 'pd' },
  'NE': { label: '无法评估', cls: 'ne' },
  'Non-CR/Non-PD': { label: '非CR/非PD', cls: 'ncnp' },
  '不适用（NA）': { label: '不适用(NA)', cls: 'na' },
  '不适用': { label: '不适用(NA)', cls: 'na' }
}
const statusLabel = (s) => STATUS_META[s]?.label || s
const statusCardClass = (s) => STATUS_META[s]?.cls || 'ne'

const targetStatusCounts = computed(() => statistics.value?.target_status_counts || {})
const nonTargetStatusCounts = computed(() => statistics.value?.non_target_status_counts || {})
const newLesionCount = computed(() => statistics.value?.new_lesion_count || 0)
const totalAssessments = computed(() => statistics.value?.total_assessments || 0)

// 病灶评估分布切换：同一水平位置，默认展示靶病灶评估分布
const selectedDist = ref('target')
const distributionTabs = [
  { key: 'target', label: '靶病灶评估分布' },
  { key: 'nonTarget', label: '非靶病灶评估分布' },
  { key: 'new', label: '新病灶分布' }
]

const assessmentTable = computed(() => statistics.value?.assessment_table || [])

const pagedAssessmentTable = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return assessmentTable.value.slice(start, start + pageSize.value)
})

const renderTrendChart = () => {
  if (!trendChartRef.value || !trendData.value?.historical_data?.length) return
  if (trendChart) trendChart.dispose()
  trendChart = echarts.init(trendChartRef.value)

  const history = [...trendData.value.historical_data].sort((a, b) => a.cycle_number - b.cycle_number)
  const xData = history.map(h => {
    if (h.cycle_number) return `周期${h.cycle_number}`
    const d = h.assessment_date || h.date
    if (d) return String(d).split('T')[0]
    return `周期${h.cycle_number || '-'}`
  })
  const statusData = history.map(h => getStatusText(h.overall_status))
  const currentSld = history.map(h => (h.current_sld ?? null))
  const changePct = history.map(h => (h.change_percent ?? 0))
  // 各周期基线 SLD（每期可能不同，取该期 baseline_sld）
  const baselinePerCycle = history.map(h => h.baseline_sld ?? null)
  // 基线 SLD 固定参照（取首期 baseline_sld，通常各期一致）
  const baselineRef = history.length ? (history[0].baseline_sld ?? null) : null
  const hasSld = currentSld.some(v => v !== null)

  const series = []
  // 主线：各周期当前 SLD（准确反映真实测量）
  if (hasSld) {
    series.push({
      name: '当前SLD(mm)',
      type: 'line',
      yAxisIndex: 0,
      data: currentSld,
      smooth: true,
      symbolSize: 8,
      lineStyle: { color: '#409eff', width: 3 },
      itemStyle: { color: '#409eff' },
      // 基线 SLD 固定参照线
      markLine: baselineRef != null ? {
        silent: true,
        symbol: 'none',
        lineStyle: { color: '#909399', type: 'dashed', width: 2 },
        label: { formatter: '基线SLD ' + Number(baselineRef).toFixed(1) + 'mm', position: 'insideEndTop' },
        data: [{ yAxis: baselineRef }]
      } : undefined
    })
  }
  // 辅线：变化率(%)（智能趋势指标 + PR/PD 阈值）
  series.push({
    name: '变化率(%)',
    type: 'line',
    yAxisIndex: hasSld ? 1 : 0,
    data: changePct,
    smooth: true,
    symbolSize: 6,
    lineStyle: { color: '#e6a23c', width: 2, type: 'dashed' },
    itemStyle: { color: '#e6a23c' },
    markLine: {
      silent: true,
      data: [
        { yAxis: 20, lineStyle: { color: '#f56c6c', type: 'dashed' }, label: { formatter: 'PD阈值(+20%)', position: 'insideEndTop' } },
        { yAxis: -30, lineStyle: { color: '#67c23a', type: 'dashed' }, label: { formatter: 'PR阈值(-30%)', position: 'insideEndTop' } }
      ]
    }
  })

  // 横坐标标签策略：标签较多或较长时旋转并加大底部留白，避免被裁切/重叠
  const maxLabelLen = Math.max(...xData.map(l => String(l).length), 0)
  const needRotate = xData.length > 6 || maxLabelLen > 6

  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const idx = params[0].dataIndex
        let html = `<strong>${xData[idx]}</strong><br/>`
        params.forEach(p => {
          const val = p.value
          if (val !== null && val !== undefined) {
            const suffix = p.seriesName.includes('SLD') ? 'mm' : '%'
            html += `${p.marker} ${p.seriesName}: <b>${Number(val).toFixed(1)}</b>${suffix}<br/>`
          }
        })
        // 基线 SLD（该周期的基线值）
        const bl = baselinePerCycle[idx]
        if (bl != null) {
          html += `─────────<br/>基线 SLD: <b>${Number(bl).toFixed(1)}</b> mm`
        }
        html += `<br/>总体疗效: ${statusData[idx]}`
        return html
      }
    },
    legend: { data: series.map(s => s.name), top: 5 },
    grid: {
      left: 64,
      right: hasSld ? 64 : 24,
      top: 56,
      // 底部留白动态计算：旋转标签按长度估算纵向占用，未旋转按单行估算，
      // containLabel 兜底确保不裁切；避免固定留白造成过多空白
      bottom: needRotate
        ? Math.min(Math.max(40, Math.round(maxLabelLen * 3.4) + 12), 78)
        : (maxLabelLen > 4 ? 34 : 28),
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: xData,
      boundaryGap: true,
      axisLabel: {
        interval: 0,
        rotate: needRotate ? 30 : 0,
        align: needRotate ? 'right' : 'center',
        verticalAlign: needRotate ? 'middle' : 'top',
        fontSize: 12,
        color: '#606266',
        hideOverlap: false
      },
      axisTick: { alignWithLabel: true }
    },
    yAxis: hasSld
      ? [
          { type: 'value', name: 'SLD(mm)' },
          { type: 'value', name: '变化率(%)', position: 'right' }
        ]
      : [{ type: 'value', name: '变化率(%)' }],
    series: series
  })
}

const analyzeTrend = async () => {
  if (!selectedSubjectId.value) {
    ElMessage.warning('请先选择受试者')
    return
  }
  trendLoading.value = true
  try {
    trendData.value = await analysisApi.getTrend(selectedSubjectId.value, state.currentBatchId || undefined)
    await nextTick()
    renderTrendChart()
  } catch (e) {
    console.error(e)
    ElMessage.error('趋势分析失败')
  } finally {
    trendLoading.value = false
  }
}

const getTrendText = (t) => ({ improving: '改善中', worsening: '恶化中', stable: '稳定' }[t] || t)
const getTrendClass = (t) => ({ improving: 'trend-good', worsening: 'trend-bad', stable: 'trend-normal' }[t] || '')

const goToDistribution = (status) => {
  router.push({ path: `/stat-detail/${status}`, query: { batch: state.currentBatchId } })
}

onMounted(async () => {
  // 默认展示当前（最新）批次的评估结果
  await loadBatches()
  loadData()
  window.addEventListener('resize', handleResize)
})

onActivated(() => {
  // keep-alive 重新激活时刷新数据并重绘图表
  loadData()
  if (trendData.value) {
    nextTick(() => renderTrendChart())
  }
})

// 导入新数据 / 批次刷新后重新加载
watch(() => state.version, () => {
  loadData()
  if (trendData.value) nextTick(() => renderTrendChart())
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (trendChart) trendChart.dispose()
})

const handleResize = () => {
  trendChart?.resize()
}

// ========== 受试者明细页跳转 ==========
const goToSubjects = () => {
  router.push({ path: '/analysis/subjects', query: { batch: state.currentBatchId } })
}

// ========== 弹窗：ORR / DCR 详情 ==========
const showRateDialog = ref(false)
const rateDialogType = ref('') // 'ORR' | 'DCR'
const ratePage = ref(1)
const ratePageSize = ref(10)
const rateDialogTitle = computed(() => rateDialogType.value + ' 详细说明')

// ORR/DCR 分子分母计算
const orrNumerator = computed(() => {
  if (!statistics.value) return 0
  const table = assessmentTable.value
  // 每个受试者取最新一次评估的 overall_status
  const latestPerSubject = getLatestOverallPerSubject()
  let n = 0
  latestPerSubject.forEach(s => { if (s.status === 'CR' || s.status === 'PR') n++ })
  return n
})
const dcrNumerator = computed(() => {
  if (!statistics.value) return 0
  const latestPerSubject = getLatestOverallPerSubject()
  let n = 0
  latestPerSubject.forEach(s => { if (['CR', 'PR', 'SD'].includes(s.status)) n++ })
  return n
})
const orrDenominator = computed(() => getLatestOverallPerSubject().length)
const dcrDenominator = computed(() => getLatestOverallPerSubject().length)

// 每个受试者的最新 overall_status（去重）
const getLatestOverallPerSubject = () => {
  const table = assessmentTable.value
  const map = new Map() // subject_db_id -> row with latest date
  table.forEach(r => {
    if (!r.subject_db_id) return
    const existing = map.get(r.subject_db_id)
    if (!existing || (r.assessment_date || '') > (existing.assessment_date || '')) {
      map.set(r.subject_db_id, r)
    }
  })
  // 返回 { subject_db_id, status }
  return Array.from(map.values()).map(r => ({
    subject_db_id: r.subject_db_id,
    subject_id: r.subject_id,
    status: r.overall_status || 'NE',
    target_status: r.target_status,
    change_percent: r.change_percent,
    overall_reason: r.overall_reason
  }))
}

const rateSubjectRows = computed(() => {
  if (!statistics.value) return []
  const all = getLatestOverallPerSubject()
  if (rateDialogType.value === 'ORR') {
    return all.filter(s => s.status === 'CR' || s.status === 'PR')
  } else {
    return all.filter(s => ['CR', 'PR', 'SD'].includes(s.status))
  }
})
const pagedRateRows = computed(() => {
  const start = (ratePage.value - 1) * ratePageSize.value
  return rateSubjectRows.value.slice(start, start + ratePageSize.value)
})

const openRateDialog = (type) => {
  rateDialogType.value = type
  ratePage.value = 1
  showRateDialog.value = true
}

// ========== 一键下发质疑（数据质疑清单） ==========
const showQueryDialog = ref(false)
const queryExporting = ref(false)

// 取每个受试者最新一次评估中「程序与人工不一致」的行，作为质疑清单
const queryRows = computed(() => {
  if (!statistics.value) return []
  const table = assessmentTable.value
  // 先按受试者取最新一条评估
  const map = new Map()
  table.forEach(r => {
    if (!r.subject_db_id) return
    const existing = map.get(r.subject_db_id)
    if (!existing || (r.assessment_date || '') > (existing.assessment_date || '')) {
      map.set(r.subject_db_id, r)
    }
  })
  // 只保留有人工数据且「总体疗效(程序) vs 总体疗效(人工)」不一致的行
  return Array.from(map.values())
    .filter(r => r.has_manual_data && r.overall_match === false)
    .map(r => ({
      subject_id: r.subject_id,
      visit: r.cycle_number ? `周期${r.cycle_number}` : (r.assessment_date ? String(r.assessment_date).split('T')[0] : '-'),
      overall_status: r.overall_status || 'NE',
      manual_overall_status: r.manual_overall_status || '',
      target_status: r.target_status || '',
      manual_target_status: r.manual_target_status || '',
      non_target_status: r.non_target_status || '',
      manual_non_target_status: r.manual_non_target_status || '',
      change_percent: r.change_percent,
      overall_reason: r.overall_reason || '-',
      overall_match: r.overall_match,
      target_match: r.target_match,
      non_target_match: r.non_target_match,
      has_new_lesion: r.has_new_lesion
    }))
})

const exportQueryExcel = async () => {
  if (!queryRows.value.length) {
    ElMessage.warning('暂无不一致数据，无需质疑')
    return
  }
  queryExporting.value = true
  try {
    const data = queryRows.value.map(r => ({
      '受试者编号': r.subject_id,
      '访视/周期': r.visit,
      '总体疗效(程序)': getStatusText(r.overall_status),
      '总体疗效(人工)': r.manual_overall_status ? getStatusText(r.manual_overall_status) : '-',
      '一致性(整体)': r.overall_match === false ? '✗ 不一致' : (r.overall_match === true ? '✓ 一致' : '-'),
      '靶病灶(程序)': r.target_status ? getStatusText(r.target_status) : '-',
      '靶病灶(人工)': r.manual_target_status ? getStatusText(r.manual_target_status) : '-',
      '非靶(程序)': r.non_target_status ? getStatusText(r.non_target_status) : '-',
      '非靶(人工)': r.manual_non_target_status ? getStatusText(r.manual_non_target_status) : '-',
      '变化率(%)': r.change_percent != null ? Number(r.change_percent).toFixed(1) : '-',
      '新病灶': r.has_new_lesion ? '有' : '无',
      '程序判定理由': r.overall_reason
    }))
    const fn = `数据质疑清单_不一致_${new Date().toISOString().split('T')[0]}.xlsx`
    const res = await exportToExcelWithPicker(data, fn, '数据质疑')
    if (res === 'cancelled') ElMessage.info('已取消导出')
    else if (res === 'empty') ElMessage.warning('暂无可导出的质疑数据')
    else ElMessage.success('已导出不一致数据 Excel（已选择保存位置）')
  } catch (e) {
    console.error(e)
    ElMessage.error('导出失败：' + e.message)
  } finally {
    queryExporting.value = false
  }
}
</script>

<style scoped>
.analysis-container {
  max-width: 1400px;
  margin: 0 auto;
  padding-bottom: 40px;
}
.page-header h2 {
  font-size: 28px;
  color: var(--text-primary);
  margin: 0;
  font-weight: 700;
  letter-spacing: -0.5px;
}
.header-actions {
  margin-left: auto;
}
.query-tip {
  font-size: 14px;
  color: var(--text-regular);
  line-height: 1.7;
  background: var(--bg-color);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  margin-bottom: var(--spacing-md);
}
.page-subtitle {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0;
  line-height: 1.6;
  align-self: center;
}
.loading {
  text-align: center;
  padding: 60px;
  color: var(--text-secondary);
}

/* 顶部核心指标 */
.stats-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}
.stat-card {
  background: var(--card-bg);
  padding: var(--spacing-xl);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  border: 1px solid var(--border-light);
}
.stat-card.highlight {
  background: var(--primary-gradient);
  color: white;
  border: none;
}
.stat-card.clickable {
  cursor: pointer;
  transition: all var(--transition-normal);
}
.stat-card.clickable:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
}
.stat-icon {
  font-size: 32px;
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-color);
  border-radius: var(--radius-lg);
}
.stat-card.highlight .stat-icon {
  background: rgba(255,255,255,0.2);
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
}
.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}
.stat-card.highlight .stat-label {
  color: rgba(255,255,255,0.85);
}

/* 评估结果分布 */
.distribution-section {
  background: var(--card-bg);
  padding: var(--spacing-xl);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  margin-bottom: var(--spacing-lg);
  border: 1px solid var(--border-light);
}
.distribution-section h3 {
  font-size: 18px;
  color: var(--text-primary);
  margin-bottom: var(--spacing-md);
  font-weight: 600;
}

/* 病灶评估分布切换标签（同一水平位置） */
.distribution-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: var(--spacing-md);
  flex-wrap: wrap;
}
.dist-tab {
  padding: 9px 20px;
  border: 1px solid var(--border-light);
  background: var(--bg-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 14px;
  color: var(--text-regular);
  transition: all var(--transition-normal);
}
.dist-tab:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}
.dist-tab.active {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: #fff;
  font-weight: 600;
}
.dist-panel {
  margin-top: var(--spacing-sm);
}
.distribution-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: var(--spacing-lg);
}
.distribution-card {
  background: var(--card-bg);
  padding: var(--spacing-xl);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  text-align: center;
  border-top: 4px solid var(--info-color);
  transition: all var(--transition-normal);
  border: 1px solid var(--border-light);
}
.distribution-card.clickable {
  cursor: pointer;
}
.distribution-card.clickable:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
}
.distribution-card.cr { border-top-color: var(--success-color); }
.distribution-card.pr { border-top-color: var(--primary-color); }
.distribution-card.sd { border-top-color: var(--warning-color); }
.distribution-card.ncnp { border-top-color: #9ca3af; }
.distribution-card.pd { border-top-color: var(--danger-color); }
.distribution-card.ne { border-top-color: var(--info-color); }
.distribution-card.na { border-top-color: #c0c4cc; }

.dist-sub {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-secondary);
}
.distribution-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 6px;
}
.distribution-label {
  font-size: 13px;
  color: var(--text-regular);
}

/* 趋势分析 */
.trend-section {
  background: var(--card-bg);
  padding: var(--spacing-xl);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  margin-bottom: var(--spacing-lg);
  border: 1px solid var(--border-light);
}
.trend-section h3 {
  font-size: 18px;
  margin-bottom: 4px;
  color: var(--text-primary);
  font-weight: 600;
}
.trend-desc {
  color: var(--text-secondary);
  font-size: 13px;
  margin-bottom: var(--spacing-md);
}
.trend-search {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
  align-items: center;
}
.trend-search .el-select {
  width: 300px;
}
.trend-subject-info {
  margin-bottom: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--primary-light);
  border-radius: var(--radius-md);
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
}
.trend-subject-id {
  font-weight: 600;
  font-size: 18px;
  color: var(--text-primary);
}
.trend-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}
.trend-card {
  background: var(--bg-color);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
}
.trend-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.trend-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}
.prediction-detail {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 6px;
}
.no-prediction {
  color: var(--text-placeholder);
}
.trend-good { color: var(--success-color); }
.trend-bad { color: var(--danger-color); }
.trend-normal { color: var(--warning-color); }
.trend-chart-wrapper {
  margin-bottom: var(--spacing-lg);
}
.trend-chart-wrapper h4 {
  font-size: 15px;
  color: var(--text-primary);
  margin-bottom: var(--spacing-md);
  font-weight: 500;
}
.trend-chart {
  height: 360px;
  background: var(--bg-color);
  border-radius: var(--radius-md);
}

/* RECIST 标准分析 */
.recist-analysis {
  background: var(--primary-light);
  border: 1px solid #d6e4ff;
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}
.recist-analysis h4 {
  font-size: 15px;
  color: var(--text-primary);
  margin-bottom: var(--spacing-md);
  font-weight: 500;
}
.recist-analysis-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.recist-analysis-item {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.recist-icon {
  font-size: 16px;
  flex-shrink: 0;
}
.recist-text {
  font-size: 14px;
  color: var(--text-regular);
  line-height: 1.6;
}

.recommendations, .anomalies {
  margin-top: var(--spacing-lg);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--border-light);
}
.recommendations h4, .anomalies h4 {
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 500;
}
.recommendations ul {
  list-style: none;
  padding: 0;
}
.recommendations li {
  padding: 8px 0;
  color: var(--text-regular);
  line-height: 1.6;
}

/* 详细数据表格 */
.detail-section {
  background: var(--card-bg);
  padding: var(--spacing-xl);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-light);
}
.detail-section h3 {
  font-size: 18px;
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
  font-weight: 600;
}

/* 多行表头 */
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

/* 程序判定理由换行 */
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
.arrow {
  color: #909399;
  font-size: 13px;
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
.badge.auto { opacity: 1; }
.badge.human { opacity: 0.85; }
.badge-cr { background: #67c23a; }
.badge-pr { background: #409eff; }
.badge-sd { background: #e6a23c; }
.badge-pd { background: #f56c6c; }
.badge-ne { background: #909399; }
.badge-ncnp { background: #9ca3af; }
.badge-na { background: #c0c4cc; }
.no-data {
  color: #c0c4cc;
  font-size: 12px;
}
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}

/* ===== 弹窗通用样式 ===== */
.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.dialog-header span {
  font-size: 15px;
  font-weight: 600;
}

/* ===== ORR / DCR 详情弹窗 ===== */
.rate-detail {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}
.rate-concept, .rate-calc, .rate-subjects {
  background: var(--bg-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  border: 1px solid var(--border-light);
}
.rate-concept h4, .rate-calc h4, .rate-subjects h4 {
  margin: 0 0 var(--spacing-sm) 0;
  color: var(--text-primary);
  font-size: 15px;
}
.concept-text {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-regular);
}
.concept-text p { margin: 4px 0; }
.concept-text ul {
  margin: 8px 0;
  padding-left: 20px;
}
.concept-text li { margin-bottom: 4px; }

.calc-formula {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 15px;
  padding: 12px 16px;
  background: #fff;
  border-radius: var(--radius-md);
  border: 1px dashed var(--primary-color);
}
.formula-label { font-weight: 600; white-space: nowrap; }
.formula-expr { color: var(--text-secondary); }
.formula-eq { color: #909399; }
.formula-num, .formula-result { color: var(--primary-color); font-size: 18px; }
.formula-den { color: var(--text-primary); font-weight: 500; }
.formula-div { color: #909399; }

/* Tooltip 内容 */
.orr-tooltip, .dcr-tooltip {
  font-size: 13px;
  line-height: 1.7;
}
.tip-explain {
  font-size: 12px;
  opacity: 0.85;
}

/* Mini badge (用于弹窗表格内) */
.mini-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  color: white;
}

@media (max-width: 1200px) {
  .stats-section { grid-template-columns: repeat(2, 1fr); }
  .distribution-grid { grid-template-columns: repeat(3, 1fr); }
  .trend-cards { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 768px) {
  .distribution-grid { grid-template-columns: repeat(2, 1fr); }
  .trend-cards { grid-template-columns: 1fr; }
}
.flag-ok { color: #67c23a; font-weight: 600; }
.flag-bad { color: #f56c6c; font-weight: 600; }
.query-row { background-color: #fef0f0; }
.text-muted { color: #909399; }
</style>
