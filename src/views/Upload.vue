<template>
  <div class="upload-container">
    <div class="page-header">
      <div class="header-icon">📁</div>
      <div class="header-text">
        <h2>数据导入</h2>
        <p class="subtitle">上传 EDC 导出的 Excel 文件，系统自动完成 RECIST 1.1 评估并与人工结果比对</p>
      </div>
    </div>

    <div class="upload-section card-wrapper">
      <div
        class="upload-box"
        :class="{ dragging: isDragging, hasFile: uploadedFile }"
        @drop.prevent="handleDrop"
        @dragover.prevent="isDragging = true"
        @dragleave="isDragging = false"
        @click="triggerFileInput"
      >
        <div class="upload-icon-wrap">
          <div class="upload-icon">{{ uploadedFile ? '✅' : '📁' }}</div>
        </div>
        <p class="upload-title">{{ uploadedFile ? '文件已选择：' + uploadedFile.name : '拖拽Excel文件到此处，或点击选择文件' }}</p>
        <p class="upload-hint">支持 EDC 6-Sheet 格式（靶病灶/非靶病灶/新病灶/肿瘤评估）</p>
        <input
          type="file"
          ref="fileInputRef"
          accept=".xlsx,.xls"
          class="file-input"
          @change="handleFileSelect"
        />
      </div>

      <div v-if="uploadedFile" class="file-info">
        <div class="file-detail">
          <span class="file-name">{{ uploadedFile.name }}</span>
          <span class="file-size">{{ formatSize(uploadedFile.size) }}</span>
        </div>
        <button class="el-button el-button--danger el-button--small" @click.stop="clearFile">
          清除
        </button>
      </div>

      <div v-if="uploadedFile" class="import-action">
        <button
          class="el-button el-button--primary import-btn"
          size="large"
          @click="importFile"
          :disabled="isImporting"
        >
          <el-icon v-if="isImporting"><Loading /></el-icon>
          {{ isImporting ? '解析导入中...' : '解析并导入' }}
        </button>
        <p class="action-hint">导入后系统将自动进行 RECIST 1.1 评估</p>
      </div>
    </div>

    <div class="template-section card-wrapper">
      <div class="section-title">
        <h3>📋 导入模板说明</h3>
      </div>
      <p class="section-desc">请按照 EDC 6-Sheet 格式准备 Excel 文件：</p>
      <div class="template-grid">
        <div class="template-card">
          <div class="card-header">
            <span class="card-icon">🎯</span>
            <h4>Sheet 1: 靶病灶_基线</h4>
          </div>
          <ul>
            <li>受试者编号</li>
            <li>是否存在靶病灶</li>
            <li>病灶所在器官 / 具体描述</li>
            <li>最长直径</li>
          </ul>
        </div>
        <div class="template-card">
          <div class="card-header">
            <span class="card-icon">📏</span>
            <h4>Sheet 2: 靶病灶</h4>
          </div>
          <ul>
            <li>受试者编号</li>
            <li>表单集记录号</li>
            <li>表单集名称</li>
            <li>是否进行了靶病灶检查</li>
            <li>最长直径</li>
          </ul>
        </div>
        <div class="template-card">
          <div class="card-header">
            <span class="card-icon">📍</span>
            <h4>Sheet 3: 非靶病灶_基线</h4>
          </div>
          <ul>
            <li>受试者编号</li>
            <li>是否存在非靶病灶</li>
            <li>病灶所在器官</li>
          </ul>
        </div>
        <div class="template-card">
          <div class="card-header">
            <span class="card-icon">📌</span>
            <h4>Sheet 4: 非靶病灶</h4>
          </div>
          <ul>
            <li>受试者编号</li>
            <li>表单集记录号</li>
            <li>评估结果</li>
          </ul>
        </div>
        <div class="template-card">
          <div class="card-header">
            <span class="card-icon">✨</span>
            <h4>Sheet 5: 新病灶</h4>
          </div>
          <ul>
            <li>受试者编号</li>
            <li>表单集记录号</li>
            <li>是否有新病灶检出</li>
          </ul>
        </div>
        <div class="template-card">
          <div class="card-header">
            <span class="card-icon">📊</span>
            <h4>Sheet 6: 肿瘤评估</h4>
          </div>
          <ul>
            <li>受试者编号</li>
            <li>表单集记录号</li>
            <li>靶病灶评估 / 非靶病灶评估</li>
            <li>新病灶 / 总体疗效评估</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElLoading } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { dataApi } from '../api'
import { useBatchStore } from '../store/batch'

const router = useRouter()
const { state, loadBatches, setCurrentBatch, latestBatchId } = useBatchStore()
const isDragging = ref(false)
const uploadedFile = ref(null)
const isImporting = ref(false)
const fileInputRef = ref(null)

const triggerFileInput = () => {
  fileInputRef.value?.click()
}

const handleDrop = (e) => {
  isDragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) uploadedFile.value = file
}

const handleFileSelect = (e) => {
  const file = e.target.files[0]
  if (file) uploadedFile.value = file
}

const clearFile = () => {
  uploadedFile.value = null
}

// 导入成功后重置页面回到初始状态：
// 清空已选文件、复位导入按钮、清除文件选择框（input 的 value 也需清空才能再次选同一文件）
const resetToInitial = () => {
  uploadedFile.value = null
  isImporting.value = false
  isDragging.value = false
  if (fileInputRef.value) fileInputRef.value.value = ''
}

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const importFile = async () => {
  if (!uploadedFile.value) return
  isImporting.value = true
  try {
    const res = await dataApi.import(uploadedFile.value)
    ElMessage.success(`导入成功：${res.total_assessments} 条评估`)

    await loadBatches()
    if (state.batches.length) {
      setCurrentBatch(latestBatchId())
    }

    // 导入成功后先重置页面状态，再自动跳转首页
    resetToInitial()
    router.push('/')
  } catch (error) {
    console.error(error)
    ElMessage.error('导入失败：' + (error.response?.data?.detail || error.message))
  } finally {
    isImporting.value = false
  }
}
</script>

<style scoped>
.upload-container {
  max-width: 1200px;
  margin: 0 auto;
  padding-bottom: 40px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
  animation: slideIn 0.4s ease;
}

.header-icon {
  font-size: 44px;
}

.header-text h2 {
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

.card-wrapper {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-lg);
  animation: fadeIn 0.4s ease;
  border: 1px solid var(--border-light);
}

.upload-section {
  padding: 48px;
}

.upload-box {
  border: 2px dashed var(--border-color);
  border-radius: var(--radius-xl);
  padding: 56px 24px;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-normal);
  background: #fafafa;
}

.upload-box:hover {
  border-color: var(--primary-color);
  background: var(--primary-light);
}

.upload-box.dragging {
  border-color: var(--primary-color);
  background: var(--primary-light);
  transform: scale(1.01);
  box-shadow: 0 8px 24px rgba(64, 158, 255, 0.2);
}

.upload-box.hasFile {
  border-color: var(--success-color);
  background: var(--success-light);
}

.upload-icon-wrap {
  margin-bottom: 24px;
}

.upload-icon {
  font-size: 64px;
  transition: transform var(--transition-normal);
}

.upload-box:hover .upload-icon {
  transform: scale(1.1);
}

.upload-title {
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}

.upload-hint {
  color: var(--text-secondary);
  font-size: 13px;
}

.file-input {
  display: none;
}

.file-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 24px;
  padding: 18px 24px;
  background-color: var(--bg-color);
  border-radius: var(--radius-md);
}

.file-detail {
  display: flex;
  align-items: center;
  gap: 16px;
}

.file-name {
  font-size: 15px;
  color: var(--text-primary);
  font-weight: 600;
}

.file-size {
  font-size: 13px;
  color: var(--text-secondary);
  padding: 4px 12px;
  background: white;
  border-radius: 4px;
}

.import-action {
  text-align: center;
  margin-top: 36px;
}

.import-btn {
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  border-radius: var(--radius-lg);
  background: var(--primary-gradient);
  border: none;
  transition: all var(--transition-normal);
}

.import-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(64, 158, 255, 0.35);
}

.action-hint {
  margin-top: 14px;
  color: var(--text-secondary);
  font-size: 13px;
}

.section-title h3 {
  font-size: 20px;
  color: var(--text-primary);
  margin-bottom: 8px;
  font-weight: 600;
}

.section-desc {
  color: var(--text-secondary);
  margin-bottom: 28px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.template-card {
  background: var(--bg-color);
  padding: 24px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-light);
  transition: all var(--transition-normal);
}

.template-card:hover {
  transform: translateY(-6px);
  box-shadow: var(--shadow-lg);
  border-color: var(--primary-color);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.card-icon {
  font-size: 28px;
}

.template-card h4 {
  font-size: 14px;
  color: var(--text-primary);
  margin: 0;
  font-weight: 600;
}

.template-card ul {
  list-style: none;
  padding: 0;
}

.template-card li {
  font-size: 13px;
  color: var(--text-regular);
  padding: 8px 0;
  padding-left: 24px;
  position: relative;
  border-bottom: 1px solid var(--border-light);
}

.template-card li:last-child {
  border-bottom: none;
}

.template-card li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: var(--success-color);
  font-size: 12px;
  font-weight: 600;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 900px) {
  .template-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 600px) {
  .template-grid { grid-template-columns: 1fr; }
  .upload-section { padding: 32px 16px; }
}
</style>