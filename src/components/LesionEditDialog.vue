<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="(v) => emit('update:modelValue', v)"
    :title="title"
    width="1100px"
    class="lesion-edit-dialog"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <el-form v-if="form" :model="form" label-width="170px" size="default">
      <!-- 基线期提示 -->
      <el-alert
        v-if="isBaseline"
        type="info"
        :closable="false"
        show-icon
        class="baseline-tip"
        title="基线期（Baseline）"
        description="基线期仅记录基线测量数据，不录入当前/随访径线与疗效评价。"
      />
      <!-- 随访期新增靶/非靶提示 -->
      <el-alert
        v-if="!isBaseline && isAdd && (type === 'target' || type === 'nonTarget')"
        type="warning"
        :closable="false"
        show-icon
        class="baseline-tip"
        title="随访期新增靶/非靶病灶"
        description="编号须与基线期一致（同一病灶的纵向追踪）；若为本次新发肿瘤，请关闭本弹窗，改在「新病灶」页签中新增。"
      />

      <!-- ========== 靶病灶 ========== -->
      <template v-if="type === 'target'">
        <el-row :gutter="16">
          <el-col :span="7">
            <el-form-item label="编号（EDC）" required>
              <el-input v-model="form.lesion_id" placeholder="如 T1" />
            </el-form-item>
          </el-col>
          <el-col :span="10">
            <el-form-item label="器官（分类）" required>
              <el-select
                v-model="form.organ"
                placeholder="选择器官"
                filterable
                allow-create
                style="width:100%"
              >
                <el-option v-for="o in ORGAN_OPTIONS" :key="o" :label="o" :value="o" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="7">
            <el-form-item label="是否为淋巴结">
              <el-switch v-model="form.is_lymph_node" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="具体部位">
              <el-input v-model="form.location" placeholder="如: 肝右叶" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="器官具体描述">
              <el-input v-model="form.description" placeholder="如: 肝右叶" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 基线数据 -->
        <el-divider content-position="left">基线数据</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="基线检查日期" required>
              <el-date-picker v-model="form.exam_date" type="date" placeholder="基线日期" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="基线检查方法" required>
              <el-input v-model="form.exam_method" placeholder="如: 增强CT" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="diameterLabel" required>
              <el-input-number v-model="form.baseline_size" :min="0" :precision="1" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="靶病灶直径和(mm)">
              <el-input-number v-model="form.baseline_sum_diameter" :min="0" :precision="1" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="备注">
              <el-input v-model="form.notes" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 当前/随访数据（新增基线期隐藏；编辑模式始终显示，便于修正当前测量） -->
        <template v-if="!isBaseline || !isAdd">
        <el-divider content-position="left">当前/随访数据</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="当前检查日期" required>
              <el-date-picker v-model="form.current_exam_date" type="date" placeholder="当前日期" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="当前检查方法" required>
              <el-input v-model="form.current_exam_method" placeholder="如: 增强CT" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="'当前' + diameterLabel" required>
              <el-input-number v-model="form.current_size" :min="0" :precision="1" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="靶病灶直径和(mm)">
              <el-input-number v-model="form.sum_diameter" :min="0" :precision="1" controls-position="right" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="备注">
              <el-input v-model="form.notes" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
        </el-row>
        </template>
      </template>

      <!-- ========== 非靶病灶 ========== -->
      <template v-else-if="type === 'nonTarget'">
        <el-row :gutter="16">
          <el-col :span="6">
            <el-form-item label="编号（EDC）" required>
              <el-input v-model="form.lesion_id" placeholder="如 NT1" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="器官（分类）" required>
              <el-select
                v-model="form.organ"
                placeholder="选择器官"
                filterable
                allow-create
                style="width:100%"
              >
                <el-option v-for="o in ORGAN_OPTIONS" :key="o" :label="o" :value="o" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="是否为淋巴结" label-width="100px">
              <el-switch v-model="form.is_lymph_node" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="具体部位" required>
              <el-input v-model="form.location" placeholder="如: 肝左右叶" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="24">
            <el-form-item label="器官具体描述" required label-width="150px">
              <el-input v-model="form.description" placeholder="如: 肝左右叶多处" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 状态 -->
        <el-divider content-position="left">状态</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="基线状态" required>
              <el-select v-model="form.baseline_status" placeholder="" style="width:100%">
                <el-option label="持续存在" value="持续存在" />
                <el-option label="消失" value="消失" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="当前状态" required>
              <el-select v-model="form.status" placeholder="" style="width:100%">
                <el-option label="消失" value="消失" />
                <el-option label="持续存在" value="持续存在" />
                <el-option label="进展" value="进展" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 基线检查信息 -->
        <el-divider content-position="left">基线检查信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="5">
            <el-form-item label="是否检查(基线)" required label-width="120px">
              <el-select v-model="form.baseline_is_checked" placeholder="" style="width:100%">
                <el-option label="是" :value="true" />
                <el-option label="否" :value="false" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="7">
            <el-form-item label="检查日期(基线)" required label-width="130px">
              <el-date-picker v-model="form.exam_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="检查方法(基线)" required label-width="140px">
              <el-input v-model="form.exam_method" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 当前检查信息（新增基线期隐藏；编辑模式始终显示） -->
        <template v-if="!isBaseline || !isAdd">
        <el-divider content-position="left">当前检查信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="5">
            <el-form-item label="是否检查(当前)" required label-width="125px">
              <el-select v-model="form.current_is_checked" placeholder="" style="width:100%">
                <el-option label="是" :value="true" />
                <el-option label="否" :value="false" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="7">
            <el-form-item label="检查日期(当前)" required label-width="135px">
              <el-date-picker v-model="form.current_exam_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="检查方法(当前)" required label-width="145px">
              <el-input v-model="form.current_exam_method" />
            </el-form-item>
          </el-col>
        </el-row>
        </template>

        <el-form-item label="备注" label-width="150px">
          <el-input v-model="form.notes" type="textarea" :rows="2" />
        </el-form-item>
      </template>

      <!-- ========== 新病灶 ========== -->
      <template v-else-if="type === 'newLesion'">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="编号（EDC）">
              <el-input v-model="form.lesion_id" placeholder="如 NL1" />
            </el-form-item>
          </el-col>
          <el-col :span="10">
            <el-form-item label="器官（分类）" required>
              <el-select
                v-model="form.organ"
                placeholder="选择器官"
                filterable
                allow-create
                style="width:100%"
              >
                <el-option v-for="o in ORGAN_OPTIONS" :key="o" :label="o" :value="o" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="是否为淋巴结">
              <el-switch v-model="form.is_lymph_node" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="具体部位" required>
              <el-input v-model="form.location" placeholder="如: 新发肺转移灶" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="器官具体描述">
              <el-input v-model="form.description" placeholder="如: 新发肺转移灶" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="检查日期" required>
              <el-date-picker v-model="form.exam_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="检查方法" required>
              <el-input v-model="form.exam_method" placeholder="如: 增强CT" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="其他检查方法">
              <el-input v-model="form.other_exam_method" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" />
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" @click="save" :loading="saving">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

// 标准 RECIST 1.1 器官分类（下拉枚举）
const ORGAN_OPTIONS = [
  '淋巴结', '肺', '肝', '骨', '脑', '肾上腺', '腹膜后', '盆腔', '乳腺', '皮下软组织', '其他'
]

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  type: { type: String, default: '' },        // 'target' | 'nonTarget' | 'newLesion'
  isAdd: { type: Boolean, default: false },   // true=新增模式
  lesion: { type: Object, default: () => ({}) },
  assessmentId: { type: [Number, null], default: null },
  isBaseline: { type: Boolean, default: false } // true=基线期：仅录基线测量
})
const emit = defineEmits(['update:modelValue', 'saved'])

const title = computed(() => {
  const prefix = props.isAdd ? '新增' : '编辑'
  return ({
    target: prefix + '靶病灶',
    nonTarget: prefix + '非靶病灶',
    newLesion: prefix + '新病灶'
  }[props.type] || (prefix + '病灶'))
})

// 直径标签：根据是否为淋巴结切换「最短直径」/「最长直径」
const diameterLabel = computed(() => {
  return form.value?.is_lymph_node ? '最短直径(mm)' : '最长直径(mm)'
})

const form = ref(null)
const saving = ref(false)

watch(
  () => [props.modelValue, props.lesion, props.isAdd],
  () => {
    if (props.modelValue) buildForm()
  },
  { immediate: true }
)

// 自动填充：location 变化时若 organ 为空则用 location 值填充
watch(
  () => form.value?.location,
  (val) => {
    if (form.value && val && !form.value.organ) {
      form.value.organ = val
    }
  }
)

function buildForm() {
  const r = props.lesion || {}
  if (props.type === 'target') {
    form.value = {
      name: r.name || '',
      location: r.location || '',
      organ: r.organ || '',
      is_lymph_node: !!(r.is_lymph_node),
      description: r.description || '',
      lesion_id: r.lesion_id || '',
      baseline_size: props.isAdd ? 0 : (r.baseline_size ?? r.baselineSize ?? 0),
      current_size: props.isAdd ? 0 : (r.current_size ?? r.currentSize ?? 0),
      size_unit: r.size_unit || 'mm',
      baseline_sum_diameter: props.isAdd ? 0 : (r.baseline_sum_diameter ?? 0),
      sum_diameter: props.isAdd ? 0 : (r.sum_diameter ?? 0),
      exam_date: r.exam_date || '',
      exam_method: r.exam_method || '',
      current_exam_date: r.current_exam_date || '',
      current_exam_method: r.current_exam_method || '',
      notes: r.notes || ''
    }
  } else if (props.type === 'nonTarget') {
    form.value = {
      name: r.name || '',
      location: r.location || '',
      organ: r.organ || '',
      is_lymph_node: !!(r.is_lymph_node),
      description: r.description || '',
      lesion_id: r.lesion_id || '',
      baseline_status: r.baseline_status ?? r.baselineStatus ?? '持续存在',
      status: r.status || '持续存在',
      baseline_is_checked: r.baseline_is_checked !== undefined ? r.baseline_is_checked : true,
      current_is_checked: r.current_is_checked !== undefined ? r.current_is_checked : true,
      exam_date: r.exam_date || '',
      exam_method: r.exam_method || '',
      current_exam_date: r.current_exam_date || '',
      current_exam_method: r.current_exam_method || '',
      notes: r.notes || ''
    }
  } else if (props.type === 'newLesion') {
    form.value = {
      name: r.name || '',
      location: r.location || '',
      organ: r.organ || '',
      is_lymph_node: !!(r.is_lymph_node),
      description: r.description || '',
      lesion_id: r.lesion_id || '',
      exam_date: r.exam_date || r.foundDate || '',
      exam_method: r.exam_method || '',
      other_exam_method: r.other_exam_method || '',
      notes: r.notes || ''
    }
  }
}

// 必填校验辅助
const isBlank = (v) => v === null || v === undefined || v === ''
const numBlank = (v) => v === null || v === undefined || v === '' || Number.isNaN(Number(v))

async function save() {
  const f = form.value
  if (props.type === 'target') {
    if (isBlank(f.organ)) { ElMessage.warning('请选择器官（分类）'); return }
    if (isBlank(f.exam_date)) { ElMessage.warning('请填写基线检查日期'); return }
    if (isBlank(f.exam_method)) { ElMessage.warning('请填写基线检查方法'); return }
    if (numBlank(f.baseline_size)) { ElMessage.warning('请填写基线' + diameterLabel.value); return }
    if (!props.isBaseline) {
      if (isBlank(f.current_exam_date)) { ElMessage.warning('请填写当前检查日期'); return }
      if (isBlank(f.current_exam_method)) { ElMessage.warning('请填写当前检查方法'); return }
      if (numBlank(f.current_size)) { ElMessage.warning('请填写当前' + diameterLabel.value); return }
    }
  } else if (props.type === 'nonTarget') {
    if (isBlank(f.lesion_id)) { ElMessage.warning('请填写编号（EDC）'); return }
    if (isBlank(f.organ)) { ElMessage.warning('请选择器官（分类）'); return }
    if (isBlank(f.location)) { ElMessage.warning('请填写具体部位'); return }
    if (isBlank(f.description)) { ElMessage.warning('请填写器官具体描述'); return }
    if (isBlank(f.baseline_status)) { ElMessage.warning('请选择基线状态'); return }
    if (isBlank(f.status)) { ElMessage.warning('请选择当前状态'); return }
    if (f.baseline_is_checked === undefined || f.baseline_is_checked === null) { ElMessage.warning('请选择是否检查(基线)'); return }
    if (isBlank(f.exam_date)) { ElMessage.warning('请填写检查日期(基线)'); return }
    if (isBlank(f.exam_method)) { ElMessage.warning('请填写检查方法(基线)'); return }
    if (!props.isBaseline) {
      if (f.current_is_checked === undefined || f.current_is_checked === null) { ElMessage.warning('请选择是否检查(当前)'); return }
      if (isBlank(f.current_exam_date)) { ElMessage.warning('请填写检查日期(当前)'); return }
      if (isBlank(f.current_exam_method)) { ElMessage.warning('请填写检查方法(当前)'); return }
    }
  } else if (props.type === 'newLesion') {
    if (isBlank(f.organ)) { ElMessage.warning('请选择器官（分类）'); return }
    if (isBlank(f.location)) { ElMessage.warning('请填写具体部位'); return }
    if (isBlank(f.exam_date)) { ElMessage.warning('请填写检查日期'); return }
    if (isBlank(f.exam_method)) { ElMessage.warning('请填写检查方法'); return }
  }

  saving.value = true
  try {
    if (props.isAdd) {
      const postMap = {
        target: `/api/assessments/${props.assessmentId}/target-lesions`,
        nonTarget: `/api/assessments/${props.assessmentId}/non-target-lesions`,
        newLesion: `/api/assessments/${props.assessmentId}/new-lesions`
      }
      await api.post(postMap[props.type], form.value)
      ElMessage.success('病灶已添加')
    } else {
      const putMap = {
        target: `/api/assessments/${props.assessmentId}/target-lesions/${props.lesion.id}`,
        nonTarget: `/api/assessments/${props.assessmentId}/non-target-lesions/${props.lesion.id}`,
        newLesion: `/api/assessments/${props.assessmentId}/new-lesions/${props.lesion.id}`
      }
      await api.put(putMap[props.type], form.value)
      ElMessage.success('病灶信息已更新')
    }
    emit('saved')
    emit('update:modelValue', false)
  } catch (e) {
    ElMessage.error('保存到服务器失败：' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}
</script>

<!-- 非 scoped：el-dialog 被 teleport 到 body，scoped 样式无法命中 -->
<style>
.lesion-edit-dialog .el-dialog__header {
  padding-bottom: 16px;
}

.lesion-edit-dialog .el-dialog__body {
  padding-top: 24px;
}

.lesion-edit-dialog .baseline-tip {
  margin-bottom: 16px;
}

.lesion-edit-dialog .el-form-item {
  margin-bottom: 18px;
}

.lesion-edit-dialog .el-divider__text {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
</style>
