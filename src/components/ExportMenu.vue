<template>
  <div class="export-menu">
    <el-tooltip
      content="导出 Excel：点击直接下载，并弹出窗口选择保存位置"
      placement="top"
    >
      <el-button size="small" type="primary" :loading="exporting" @click="onExcel">
        <el-icon class="exp-icon"><Document /></el-icon>
        <span>导出 Excel</span>
      </el-button>
    </el-tooltip>
    <el-tooltip
      content="导出 PDF：点击生成报表，并在打印对话框中选择“另存为 PDF”指定保存位置"
      placement="top"
    >
      <el-button size="small" @click="onPdf">
        <el-icon class="exp-icon"><Printer /></el-icon>
        <span>导出 PDF</span>
      </el-button>
    </el-tooltip>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Printer } from '@element-plus/icons-vue'
import {
  exportAssessmentsToExcelPicker,
  exportSubjectsToExcelPicker,
  exportAssessmentsToPDF,
  exportSubjectsToPDF
} from '../utils/export'

const props = defineProps({
  // 已扁平化的数据行（评估行或受试者分组行）
  rows: { type: Array, default: () => [] },
  // 'assessments' | 'subjects'
  type: { type: String, default: 'assessments' },
  // 文件名（不含扩展名）
  filename: { type: String, default: '数据' },
  // PDF 标题
  title: { type: String, default: '评估报告' },
  // PDF 副标题
  subtitle: { type: String, default: '' }
})

const exporting = ref(false)

const stamp = () => {
  const ts = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${ts.getFullYear()}${p(ts.getMonth() + 1)}${p(ts.getDate())}`
}

// 导出 Excel：优先让用户选择保存位置，点击直接下载
const onExcel = async () => {
  if (!props.rows || props.rows.length === 0) {
    ElMessage.warning('暂无数据可导出')
    return
  }
  exporting.value = true
  try {
    const fn = `${props.filename}_${stamp()}.xlsx`
    const res = props.type === 'subjects'
      ? await exportSubjectsToExcelPicker(props.rows, fn)
      : await exportAssessmentsToExcelPicker(props.rows, fn, '评估数据')
    if (res === 'cancelled') {
      ElMessage.info('已取消导出')
    } else {
      ElMessage.success(res === 'picker' ? '已导出 Excel（已选择保存位置）' : '已导出 Excel')
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('导出 Excel 失败')
  } finally {
    exporting.value = false
  }
}

// 导出 PDF：生成报表并在打印对话框中指定保存位置
const onPdf = () => {
  if (!props.rows || props.rows.length === 0) {
    ElMessage.warning('暂无数据可导出')
    return
  }
  if (props.type === 'subjects') {
    exportSubjectsToPDF(props.rows, props.subtitle || '受试者概览')
  } else {
    exportAssessmentsToPDF(props.title, props.rows, props.subtitle)
  }
  ElMessage.success('已生成 PDF（请在打印对话框中选择“另存为 PDF”并指定保存位置）')
}
</script>

<style scoped>
.export-menu {
  display: inline-flex;
  gap: 8px;
  align-items: center;
}
.exp-icon {
  margin-right: 4px;
  vertical-align: -2px;
}
</style>
