<template>
  <div class="subjects-container">
    <div class="page-header">
      <div class="header-left">
        <h2>👥 受试者管理</h2>
        <p class="subtitle">管理受试者基本信息和评估记录</p>
      </div>
      <el-button type="primary" @click="showAddDialog = true" size="large">
        <el-icon><Plus /></el-icon>
        添加受试者
      </el-button>
    </div>

    <div class="search-bar">
      <el-select v-model="searchQuery" placeholder="输入或选择受试者编号搜索" filterable clearable style="width: 320px" @clear="searchQuery = ''">
        <el-option v-for="opt in subjectOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
      </el-select>
      <div class="search-stats">
        共 {{ filteredSubjects.length }} 位受试者
      </div>
    </div>

    <div v-if="loading" class="loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <div v-else class="table-container">
      <el-table :data="pagedSubjects" border stripe size="small" style="width: 100%">
        <el-table-column prop="subject_id" label="受试者编号" width="130" align="center">
          <template #default="scope">
            <span class="subject-id-link" @click="goToConsole(scope.row.id)">{{ scope.row.subject_id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="综合评估" min-width="220" align="center">
          <template #default="scope">
            <div class="overall-eval">
              <div class="eval-row">
                <span class="eval-tag">程序</span>
                <span v-if="latestProgramOverall(scope.row)" class="badge" :class="badgeClass(shortStatus(latestProgramOverall(scope.row)))">{{ shortStatus(latestProgramOverall(scope.row)) }}</span>
                <span v-else class="text-muted">-</span>
              </div>
              <div class="eval-row">
                <span class="eval-tag eval-manual">人工</span>
                <span v-if="latestManualOverall(scope.row)" class="badge" :class="badgeClass(shortStatus(latestManualOverall(scope.row)))">{{ shortStatus(latestManualOverall(scope.row)) }}</span>
                <span v-else class="text-muted">未录入</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="400" align="center" fixed="right">
          <template #default="scope">
            <div class="action-buttons">
              <el-button type="warning" size="small" @click="openAddLesion(scope.row)">新增病灶</el-button>
              <el-button type="primary" size="small" @click="openSubjectEdit(scope.row)">编辑病灶</el-button>
              <el-button type="success" size="small" @click="goToAssessment(scope.row.id)">病灶评估</el-button>
              <el-button type="info" size="small" @click="goToReport(scope.row.id)">报告</el-button>
              <el-button type="danger" size="small" @click="deleteSubject(scope.row.id)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-if="filteredSubjects.length > pageSize" class="pager" background layout="total, sizes, prev, pager, next" :total="filteredSubjects.length" :page-size="pageSize" :page-sizes="[10, 20, 50, 100]" v-model:current-page="page" @size-change="(s) => { pageSize = s; page = 1 }" />
    </div>

    <el-dialog v-model="showAddDialog" title="添加受试者" width="420px" class="add-subject-dialog">
      <el-form :model="newSubject" label-width="100px">
        <el-form-item label="受试者编号" required>
          <el-input v-model="newSubject.subject_id" placeholder="如：S001" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addSubject">确定</el-button>
      </template>
    </el-dialog>

    <!-- 受试者病灶编辑弹窗 -->
    <el-dialog v-model="subjectEdit.visible" title="编辑病灶信息" width="920px" destroy-on-close>
      <div v-if="subjectEdit.loading" class="loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
      <template v-else-if="subjectEdit.assessments.length">
        <div class="edit-toolbar">
          <div class="edit-toolbar-left">
            <label class="edit-label">检查时间点</label>
            <el-select v-model="subjectEdit.assessmentId" placeholder="选择检查时间点" style="width:260px">
              <el-option v-for="(a, i) in subjectEdit.assessments" :key="a.id" :label="a.visit_name || (`周期${i + 1} · ${formatDate(a.assessment_date)}`)" :value="a.id" />
            </el-select>
          </div>
          <span class="edit-tip">选择检查时间点后，下方为该点对应的靶病灶 / 非靶病灶 / 新病灶，可逐条编辑或删除</span>
        </div>

        <el-tabs v-model="subjectEdit.tab">
          <el-tab-pane label="靶病灶" name="target">
            <el-table :data="currentAssessment?.target_lesions || []" border size="small" empty-text="无靶病灶">
              <el-table-column prop="lesion_id" label="编号" width="90" />
              <el-table-column prop="organ" label="器官分类" width="100" />
              <el-table-column prop="location" label="具体部位" min-width="120" show-overflow-tooltip />
              <el-table-column label="基线径" width="90" align="center">
                <template #default="s">{{ fmtNum(s.row.baseline_size) }}</template>
              </el-table-column>
              <el-table-column label="当前径" width="90" align="center">
                <template #default="s">{{ fmtNum(s.row.current_size) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="140" align="center" fixed="right">
                <template #default="s">
                  <el-button size="small" type="primary" @click="openLesionEdit('target', s.row)">编辑</el-button>
                  <el-button size="small" type="danger" @click="deleteLesion('target', s.row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="非靶病灶" name="nonTarget">
            <el-table :data="currentAssessment?.non_target_lesions || []" border size="small" empty-text="无非靶病灶">
              <el-table-column prop="lesion_id" label="编号" width="90" />
              <el-table-column prop="organ" label="器官分类" width="100" />
              <el-table-column prop="location" label="具体部位" min-width="120" show-overflow-tooltip />
              <el-table-column prop="baseline_status" label="基线状态" width="100" align="center" />
              <el-table-column prop="status" label="当前状态" width="100" align="center" />
              <el-table-column label="操作" width="140" align="center" fixed="right">
                <template #default="s">
                  <el-button size="small" type="primary" @click="openLesionEdit('nonTarget', s.row)">编辑</el-button>
                  <el-button size="small" type="danger" @click="deleteLesion('nonTarget', s.row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="新病灶" name="newLesion">
            <el-table :data="currentAssessment?.new_lesions || []" border size="small" empty-text="无新病灶">
              <el-table-column prop="lesion_id" label="编号" width="90" />
              <el-table-column prop="organ" label="器官分类" width="100" />
              <el-table-column prop="location" label="具体部位" min-width="120" show-overflow-tooltip />
              <el-table-column prop="exam_date" label="检查日期" width="110" align="center" />
              <el-table-column label="操作" width="140" align="center" fixed="right">
                <template #default="s">
                  <el-button size="small" type="primary" @click="openLesionEdit('newLesion', s.row)">编辑</el-button>
                  <el-button size="small" type="danger" @click="deleteLesion('newLesion', s.row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </template>
      <el-empty v-else description="该受试者暂无评估记录" />
    </el-dialog>

    <!-- 单病灶编辑/新增弹窗 -->
    <LesionEditDialog
      v-model="lesionEdit.visible"
      :type="lesionEdit.type"
      :is-add="lesionEdit.isAdd"
      :lesion="lesionEdit.lesion"
      :assessment-id="lesionEdit.assessmentId"
      :is-baseline="lesionEditIsBaseline"
      @saved="onLesionSaved"
    />

    <!-- 新增病灶（新建检查时间点）弹窗 -->
    <AddCheckpointDialog
      v-model="addLesion.visible"
      :subject-id="addLesion.subjectId"
      :next-cycle="addLesion.nextCycle"
      :batch-id="state.currentBatchId"
      @saved="onAddLesionSaved"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onActivated, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Loading } from '@element-plus/icons-vue'
import { subjectApi, assessmentApi } from '../api'
import { useBatchStore } from '../store/batch'
import LesionEditDialog from '../components/LesionEditDialog.vue'
import AddCheckpointDialog from '../components/AddCheckpointDialog.vue'

const router = useRouter()
const { state } = useBatchStore()
const loading = ref(false)
const searchQuery = ref('')
const showAddDialog = ref(false)
const subjects = ref([])
const page = ref(1)
const pageSize = ref(10)
const newSubject = ref({
  subject_id: ''
})

const formatDate = (dt) => {
  if (!dt) return '-'
  return new Date(dt).toLocaleDateString('zh-CN')
}

const loadSubjects = async () => {
  loading.value = true
  try {
    subjects.value = await subjectApi.list({ limit: 1000, batch_id: state.currentBatchId })
  } catch (e) {
    console.error(e)
    ElMessage.error('加载受试者列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => { loadSubjects() })
onActivated(() => { loadSubjects() })

watch(() => state.version, () => { loadSubjects() })

const subjectOptions = computed(() => subjects.value.map(s => ({
  value: s.subject_id,
  label: s.subject_id
})))

const filteredSubjects = computed(() => {
  if (!searchQuery.value) return subjects.value
  const q = searchQuery.value.toLowerCase()
  return subjects.value.filter(s =>
    (s.subject_id || '').toLowerCase().includes(q)
  )
})

const pagedSubjects = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredSubjects.value.slice(start, start + pageSize.value)
})

watch(searchQuery, () => { page.value = 1 })

const goToAssessment = (id) => { router.push({ path: `/assessment/${id}`, query: { batch: state.currentBatchId } }) }
const goToReport = (id) => { router.push({ path: `/report/${id}`, query: { batch: state.currentBatchId } }) }
const goToConsole = (id) => { router.push({ path: `/subjects/${id}`, query: { batch: state.currentBatchId } }) }

// 列表页：取受试者最新评估与疗效标签（供「最新SOD」「疗效标签」列使用）
const latestAssessmentOf = (row) => {
  if (!row.assessments || !row.assessments.length) return null
  return [...row.assessments].sort((a, b) => (b.id || 0) - (a.id || 0))[0]
}

const latestOverallOf = (row) => {
  const a = latestAssessmentOf(row)
  if (!a) return null
  return a.manual_overall_status || a.overall_status || null
}

// 综合评估：程序（系统自动判定）与人工（EDC 录入）分别取最新评估对应字段
const latestProgramOverall = (row) => {
  const a = latestAssessmentOf(row)
  return a?.overall_status || null
}
const latestManualOverall = (row) => {
  const a = latestAssessmentOf(row)
  return a?.manual_overall_status || null
}

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

const latestSodTrendClass = (row) => {
  const a = latestAssessmentOf(row)
  if (!a || a.change_percent == null) return ''
  const p = a.change_percent
  if (p <= -30) return 'sod-down'
  if (p >= 20) return 'sod-up'
  return 'sod-flat'
}

const deleteSubject = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除该受试者吗？', '提示', { type: 'warning' })
    await subjectApi.delete(id)
    ElMessage.success('删除成功')
    loadSubjects()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const addSubject = async () => {
  if (!newSubject.value.subject_id) {
    ElMessage.warning('请填写受试者编号')
    return
  }
  try {
    // 不收集姓名，入库时姓名自动等于受试者编号
    await subjectApi.create({
      ...newSubject.value,
      name: newSubject.value.subject_id,
      batch_id: state.currentBatchId
    })
    ElMessage.success('添加成功')
    showAddDialog.value = false
    newSubject.value = { subject_id: '' }
    loadSubjects()
  } catch (e) {
    ElMessage.error('添加失败：' + (e.response?.data?.detail || e.message))
  }
}

// ========== 受试者病灶编辑 ==========
const subjectEdit = reactive({
  visible: false,
  loading: false,
  subjectId: null,
  assessments: [],
  assessmentId: null,
  tab: 'target'
})

const lesionEdit = reactive({
  visible: false,
  type: '',          // 'target' | 'nonTarget' | 'newLesion'
  isAdd: false,      // true=新增模式, false=编辑模式
  lesion: {},
  assessmentId: null
})

// ========== 新增病灶（新建检查时间点）弹窗 ==========
const addLesion = reactive({
  visible: false,
  subjectId: null,
  nextCycle: 1
})

const fmtNum = (v) => {
  if (v === null || v === undefined || v === '') return '-'
  return v
}

const currentAssessment = computed(() =>
  subjectEdit.assessments.find(a => a.id === subjectEdit.assessmentId) || null
)

// 基线期 = 评估的 cycle_number === 1（真正的基线，而非“日期排序第一条/唯一一条”）。
// 之前用“日期升序第一条”判定，会导致只有一条随访评估(cycle>1)的受试者被误判为基线，
// 编辑弹窗里“当前/随访数据”被 v-if 隐藏，出现“只能编辑基线、不能编辑当前”的问题。
const lesionEditIsBaseline = computed(() => {
  if (!subjectEdit.assessments.length) return false
  const a = subjectEdit.assessments.find(x => x.id === subjectEdit.assessmentId)
  return !a || a.cycle_number === 1
})

const openSubjectEdit = async (row) => {
  subjectEdit.visible = true
  subjectEdit.loading = true
  subjectEdit.subjectId = row.id
  subjectEdit.assessments = []
  subjectEdit.assessmentId = null
  try {
    const detail = await subjectApi.get(row.id, { batch_id: state.currentBatchId })
    const list = (detail.assessments || []).slice().sort(
      (a, b) => new Date(a.assessment_date) - new Date(b.assessment_date)
    )
    subjectEdit.assessments = list
    // 默认选中最新（日期最大）的评估时间点
    subjectEdit.assessmentId = list.length ? list[list.length - 1].id : null
  } catch (e) {
    ElMessage.error('加载病灶数据失败：' + (e.response?.data?.detail || e.message))
  } finally {
    subjectEdit.loading = false
  }
}

const openLesionEdit = (type, row) => {
  lesionEdit.type = type
  lesionEdit.isAdd = false
  lesionEdit.lesion = row
  lesionEdit.assessmentId = subjectEdit.assessmentId
  lesionEdit.visible = true
}

// 新增病灶：新建一个检查时间点（新评估）。先取该受试者详情以推算下一周期编号。
const openAddLesion = async (row) => {
  try {
    const detail = await subjectApi.get(row.id, { batch_id: state.currentBatchId })
    const maxCycle = (detail.assessments || []).reduce(
      (m, a) => Math.max(m, a.cycle_number || 0), 0
    )
    addLesion.subjectId = row.id
    addLesion.nextCycle = maxCycle + 1
    addLesion.visible = true
  } catch (e) {
    ElMessage.error('加载受试者详情失败：' + (e.response?.data?.detail || e.message))
  }
}

const deleteLesion = async (type, row) => {
  try {
    await ElMessageBox.confirm(`确定删除该${type === 'target' ? '靶' : type === 'nonTarget' ? '非靶' : '新'}病灶（编号 ${row.lesion_id || row.id}）吗？`, '提示', { type: 'warning' })
    await assessmentApi.deleteLesion(type, subjectEdit.assessmentId, row.id)
    ElMessage.success('病灶已删除')
    await onLesionSaved()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  }
}

const openLesionAdd = (type) => {
  lesionEdit.type = type
  lesionEdit.isAdd = true
  lesionEdit.lesion = {}   // 空对象=新增模式
  lesionEdit.assessmentId = subjectEdit.assessmentId
  lesionEdit.visible = true
}

const onLesionSaved = async () => {
  // 重新拉取该受试者最新病灶数据，刷新表格
  try {
    const detail = await subjectApi.get(subjectEdit.subjectId, { batch_id: state.currentBatchId })
    const list = (detail.assessments || []).slice().sort(
      (a, b) => new Date(a.assessment_date) - new Date(b.assessment_date)
    )
    subjectEdit.assessments = list
    if (!subjectEdit.assessments.some(a => a.id === subjectEdit.assessmentId)) {
      subjectEdit.assessmentId = list.length ? list[list.length - 1].id : null
    }
  } catch (e) {
    console.error(e)
  }
}

const onAddLesionSaved = () => {
  // 新增检查时间点成功，刷新受试者列表 + 已打开的受试者编辑弹窗
  loadSubjects()
  if (subjectEdit.visible && subjectEdit.subjectId) {
    refreshSubjectEdit(subjectEdit.subjectId)
  }
}

// 重新拉取指定受试者的评估列表（保持编辑弹窗内时间点最新）
const refreshSubjectEdit = async (subjectId) => {
  try {
    const detail = await subjectApi.get(subjectId, { batch_id: state.currentBatchId })
    const list = (detail.assessments || []).slice().sort(
      (a, b) => new Date(a.assessment_date) - new Date(b.assessment_date)
    )
    subjectEdit.assessments = list
    // 若当前选中的时间点已不存在，切到最新
    if (!subjectEdit.assessments.some(a => a.id === subjectEdit.assessmentId)) {
      subjectEdit.assessmentId = list.length ? list[list.length - 1].id : null
    }
  } catch (e) {
    console.error(e)
  }
}
</script>

<style scoped>
.subjects-container {
  max-width: 1400px;
  margin: 0 auto;
  padding-bottom: 40px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-xl);
}

.header-left h2 {
  font-size: 28px;
  color: var(--text-primary);
  margin-bottom: 6px;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.subtitle {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0;
  line-height: 1.6;
}

.search-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.search-stats {
  font-size: 13px;
  color: var(--text-secondary);
}

.table-container {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: var(--spacing-xl);
  border: 1px solid var(--border-light);
}

.subject-id-link {
  color: var(--primary-color);
  font-weight: 500;
  cursor: pointer;
  transition: color var(--transition-fast);
}

.subject-id-link:hover {
  text-decoration: underline;
  color: var(--primary-dark);
}

.gender-male {
  color: var(--primary-color);
  font-weight: 500;
}

.gender-female {
  color: var(--danger-color);
  font-weight: 500;
}

.action-buttons {
  display: flex;
  gap: 6px;
  justify-content: center;
  flex-wrap: nowrap;
  white-space: nowrap;
}

/* 综合评估：程序 / 人工 两行，标签与结果之间留出间距，避免与结果「较劲」 */
.overall-eval {
  display: inline-flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
  padding: 2px 0;
}

.eval-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.eval-tag {
  flex: 0 0 auto;
  min-width: 36px;
  padding: 1px 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-secondary, #f4f4f5);
  border-radius: 4px;
  text-align: center;
}

.eval-tag.eval-manual {
  color: #b88230;
  background: #fdf6ec;
}

.text-muted {
  color: var(--text-secondary);
  font-size: 13px;
}

/* 综合评估列与右侧固定「操作」列之间补一条分割线 */
:deep(.el-table .el-table-fixed-column--right) {
  border-left: 1px solid var(--el-table-border-color, #ebeef5);
}

/* 列表页「疗效标签」状态徽章 */
.badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.6;
}
.badge-cr { background: #67c23a; }
.badge-pr { background: #409eff; }
.badge-sd { background: #e6a23c; }
.badge-pd { background: #f5f7fa; color: #f56c6c; border: 1px solid #f56c6c; }
.badge-ne { background: #909399; }
.badge-ncnp { background: #9ca3af; }
.badge-na { background: #c0c4cc; }

/* 最新SOD 涨跌着色 */
.sod-down { color: #67c23a; font-weight: 600; }
.sod-up { color: #f56c6c; font-weight: 600; }
.sod-flat { color: #e6a23c; font-weight: 600; }

.edit-toolbar {
  display: flex;
  align-items: center;
  margin-bottom: var(--spacing-md);
  padding-top: 4px;
}

.edit-toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.edit-label {
  font-size: 14px;
  color: var(--text-primary);
  white-space: nowrap;
}

.edit-tip {
  font-size: 13px;
  color: var(--text-secondary);
  margin-left: 16px;
  white-space: nowrap;
}

.pager {
  margin-top: var(--spacing-md);
  justify-content: flex-end;
}

.loading {
  text-align: center;
  padding: 80px;
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

@media (max-width: 768px) {
  .page-header { flex-direction: column; gap: 16px; }
  .search-bar { flex-direction: column; gap: 12px; }
}
</style>

<!-- 非 scoped：el-dialog 被 teleport 到 body，scoped :deep 无法命中 -->
<style>
.add-subject-dialog .el-dialog__header {
  padding-bottom: 16px;
}

.add-subject-dialog .el-dialog__body {
  padding-top: 24px;
}
</style>