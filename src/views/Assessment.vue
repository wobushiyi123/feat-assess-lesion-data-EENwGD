<template>
  <div class="assessment-container">
    <div class="page-header">
      <el-button @click="$router.back()" :icon="ArrowLeft">返回</el-button>
      <h2>病灶评估 - {{ subject?.subject_id }}</h2>
      <div class="header-actions">
        <el-button type="primary" :icon="DataAnalysis" @click="showResultDialog = true">评估结果</el-button>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="subject" class="assessment-content">
      <div class="period-bar">
        <span class="period-label">检测周期</span>
        <el-select v-model="selectedId" placeholder="选择检测周期" style="width: 340px">
          <el-option
            v-for="opt in cycleOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </div>

      <div class="assessment-tabs">
        <div
          class="tab-item"
          :class="{ active: activeTab === 'target' }"
          @click="activeTab = 'target'"
        >
          靶病灶
        </div>
        <div
          class="tab-item"
          :class="{ active: activeTab === 'nonTarget' }"
          @click="activeTab = 'nonTarget'"
        >
          非靶病灶
        </div>
        <div
          class="tab-item"
          :class="{ active: activeTab === 'newLesion' }"
          @click="activeTab = 'newLesion'"
        >
          新病灶
        </div>
      </div>

      <div class="tab-content">
        <!-- 靶病灶 -->
        <div v-show="activeTab === 'target'">
          <div class="section-header">
            <h3>靶病灶数据</h3>
          </div>

          <el-table :data="assessment.targetLesions" border style="width: 100%" size="small">
            <el-table-column label="病灶名称" min-width="240">
              <template #default="scope">
                <span class="lesion-cell-text">{{ scope.row.name || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="位置" min-width="160">
              <template #default="scope">
                <span class="lesion-cell-text">{{ scope.row.location || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="基线最长径(mm)" width="150" align="center">
              <template #default="scope">
                <span>{{ scope.row.baselineSize ?? 0 }}</span>
              </template>
            </el-table-column>
            <el-table-column label="当前最长径(mm)" width="150" align="center">
              <template #default="scope">
                <span>{{ scope.row.currentSize ?? 0 }}</span>
              </template>
            </el-table-column>
            <el-table-column label="变化(%)" width="120" align="center">
              <template #default="scope">
                <span :style="{ color: getChangeColor(scope.row) }">
                  {{ getChangePercent(scope.row) }}%
                </span>
              </template>
            </el-table-column>
          </el-table>

          <div class="baseline-section">
            <h4>靶病灶基线数据</h4>
            <div class="baseline-grid">
              <div class="baseline-item">
                <span class="baseline-label">基线SLD总和</span>
                <span class="baseline-value">{{ baselineSum.toFixed(1) }} mm</span>
              </div>
              <div class="baseline-item">
                <span class="baseline-label">当前SLD总和</span>
                <span class="baseline-value">{{ currentSum.toFixed(1) }} mm</span>
              </div>
            </div>
          </div>

          <div class="summary-card">
            <div class="summary-item">
              <span class="summary-label">变化率</span>
              <span class="summary-value" :style="{ color: overallChangeColor }">{{ overallChangePercent }}%</span>
            </div>
            <div v-if="nadirSum !== null" class="summary-item">
              <span class="summary-label">历史最低点 (Nadir)</span>
              <span class="summary-value">{{ nadirSum.toFixed(1) }} mm</span>
            </div>
          </div>
        </div>

        <!-- 非靶病灶 -->
        <div v-show="activeTab === 'nonTarget'">
          <div class="section-header">
            <h3>非靶病灶数据</h3>
          </div>

          <el-table :data="assessment.nonTargetLesions" border style="width: 100%" size="small">
            <el-table-column label="病灶名称" min-width="240">
              <template #default="scope">
                <span class="lesion-cell-text">{{ scope.row.name || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="位置" min-width="160">
              <template #default="scope">
                <span class="lesion-cell-text">{{ scope.row.location || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="基线状态" width="150" align="center">
              <template #default="scope">
                <span>{{ scope.row.baseline_status || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="当前状态" width="150" align="center">
              <template #default="scope">
                <span>{{ scope.row.status || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="当前检查日期" width="150" align="center">
              <template #default="scope">
                <span>{{ scope.row.current_exam_date || '-' }}</span>
              </template>
            </el-table-column>
          </el-table>

          <!-- 非靶病灶基线数据 -->
          <div class="baseline-section">
            <h4>非靶病灶基线数据</h4>
            <div class="baseline-grid">
              <div class="baseline-item">
                <span class="baseline-label">基线病灶数</span>
                <span class="baseline-value">{{ assessment.nonTargetLesions.length }} 个</span>
              </div>
              <div class="baseline-item">
                <span class="baseline-label">肿瘤标志物正常</span>
                <span class="baseline-value">{{ assessment.tumorMarkerNormal ? '是' : '否' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 新病灶 -->
        <div v-show="activeTab === 'newLesion'">
          <div class="section-header">
            <h3>新病灶数据</h3>
          </div>

          <div class="new-lesion-notice">
            <el-alert
              title="新病灶无基线数据"
              type="info"
              description="根据 RECIST 1.1 标准，新病灶一经确认即判定整体疗效为疾病进展(PD)。新病灶不需要基线数据。"
              :closable="false"
              show-icon
            />
          </div>

          <el-alert
            v-if="assessment.newLesion"
            type="error"
            :closable="false"
            show-icon
            class="pd-new-lesion-banner"
            title="新病灶 → 整体疗效 PD"
            description="已标记存在新病灶，保存后整体疗效将按 RECIST 1.1 自动判定为疾病进展（PD）。"
          />

          <el-table :data="assessment.newLesions" border style="width: 100%" size="small">
            <el-table-column label="病灶名称" min-width="240">
              <template #default="scope">
                <span class="lesion-cell-text">{{ scope.row.name || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="位置" min-width="160">
              <template #default="scope">
                <span class="lesion-cell-text">{{ scope.row.location || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="检查日期" width="180" align="center">
              <template #default="scope">
                <span>{{ scope.row.exam_date || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="检查方法" width="150" align="center">
              <template #default="scope">
                <span>{{ scope.row.exam_method || '-' }}</span>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="assessment.newLesions.length === 0" class="no-new-lesion">
            <el-empty description="暂无新病灶记录" />
          </div>
        </div>

      </div>

      <!-- 评估结果弹窗：全周期综合评估 + 导出 Excel -->
      <el-dialog v-model="showResultDialog" :title="'综合评估报告 - ' + (subject?.subject_id || '')" width="900px" top="5vh">
        <div class="report-overview">
          <!-- 受试者概要 -->
          <div class="report-summary">
            <span class="rs-item"><b>受试者</b> {{ subject?.subject_id }}</span>
            <span class="rs-item"><b>评估周期数</b> {{ assessments.length }}</span>
          </div>

          <!-- 生成按钮 -->
          <el-button type="primary" :icon="DataAnalysis" @click="calculateFullReport" :loading="calculating">重新生成综合评估</el-button>

          <!-- 全周期评估结果表格 -->
          <div v-if="fullReport.length" class="full-report-table">
            <h4>各周期疗效评估明细</h4>
            <el-table :data="fullReport" border size="small" max-height="45vh">
              <el-table-column prop="cycle" label="周期" width="70" align="center" />
              <el-table-column prop="visit_name" label="访视名称" min-width="180" show-overflow-tooltip />
              <el-table-column prop="date" label="检查日期" width="120" align="center" />
              <el-table-column label="靶病灶 SLD" width="110" align="center">
                <template #default="{ row }">{{ row.target_sld?.toFixed(1) || '-' }} mm</template>
              </el-table-column>
              <el-table-column label="非靶病灶" width="100" align="center">
                <template #default="{ row }"><el-tag size="small" :type="row.nt_status === '进展' ? 'danger' : 'info'">{{ row.nt_status || '-' }}</el-tag></template>
              </el-table-column>
              <el-table-column label="新病灶" width="70" align="center">
                <template #default="{ row }"><span :style="{ color: row.has_new ? '#f56c6c' : '#67c23a' }">{{ row.has_new ? '有' : '无' }}</span></template>
              </el-table-column>
              <el-table-column label="总体疗效" width="100" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.overall" size="small" :type="overallTagType(row.overall)">{{ getStatusText(row.overall) }}</el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
            </el-table>

            <!-- 综合结论 -->
            <div class="report-conclusion">
              <h4>综合评估结论</h4>
              <div class="conclusion-card">
                <div class="conclusion-item">
                  <span class="conclusion-label">最佳疗效</span>
                  <span class="conclusion-value best" :style="{ color: bestResponseColor }">{{ bestResponse || '-' }}</span>
                </div>
                <div class="conclusion-item">
                  <span class="conclusion-label">当前疗效（最新周期）</span>
                  <span class="conclusion-value latest" :style="{ color: latestResponseColor }">{{ latestResponse || '-' }}</span>
                </div>
                <div class="conclusion-item">
                  <span class="conclusion-label">是否进展(PD)</span>
                  <span class="conclusion-value" :class="{ 'text-danger': everPD }">{{ everPD ? '是' : '否' }}</span>
                </div>
              </div>
            </div>
          </div>

          <el-empty v-else-if="!calculating && assessments.length === 0" description="暂无评估数据" />
        </div>

        <template #footer>
          <el-button @click="showResultDialog = false">关闭</el-button>
          <el-button type="success" :icon="Download" :disabled="fullReport.length === 0" @click="exportReportExcel" :loading="exporting">保存评估结果</el-button>
        </template>
      </el-dialog>

      <!-- 编辑病灶弹窗 -->
      <el-dialog
        v-model="editDialog.visible"
        :title="editDialog.title"
        width="780px"
        :close-on-click-modal="false"
        destroy-on-close
      >
        <!-- 基线期提示 / 随访期新增提示 -->
        <el-alert
          v-if="isBaselineAssessment"
          type="info"
          :closable="false"
          show-icon
          class="baseline-tip"
          title="基线期（Baseline）"
          description="基线期仅记录基线测量数据，不录入当前/随访径线与疗效评价。"
        />
        <el-alert
          v-if="!isBaselineAssessment && editDialog.lesionId === null && (editDialog.type === 'target' || editDialog.type === 'nonTarget')"
          type="warning"
          :closable="false"
          show-icon
          class="baseline-tip"
          title="随访期新增靶/非靶病灶"
          description="编号须与基线期一致（同一病灶的纵向追踪）；若为本次新发肿瘤，请使用「新病灶」页签新增。"
        />
        <!-- 靶病灶编辑表单 -->
        <template v-if="editDialog.type === 'target'">
          <el-form :model="editDialog.form" label-width="140px" size="small">
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="编号（EDC）">
                  <el-input v-model="editDialog.form.lesion_id" placeholder="如 T1" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="器官（分类）" required>
                  <el-select v-model="editDialog.form.organ" placeholder="选择器官" style="width:100%">
                    <el-option v-for="o in ORGAN_OPTIONS" :key="o" :label="o" :value="o" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="是否为淋巴结">
                  <el-switch v-model="editDialog.form.is_lymph_node" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="具体部位">
                  <el-input v-model="editDialog.form.location" placeholder="如: 肝右叶" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="器官具体描述">
              <el-input v-model="editDialog.form.description" placeholder="如: 肝右叶" />
            </el-form-item>
            <el-divider content-position="left">基线数据</el-divider>
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="是否检查">
                  <el-select v-model="editDialog.form.is_checked" placeholder="">
                    <el-option label="是" :value="true" />
                    <el-option label="否" :value="false" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="检查日期">
                  <el-date-picker v-model="editDialog.form.exam_date" type="date" placeholder="基线日期" value-format="YYYY-MM-DD" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="检查方法">
                  <el-input v-model="editDialog.form.exam_method" placeholder="如: 增强CT" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="其他检查方法">
                  <el-input v-model="editDialog.form.other_exam_method" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="分裂/融合">
                  <el-select v-model="editDialog.form.is_split_fused" placeholder="" clearable>
                    <el-option label="未发生" value="未发生" />
                    <el-option label="是" value="是" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="最长直径(mm)">
                  <el-input-number v-model="editDialog.form.baseline_size" :min="0" :precision="1" controls-position="right" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-divider content-position="left">当前/随访数据</el-divider>
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="是否检查">
                  <el-select v-model="editDialog.form.current_is_checked" placeholder="" clearable>
                    <el-option label="是" :value="true" />
                    <el-option label="否" :value="false" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="检查日期">
                  <el-date-picker v-model="editDialog.form.current_exam_date" type="date" placeholder="当前日期" value-format="YYYY-MM-DD" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="检查方法">
                  <el-input v-model="editDialog.form.current_exam_method" placeholder="如: 增强CT" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="其他检查方法">
                  <el-input v-model="editDialog.form.current_other_exam_method" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="分裂/融合">
                  <el-select v-model="editDialog.form.current_is_split_fused" placeholder="" clearable>
                    <el-option label="未发生" value="未发生" />
                    <el-option label="是" value="是" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="最长直径(mm)">
                  <el-input-number v-model="editDialog.form.current_size" :min="0" :precision="1" controls-position="right" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="靶病灶直径和(EDC)">
                  <el-input-number v-model="editDialog.form.sum_diameter" :min="0" :precision="1" controls-position="right" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="备注">
                  <el-input v-model="editDialog.form.notes" type="textarea" :rows="2" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </template>

        <!-- 非靶病灶编辑表单 -->
        <template v-else-if="editDialog.type === 'nonTarget'">
          <el-form :model="editDialog.form" label-width="140px" size="small">
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="编号（EDC）">
                  <el-input v-model="editDialog.form.lesion_id" placeholder="如 NT1" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="器官（分类）" required>
                  <el-select v-model="editDialog.form.organ" placeholder="选择器官" style="width:100%">
                    <el-option v-for="o in ORGAN_OPTIONS" :key="o" :label="o" :value="o" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="是否为淋巴结">
                  <el-switch v-model="editDialog.form.is_lymph_node" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="具体部位">
                  <el-input v-model="editDialog.form.location" placeholder="如: 肝左右叶" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="器官具体描述">
              <el-input v-model="editDialog.form.description" placeholder="如: 肝左右叶多处" />
            </el-form-item>
            <el-divider content-position="left">状态</el-divider>
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="基线状态">
                  <el-select v-model="editDialog.form.baseline_status" placeholder="">
                    <el-option label="持续存在" value="持续存在" />
                    <el-option label="消失" value="消失" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="当前状态">
                  <el-select v-model="editDialog.form.status" placeholder="">
                    <el-option label="消失" value="消失" />
                    <el-option label="持续存在" value="持续存在" />
                    <el-option label="进展" value="进展" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-divider content-position="left">基线检查信息</el-divider>
            <el-row :gutter="16">
              <el-col :span="6">
                <el-form-item label="是否检查(基线)">
                  <el-select v-model="editDialog.form.baseline_is_checked" placeholder="">
                    <el-option label="是" :value="true" />
                    <el-option label="否" :value="false" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="检查日期(基线)">
                  <el-date-picker v-model="editDialog.form.exam_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="检查方法(基线)">
                  <el-input v-model="editDialog.form.exam_method" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-divider content-position="left">当前检查信息</el-divider>
            <el-row :gutter="16">
              <el-col :span="6">
                <el-form-item label="是否检查(当前)">
                  <el-select v-model="editDialog.form.current_is_checked" placeholder="" clearable>
                    <el-option label="是" :value="true" />
                    <el-option label="否" :value="false" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="检查日期(当前)">
                  <el-date-picker v-model="editDialog.form.current_exam_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item label="检查方法(当前)">
                  <el-input v-model="editDialog.form.current_exam_method" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="备注">
              <el-input v-model="editDialog.form.notes" type="textarea" :rows="2" />
            </el-form-item>
          </el-form>
        </template>

        <!-- 新病灶编辑表单 -->
        <template v-else-if="editDialog.type === 'newLesion'">
          <el-form :model="editDialog.form" label-width="140px" size="small">
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="编号（EDC）">
                  <el-input v-model="editDialog.form.lesion_id" placeholder="如 NL1" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="器官（分类）" required>
                  <el-select v-model="editDialog.form.organ" placeholder="选择器官" style="width:100%">
                    <el-option v-for="o in ORGAN_OPTIONS" :key="o" :label="o" :value="o" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="是否为淋巴结">
                  <el-switch v-model="editDialog.form.is_lymph_node" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="具体部位">
                  <el-input v-model="editDialog.form.location" placeholder="如: 新发肺转移灶" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="器官具体描述">
              <el-input v-model="editDialog.form.description" placeholder="如: 新发肺转移灶" />
            </el-form-item>
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="检查日期">
                  <el-date-picker v-model="editDialog.form.exam_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="检查方法">
                  <el-input v-model="editDialog.form.exam_method" placeholder="如: 增强CT" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="其他检查方法">
                  <el-input v-model="editDialog.form.other_exam_method" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="备注">
              <el-input v-model="editDialog.form.notes" type="textarea" :rows="2" />
            </el-form-item>
          </el-form>
        </template>

        <template #footer>
          <el-button @click="editDialog.visible = false">取消</el-button>
          <el-button type="primary" @click="saveLesionEdit" :loading="editDialog.saving">保存</el-button>
        </template>
      </el-dialog>
    </div>

    <div v-else class="empty">
      <el-empty description="未找到受试者" />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Loading, DataAnalysis, Download } from '@element-plus/icons-vue'
import { subjectApi, assessmentApi } from '../api'
import { useBatchStore } from '../store/batch'
import api from '../api'
import { calculateTargetAssessment, calculateNonTargetAssessment, calculateOverallAssessment, getStatusColor, getStatusText } from '../utils/recist'
import { exportToExcelWithPicker } from '../utils/export'

const route = useRoute()
const router = useRouter()
const { state: batchState } = useBatchStore()

// 当前批次ID：优先取路由参数（从Subjects.vue跳转携带），其次取全局store
const currentBatchId = computed(() => {
  const q = Number(route.query.batch)
  return q > 0 ? q : batchState.currentBatchId
})
const loading = ref(false)
const subject = ref(null)
const activeTab = ref('target')
const assessmentResult = ref(null)
const nadirSum = ref(null)
// 按检测周期展示：所有评估周期 + 当前选中周期 + 结果弹窗可见性
const assessments = ref([])
const selectedId = ref(null)
const showResultDialog = ref(false)
// 全周期综合评估
const fullReport = ref([])
const calculating = ref(false)
const exporting = ref(false)

const assessment = ref({
  date: new Date().toISOString().split('T')[0],
  baselineDate: null,
  targetLesions: [],
  nonTargetLesions: [],
  newLesions: [],
  newLesion: false,
  tumorMarkerNormal: true,
  result: null
})

/** 将后端 snake_case 病灶字段映射为前端 camelCase 表单字段 */
function mapTargetLesion(t, aid) {
  return {
    id: t.id,
    assessment_id: aid,
    name: t.name || '',
    location: t.location || '',
    description: t.description || '',
    lesion_id: t.lesion_id || '',
    baselineSize: t.baseline_size ?? 0,
    currentSize: t.current_size ?? 0,
    size_unit: t.size_unit || 'mm',
    sum_diameter: t.sum_diameter ?? 0,
    is_checked: t.is_checked,
    exam_date: t.exam_date || '',
    exam_method: t.exam_method || '',
    other_exam_method: t.other_exam_method || '',
    is_split_fused: t.is_split_fused || '未发生',
    split_fuse_detail: t.split_fuse_detail || '',
    current_is_checked: t.current_is_checked,
    current_exam_date: t.current_exam_date || '',
    current_exam_method: t.current_exam_method || '',
    current_other_exam_method: t.current_other_exam_method || '',
    current_is_split_fused: t.current_is_split_fused || '未发生',
    current_split_fuse_detail: t.current_split_fuse_detail || '',
    notes: t.notes || ''
  }
}

function mapNonTargetLesion(t, aid) {
  return {
    id: t.id,
    assessment_id: aid,
    name: t.name || '',
    location: t.location || '',
    description: t.description || '',
    lesion_id: t.lesion_id || '',
    baseline_status: t.baseline_status ?? '持续存在',
    status: t.status || '持续存在',
    baseline_is_checked: t.baseline_is_checked,
    current_is_checked: t.current_is_checked,
    exam_date: t.exam_date || '',
    exam_method: t.exam_method || '',
    current_exam_date: t.current_exam_date || '',
    current_exam_method: t.current_exam_method || '',
    notes: t.notes || ''
  }
}

function mapNewLesion(t, aid) {
  return {
    id: t.id,
    assessment_id: aid,
    name: t.name || '',
    location: t.location || '',
    description: t.description || '',
    lesion_id: t.lesion_id || '',
    exam_date: t.exam_date || '',
    exam_method: t.exam_method || '',
    other_exam_method: t.other_exam_method || '',
    notes: t.notes || ''
  }
}

const loadSubject = async () => {
  // keep-alive 下从详情导航到列表（/subjects，无 id 参数）时 route.params.id 为 undefined，跳过请求
  if (!route.params.id) {
    loading.value = false
    return
  }
  loading.value = true
  try {
    subject.value = await subjectApi.get(route.params.id, { batch_id: currentBatchId.value })
    // 按周期（cycle_number）升序排列所有评估，供「检测周期」选择器使用
    const list = subject.value.assessments || []
    assessments.value = [...list].sort((a, b) => {
      const ca = a.cycle_number || 0
      const cb = b.cycle_number || 0
      if (ca !== cb) return ca - cb
      const da = new Date(a.assessment_date || 0).getTime()
      const db = new Date(b.assessment_date || 0).getTime()
      if (da !== db) return da - db
      return (a.id || 0) - (b.id || 0)
    })
    if (assessments.value.length) {
      // 计算历史最低点（Nadir），跨所有周期
      const allSums = assessments.value.map(a => a.current_sum || 0).filter(s => s > 0)
      if (allSums.length > 0) nadirSum.value = Math.min(...allSums)
      // 默认选中最新周期（按 ID 降序）
      const latest = [...assessments.value].sort((a, b) => (b.id || 0) - (a.id || 0))[0]
      selectedId.value = latest.id
      applySelected()
    } else {
      selectedId.value = null
      assessmentResult.value = null
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载受试者详情失败')
  } finally {
    loading.value = false
  }
}

// 将选中的检测周期数据灌入表格（靶/非靶/新病灶）
const applySelected = () => {
  const a = assessments.value.find(x => x.id === selectedId.value)
  if (!a) return
  assessment.value.date = a.assessment_date ? a.assessment_date.split('T')[0] : assessment.value.date
  assessment.value.targetLesions = (a.target_lesions || []).map(t => mapTargetLesion(t, a.id))
  assessment.value.nonTargetLesions = (a.non_target_lesions || []).map(t => mapNonTargetLesion(t, a.id))
  assessment.value.newLesions = (a.new_lesions || []).map(t => mapNewLesion(t, a.id))
  assessment.value.newLesion = a.has_new_lesion || false
  assessment.value.tumorMarkerNormal = a.tumor_marker_normal !== false
  // 切换周期后清空上一次评估结果
  assessmentResult.value = null
}

// 周期选择器选项：优先用 EDC 原始访视名称，无则回退「周期N」+ 评估日期
const cycleOptions = computed(() => {
  return assessments.value.map((a, i) => {
    const cyc = a.cycle_number || (i + 1)
    const base = a.visit_name || ('周期' + cyc)
    const date = a.assessment_date ? a.assessment_date.split('T')[0] : ''
    return {
      value: a.id,
      label: date ? `${base}（${date}）` : base,
      cycle: cyc
    }
  })
})

// 基线期 = 所有周期中评估日期最早的一条
const baselineId = computed(() => {
  if (!assessments.value.length) return null
  const sorted = [...assessments.value].sort((a, b) => {
    const da = new Date(a.assessment_date || 0).getTime()
    const db = new Date(b.assessment_date || 0).getTime()
    if (da !== db) return da - db
    return (a.id || 0) - (b.id || 0)
  })
  return sorted[0].id
})

onMounted(() => {
  loadSubject()
})

// 路由参数变化（切换不同受试者）时强制重新加载，避免组件复用导致显示旧受试者数据
watch(() => route.params.id, (id) => {
  if (id) loadSubject()
})

// 切换检测周期时，刷新三类病灶表格数据
watch(selectedId, () => {
  applySelected()
})

// 打开「评估结果」弹窗时，自动基于整个受试者的所有检测周期生成综合评估
watch(showResultDialog, (v) => {
  if (v && assessments.value.length) {
    calculateFullReport()
  }
})

// 纵向防呆：判断当前选中的检测周期是否为基线期（评估日期最早的一条）
const isBaselineAssessment = computed(() => selectedId.value === baselineId.value)

const baselineSum = computed(() => {
  return assessment.value.targetLesions.reduce((sum, l) => sum + (l.baselineSize || 0), 0)
})

const currentSum = computed(() => {
  return assessment.value.targetLesions.reduce((sum, l) => sum + (l.currentSize || 0), 0)
})

const overallChangePercent = computed(() => {
  if (baselineSum.value === 0) return 0
  return (((currentSum.value - baselineSum.value) / baselineSum.value) * 100).toFixed(1)
})

const overallChangeColor = computed(() => {
  const percent = parseFloat(overallChangePercent.value)
  if (percent <= -30) return '#67c23a'
  if (percent >= 20) return '#f56c6c'
  return '#e6a23c'
})

const getChangePercent = (lesion) => {
  if (!lesion.baselineSize) return 0
  return (((lesion.currentSize - lesion.baselineSize) / lesion.baselineSize) * 100).toFixed(1)
}

const getChangeColor = (lesion) => {
  const percent = parseFloat(getChangePercent(lesion))
  if (percent <= -30) return '#67c23a'
  if (percent >= 20) return '#f56c6c'
  return '#e6a23c'
}

const addTargetLesion = () => {
  assessment.value.targetLesions.push({
    name: '',
    location: '',
    baselineSize: 0,
    currentSize: 0
  })
}

const removeTargetLesion = (index) => {
  assessment.value.targetLesions.splice(index, 1)
}

const addNonTargetLesion = () => {
  assessment.value.nonTargetLesions.push({
    name: '',
    location: '',
    baselineStatus: '存在',
    status: '持续存在'
  })
}

const removeNonTargetLesion = (index) => {
  assessment.value.nonTargetLesions.splice(index, 1)
}

const addNewLesion = () => {
  assessment.value.newLesions.push({
    name: '',
    location: '',
    size: 0,
    foundDate: new Date()
  })
  assessment.value.newLesion = true
}

const removeNewLesion = (index) => {
  assessment.value.newLesions.splice(index, 1)
  if (assessment.value.newLesions.length === 0) {
    assessment.value.newLesion = false
  }
}

const calculateAssessment = () => {
  const ntStatuses = assessment.value.nonTargetLesions.map(l => l.status)
  let nonTargetStatus = ''
  if (ntStatuses.some(s => s === '进展')) {
    nonTargetStatus = '进展'
  } else if (ntStatuses.some(s => s === '持续存在')) {
    nonTargetStatus = '持续存在'
  } else if (ntStatuses.length > 0 && ntStatuses.every(s => s === '消失')) {
    nonTargetStatus = '消失'
  }

  const targetResult = calculateTargetAssessment(
    baselineSum.value,
    currentSum.value,
    assessment.value.newLesion,
    { nadirSum: nadirSum.value, isEmpty: assessment.value.targetLesions.length === 0 }
  )
  const nonTargetResult = calculateNonTargetAssessment(
    nonTargetStatus,
    assessment.value.tumorMarkerNormal,
    { isEmpty: assessment.value.nonTargetLesions.length === 0 }
  )
  const overallResult = calculateOverallAssessment(targetResult, nonTargetResult, assessment.value.newLesion)

  assessmentResult.value = {
    target: targetResult,
    nonTarget: nonTargetResult,
    overall: overallResult,
    nadirSum: nadirSum.value
  }

  assessment.value.result = assessmentResult.value
}

// ========== 全周期综合评估 ==========
const bestResponse = computed(() => {
  if (!fullReport.value.length) return null
  // 按疗效优先级排序：CR > PR > SD > Non-CR/Non-PD > PD > NE
  const order = { 'CR': 0, 'PR': 1, 'SD': 2, 'Non-CR/Non-PD': 3, 'PD': 4, 'NE': 5 }
  // 兼容后端可能存储的中/英文状态值，统一归一到排序键
  const norm = (s) => {
    if (!s || order[s] !== undefined) return s
    const m = { '完全缓解': 'CR', '部分缓解': 'PR', '疾病稳定': 'SD', '疾病进展': 'PD', '无法评估': 'NE', '非完全缓解/非疾病进展': 'Non-CR/Non-PD', '非完全缓解(Non-CR)/非疾病进展(Non-PD)': 'Non-CR/Non-PD' }
    return m[s] || s
  }
  let best = norm(fullReport.value[0].overall)
  fullReport.value.forEach(r => {
    const n = norm(r.overall)
    if (n && (order[n] ?? 9) < (order[best] ?? 9)) best = n
  })
  return best ? getStatusText(best) : null
})

const bestResponseColor = computed(() => {
  if (!bestResponse.value) return '#909399'
  return getStatusColor(bestResponse.value)
})

const latestResponse = computed(() => {
  if (!fullReport.value.length) return null
  const last = fullReport.value[fullReport.value.length - 1]
  return last.overall ? getStatusText(last.overall) : null
})

const latestResponseColor = computed(() => {
  if (!latestResponse.value) return '#909399'
  return getStatusColor(latestResponse.value)
})

const everPD = computed(() => {
  return fullReport.value.some(r => r.overall === 'PD' || r.has_new)
})

const overallTagType = (status) => {
  const map = { 'CR': 'success', 'PR': '', 'SD': 'warning', 'Non-CR/Non-PD': 'info', 'PD': 'danger', 'NE': 'info' }
  return map[status] || 'info'
}

const calculateFullReport = () => {
  calculating.value = true
  try {
    const rows = []
    const sorted = [...assessments.value].sort((a, b) => (a.cycle_number || 0) - (b.cycle_number || 0))

    sorted.forEach(a => {
      const tls = a.target_lesions || []
      const ntls = a.non_target_lesions || []
      const nls = a.new_lesions || []

      // 计算该周期靶病灶 SLD
      const targetSLD = tls.reduce((sum, t) => sum + (t.current_size || t.currentSize || 0), 0)

      // 非靶病灶状态判定
      let ntStatus = '-'
      if (ntls.length > 0) {
        if (ntls.some(s => s.status === '进展')) ntStatus = '进展'
        else if (ntls.every(s => s.status === '消失')) ntStatus = '消失'
        else if (ntls.some(s => s.status === '持续存在')) ntStatus = '持续存在'
        else ntStatus = ntls[0].status || '-'
      }

      // 是否有新病灶
      const hasNew = !!(a.has_new_lesion || (nls && nls.length > 0))

      // 该周期总体疗效：直接与「报告」保持一致，使用后端评估结论
      // （人工评估 manual_overall_status 优先于程序计算 overall_status，口径与 Report.vue 完全一致）
      const overall = a.manual_overall_status || a.overall_status || null

      rows.push({
        cycle: a.cycle_number || (sorted.indexOf(a) + 1),
        visit_name: a.visit_name || ('周期' + (a.cycle_number || sorted.indexOf(a) + 1)),
        date: a.assessment_date ? String(a.assessment_date).split('T')[0] : '',
        target_sld: targetSLD,
        nt_status: ntStatus,
        has_new: hasNew,
        overall: overall,
        target_count: tls.length,
        non_target_count: ntls.length,
        new_lesion_count: nls.length
      })
    })

    fullReport.value = rows
  } catch (e) {
    console.error(e)
    ElMessage.error('生成报告失败：' + e.message)
  } finally {
    calculating.value = false
  }
}

const exportReportExcel = async () => {
  if (!fullReport.value.length) return
  exporting.value = true
  try {
    const data = fullReport.value.map(r => ({
      '周期': r.cycle,
      '访视名称': r.visit_name,
      '检查日期': r.date,
      '靶病灶数': r.target_count,
      '非靶病灶数': r.non_target_count,
      '新病灶数': r.new_lesion_count,
      '靶病灶 SLD (mm)': r.target_sld?.toFixed(1) || '-',
      '非靶病灶状态': r.nt_status,
      '新病灶': r.has_new ? '有' : '无',
      '总体疗效': r.overall ? getStatusText(r.overall) : '-'
    }))
    // 添加综合结论行
    data.push({})
    data.push({
      '周期': '',
      '访视名称': '【综合结论】',
      '检查日期': '',
      '靶病灶数': '',
      '非靶病灶数': '',
      '新病灶数': '',
      '靶病灶 SLD (mm)': '',
      '非靶病灶状态': '',
      '新病灶': everPD.value ? '是(曾进展)' : '否',
      '总体疗效': `最佳=${bestResponse.value || '-'} / 当前=${latestResponse.value || '-'}`
    })

    const fn = `${subject.value?.subject_id || '评估报告'}_RECIST_${new Date().toISOString().split('T')[0]}.xlsx`
    await exportToExcelWithPicker(data, fn, 'RECIST 综合评估')
    ElMessage.success('已导出 Excel（已选择保存位置）')
  } catch (e) {
    console.error(e)
    ElMessage.error('导出失败：' + e.message)
  } finally {
    exporting.value = false
  }
}

const saveAssessment = async () => {
  if (!assessmentResult.value) {
    ElMessage.warning('请先执行评估')
    return
  }

  try {
    const data = {
      subject_id: parseInt(route.params.id),
      assessment_date: assessment.value.date,
      cycle_number: (subject.value?.assessments?.length || 0) + 1,
      has_new_lesion: assessment.value.newLesion,
      tumor_marker_normal: assessment.value.tumorMarkerNormal,
      target_lesions: assessment.value.targetLesions.map(l => ({
        name: l.name,
        location: l.location || '',
        baseline_size: l.baselineSize || 0,
        current_size: l.currentSize || 0
      })),
      non_target_lesions: assessment.value.nonTargetLesions.map(l => ({
        name: l.name,
        location: l.location || '',
        status: l.status || '持续存在'
      }))
    }
    await assessmentApi.create(data)
    ElMessage.success('评估结果已保存')
    await loadSubject()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  }
}

// ========== 编辑病灶弹窗 ==========
// 标准 RECIST 1.1 器官分类（下拉枚举）
const ORGAN_OPTIONS = [
  '淋巴结', '肺', '肝', '骨', '脑', '肾上腺', '腹膜后', '盆腔', '乳腺', '皮下软组织', '其他'
]

const editDialog = reactive({
  visible: false,
  type: '',          // 'target' | 'nonTarget' | 'newLesion'
  title: '',
  index: -1,         // 当前编辑的病灶在数组中的索引
  lesionId: null,    // 已有病灶的 DB id（新增时为 null）
  assessmentId: null,
  form: {},
  saving: false
})

const editTargetLesion = (row, index) => {
  editDialog.type = 'target'
  editDialog.title = '编辑靶病灶'
  editDialog.index = index
  editDialog.lesionId = row.id || null
  editDialog.assessmentId = row.assessment_id || null
  editDialog.form = {
    name: row.name || '',
    location: row.location || '',
    organ: row.organ || '',
    is_lymph_node: !!(row.is_lymph_node),
    description: row.description || '',
    lesion_id: row.lesion_id || '',
    baseline_size: row.baselineSize ?? row.baseline_size ?? 0,
    current_size: row.currentSize ?? row.current_size ?? 0,
    size_unit: row.size_unit || 'mm',
    sum_diameter: row.sum_diameter ?? 0,
    is_checked: row.is_checked !== undefined ? row.is_checked : true,
    exam_date: row.exam_date || '',
    exam_method: row.exam_method || '',
    other_exam_method: row.other_exam_method || '',
    is_split_fused: row.is_split_fused || '未发生',
    current_is_checked: row.current_is_checked !== undefined ? row.current_is_checked : true,
    current_exam_date: row.current_exam_date || '',
    current_exam_method: row.current_exam_method || '',
    current_other_exam_method: row.current_other_exam_method || '',
    current_is_split_fused: row.current_is_split_fused || '未发生',
    notes: row.notes || ''
  }
  editDialog.visible = true
}

const editNonTargetLesion = (row, index) => {
  editDialog.type = 'nonTarget'
  editDialog.title = '编辑非靶病灶'
  editDialog.index = index
  editDialog.lesionId = row.id || null
  editDialog.assessmentId = row.assessment_id || null
  editDialog.form = {
    name: row.name || '',
    location: row.location || '',
    organ: row.organ || '',
    is_lymph_node: !!(row.is_lymph_node),
    description: row.description || '',
    lesion_id: row.lesion_id || '',
    baseline_status: row.baselineStatus ?? row.baseline_status ?? '持续存在',
    status: row.status || '持续存在',
    baseline_is_checked: row.baseline_is_checked !== undefined ? row.baseline_is_checked : true,
    current_is_checked: row.current_is_checked !== undefined ? row.current_is_checked : true,
    exam_date: row.exam_date || '',
    exam_method: row.exam_method || '',
    current_exam_date: row.current_exam_date || '',
    current_exam_method: row.current_exam_method || '',
    notes: row.notes || ''
  }
  editDialog.visible = true
}

const editNewLesion = (row, index) => {
  editDialog.type = 'newLesion'
  editDialog.title = '编辑新病灶'
  editDialog.index = index
  editDialog.lesionId = row.id || null
  editDialog.assessmentId = row.assessment_id || null
  editDialog.form = {
    name: row.name || '',
    location: row.location || '',
    organ: row.organ || '',
    is_lymph_node: !!(row.is_lymph_node),
    description: row.description || '',
    lesion_id: row.lesion_id || '',
    exam_date: row.exam_date || row.foundDate || '',
    exam_method: row.exam_method || '',
    other_exam_method: row.other_exam_method || '',
    notes: row.notes || ''
  }
  editDialog.visible = true
}

const saveLesionEdit = async () => {
  if (!editDialog.form.name && !editDialog.form.location) {
    ElMessage.warning('请至少填写名称或位置')
    return
  }
  if (!editDialog.form.organ) {
    ElMessage.warning('请选择器官（分类）')
    return
  }

  // 先更新本地数据（立即反馈）
  const listKey = editDialog.type === 'target' ? 'targetLesions'
    : editDialog.type === 'nonTarget' ? 'nonTargetLesions'
    : 'newLesions'

  const localData = { ...editDialog.form }

  // 映射回本地字段名（camelCase）
  if (editDialog.type === 'target') {
    Object.assign(assessment.value[listKey][editDialog.index], {
      name: localData.name,
      location: localData.location,
      baselineSize: localData.baseline_size,
      currentSize: localData.current_size
    })
  } else if (editDialog.type === 'nonTarget') {
    Object.assign(assessment.value[listKey][editDialog.index], {
      name: localData.name,
      location: localData.location,
      baseline_status: localData.baseline_status,
      status: localData.status,
      current_exam_date: localData.current_exam_date
    })
  } else {
    Object.assign(assessment.value[listKey][editDialog.index], {
      name: localData.name,
      location: localData.location,
      size: localData.size,
      foundDate: localData.exam_date
    })
  }

  // 如果是已存在的病灶且有 assessmentId，调用后端 API 持久化
  if (editDialog.lesionId && editDialog.assessmentId) {
    editDialog.saving = true
    try {
      const apiMap = {
        target: `/api/assessments/${editDialog.assessmentId}/target-lesions/${editDialog.lesionId}`,
        nonTarget: `/api/assessments/${editDialog.assessmentId}/non-target-lesions/${editDialog.lesionId}`,
        newLesion: `/api/assessments/${editDialog.assessmentId}/new-lesions/${editDialog.lesionId}`
      }
      await api.put(apiMap[editDialog.type], editDialog.form)
      ElMessage.success('病灶信息已更新')
    } catch (e) {
      ElMessage.error('保存到服务器失败：' + (e.response?.data?.detail || e.message))
    } finally {
      editDialog.saving = false
    }
  } else {
    ElMessage.success('病灶信息已更新（本地）')
  }

  editDialog.visible = false
}
</script>

<style scoped>
.assessment-container {
  max-width: 1200px;
  margin: 0 auto;
  padding-bottom: 40px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
}

.page-header h2 {
  font-size: 28px;
  color: var(--text-primary);
  font-weight: 700;
  letter-spacing: -0.5px;
}

.header-actions {
  margin-left: auto;
}

.period-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: var(--spacing-xl);
  flex-wrap: wrap;
}

.period-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-regular);
}

.period-tag {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 10px;
  font-weight: 500;
}

.period-tag.baseline {
  background: #ecf5ff;
  color: #409eff;
  border: 1px solid #d9ecff;
}

.period-tag.followup {
  background: #f0f9eb;
  color: #67c23a;
  border: 1px solid #e1f3d8;
}

.assessment-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: var(--spacing-xl);
  background-color: var(--bg-color);
  padding: 8px;
  border-radius: var(--radius-md);
}

.tab-item {
  flex: 1;
  padding: 12px;
  text-align: center;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-normal);
  font-weight: 500;
  color: var(--text-regular);
}

.tab-item.active {
  background-color: var(--card-bg);
  color: var(--primary-color);
  box-shadow: var(--shadow-sm);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

/* 表格文本列允许换行，避免长名称/位置被截断 */
.lesion-cell-text {
  display: inline-block;
  width: 100%;
  white-space: normal;
  word-break: break-word;
  line-height: 1.5;
  text-align: left;
}

.section-header h3 {
  font-size: 18px;
  color: var(--text-primary);
  font-weight: 600;
}

.baseline-section {
  margin-top: var(--spacing-lg);
  padding: var(--spacing-md);
  background: var(--primary-light);
  border-radius: var(--radius-md);
  border: 1px solid #d6e4ff;
}

.baseline-section h4 {
  font-size: 15px;
  color: var(--text-primary);
  margin-bottom: var(--spacing-md);
  font-weight: 500;
}

.baseline-grid {
  display: flex;
  gap: var(--spacing-xl);
  flex-wrap: wrap;
}

.baseline-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.baseline-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.baseline-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.summary-card {
  display: flex;
  gap: var(--spacing-xl);
  margin-top: var(--spacing-lg);
  padding: var(--spacing-lg);
  background-color: var(--bg-color);
  border-radius: var(--radius-md);
}

.summary-item {
  display: flex;
  flex-direction: column;
}

.summary-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.summary-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.new-lesion-notice {
  margin-bottom: 16px;
}

.pd-new-lesion-banner {
  margin-bottom: 16px;
}

.baseline-tip {
  margin-bottom: 16px;
}

.no-new-lesion {
  padding: 20px 0;
}

.result-section {
  margin-top: var(--spacing-lg);
}

.result-card {
  background: var(--card-bg);
  padding: var(--spacing-xl);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  margin-bottom: var(--spacing-lg);
  border: 1px solid var(--border-light);
}

.result-card h3 {
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: var(--spacing-md);
  font-weight: 500;
}

.result-status {
  display: inline-block;
  padding: 8px 24px;
  border-radius: var(--radius-md);
  color: white;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
}

.result-status.large {
  padding: 12px 40px;
  font-size: 24px;
}

.result-reason {
  color: var(--text-regular);
  font-size: 14px;
  line-height: 1.6;
}

.result-card.overall {
  border: 2px solid var(--primary-color);
}

.loading, .empty {
  text-align: center;
  padding: 60px;
  color: #909399;
}

/* 全周期综合评估弹窗 */
.report-overview {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}
.report-summary {
  display: flex;
  gap: 24px;
  padding: 12px 16px;
  background: var(--bg-color);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  flex-wrap: wrap;
}
.rs-item {
  font-size: 14px;
  color: var(--text-regular);
}
.rs-item b {
  color: var(--text-primary);
}
.full-report-table {
  margin-top: var(--spacing-sm);
}
.full-report-table h4 {
  font-size: 15px;
  color: var(--text-primary);
  margin-bottom: var(--spacing-sm);
  font-weight: 600;
}
.report-conclusion {
  margin-top: var(--spacing-lg);
  padding: var(--spacing-lg);
  background: linear-gradient(135deg, #f0f5ff, #ecf5ff);
  border-radius: var(--radius-lg);
  border: 1px solid #d6e4ff;
}
.report-conclusion h4 {
  font-size: 15px;
  color: var(--text-primary);
  margin-bottom: var(--spacing-md);
  font-weight: 600;
}
.conclusion-card {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
}
.conclusion-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.conclusion-label {
  font-size: 13px;
  color: var(--text-secondary);
}
.conclusion-value {
  font-size: 20px;
  font-weight: 700;
}
.conclusion-value.best { font-size: 22px; }
.conclusion-value.latest { }
.text-danger { color: #f56c6c !important; }
</style>
