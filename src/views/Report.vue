<template>
  <div class="report-container">
    <div class="page-header">
      <el-button @click="$router.back()" :icon="ArrowLeft">返回</el-button>
      <h2>📊 受试者: {{ subject?.subject_id }}</h2>
      <ExportMenu :rows="exportRows" type="assessments" :filename="exportFilename" :title="exportTitle" :subtitle="exportSubtitle" />
    </div>

    <div v-if="loading" class="loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <div v-else-if="subject" class="report-body">
      <!-- SLD 解释 Tooltip（全局浮层 — 与 RECIST 1.1 6.1/6.2/6.3 标准完全对齐） -->
      <div v-if="sldTooltip.visible" class="sld-tooltip" :style="sldTooltip.style">
        <div class="sld-tooltip-title">{{ sldTooltip.title }}</div>
        <div class="sld-tooltip-content">
          <template v-if="sldTooltip.type === 'baseline'">
            <p><strong>基线 SLD（Baseline Sum of Longest Diameters）</strong></p>
            <p>定义：筛选期（基线）时，所有<strong>靶病灶最长直径</strong>的总和。</p>
            <p class="sld-tip-formula">SLD_baseline = Σ(各靶病灶基线最长径)</p>
            <p>用途：作为后续疗效评价的<strong>基准参照值</strong>，用于计算 PR 变化百分比。</p>
            <hr/>
            <p><strong>6.1 靶病灶判定标准：</strong></p>
            <ul>
              <li><span class="badge badge-cr">CR 完全缓解</span> 所有靶病灶消失；所有病理淋巴结短轴 &lt; 10 mm</li>
              <li><span class="badge badge-pr">PR 部分缓解</span> 靶病灶 SLD 较基线<strong>下降 ≥30%</strong></li>
              <li><span class="badge badge-sd">SD 疾病稳定</span> 既达不到 PR（缩小不足），也未达 PD（增大不足），介于两者之间</li>
              <li><span class="badge badge-pd">PD 疾病进展</span> 满足以下任一：<br/>
                ① SLD 较研究期间最小值(nadir,含基线) <strong>增加 ≥20%</strong> 且 <strong>绝对值增加 ≥5mm</strong>；<br/>
                ② 出现新病灶
              </li>
            </ul>
            <hr/>
            <p><strong>⚠️ 三个极易出错的细节：</strong></p>
            <ol>
              <li><strong>PD 参照是 nadir（最低值），不是基线。</strong><br/>例：基线100→最低50→复查60：相对+20%(=+60) 且绝对+10mm≥5 → 判PD。若回升到58(+16%&lt;20%) 则仍SD。</li>
              <li><strong>PD 双条件缺一不可：</strong>既需相对+20%，又需绝对+5mm。小病灶微小波动不应误判为进展。</li>
              <li><strong>新病灶 = PD</strong>，无论大小、无论出现在何处（含 FDG-PET 发现）。</li>
            </ol>
          </template>
          <template v-else>
            <p><strong>当前 SLD（Current Sum of Longest Diameters）</strong></p>
            <p>定义：本次访视时，所有<strong>靶病灶当前最长直径</strong>的总和。</p>
            <p class="sld-tip-formula">SLD_now = Σ(各靶病灶本次测量最长径)</p>
            <p>用途：与<strong>基线 SLD</strong>对比计算变化率(%)；与<strong>nadir SLD</strong>(历史最低)对比判定 PD。</p>
            <hr/>
            <p><strong>Nadir SLD 定义：</strong></p>
            <p class="sld-tip-formula">SLD_nadir = min(SLD_baseline, SLD_followup_1, SLD_followup_2, ...)</p>
            <p>即治疗过程中出现的最低 SLD 值（含基线本身）。</p>
            <hr/>
            <p><strong>关键判定公式：</strong></p>
            <ul>
              <li><strong>PR</strong>: (SLD_baseline − SLD_now) / SLD_baseline <strong>≥ 0.30</strong></li>
              <li><strong>PD</strong>: (SLD_now − SLD_nadir) / SLD_nadir <strong>≥ 0.20</strong> AND (SLD_now − SLD_nadir) <strong>≥ 5 mm</strong></li>
              <li>或 → <strong>出现新病灶 = PD</strong></li>
            </ul>
            <hr/>
            <p><strong>6.2 非靶病灶判定：</strong></p>
            <ul>
              <li><span class="badge badge-cr">CR</span> 所有非靶病灶消失；淋巴结短轴 &lt; 10 mm</li>
              <li><span class="badge badge-sd">非CR/非PD (IR/SD)</span> 存在≥1个非靶病灶，或肿瘤标志物持续高于正常</li>
              <li><span class="badge badge-pd">PD</span> 已有非靶病灶<strong>明确(unequivocal)</strong>进展，或出现任何新病灶<br/><em style="color:#909399;font-size:12px;">注：轻微增大不构成PD，须是明确进展</em></li>
            </ul>
          </template>
        </div>
      </div>

      <div class="subject-info-card">
        <div class="card-header">
          <span class="card-icon">👤</span>
          <h3>受试者基本信息</h3>
        </div>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">受试者ID</span>
            <span class="info-value">{{ subject.subject_id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">总体疗效评估</span>
            <span class="info-value" :style="{ color: latestOverallStatus ? getStatusColor(latestOverallStatus) : '' }">{{ latestOverallText }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">最近评估</span>
            <span class="info-value">{{ sortedAssessments.length ? formatDate(sortedAssessments[sortedAssessments.length - 1].assessment_date) : '-' }}</span>
          </div>
        </div>
      </div>

      <div class="timepoint-section">
        <div class="section-header">
          <h3>各时间点评估详情</h3>
        </div>
        <div class="timepoint-table">
          <div class="table-header-row">
            <div class="th">时间点</div>
            <div class="th">基线SLD
              <span class="sld-tooltip-trigger" @mouseenter="(e) => showSldTooltip(e, 'baseline')" @mouseleave="hideSldTooltip">ⓘ</span>
            </div>
            <div class="th">当前SLD
              <span class="sld-tooltip-trigger" @mouseenter="(e) => showSldTooltip(e, 'current')" @mouseleave="hideSldTooltip">ⓘ</span>
            </div>
            <div class="th">变化%</div>
            <div class="th">靶病灶评估<br><span class="th-sub-inline">程序 ↔ 人工</span></div>
            <div class="th">非靶病灶评估<br><span class="th-sub-inline">程序 ↔ 人工</span></div>
            <div class="th">新病灶<br><span class="th-sub-inline">程序 ↔ 人工</span></div>
            <div class="th">整体评价<br><span class="th-sub-inline">程序 ↔ 人工</span></div>
            <div class="th reason">程序判定理由</div>
          </div>
          <div v-for="a in pagedAssessments" :key="a.id" class="table-row" @click="showAssessmentDetail(a)">
            <div class="td">{{ a.timepoint || `周期${a.cycle_number}` }}</div>
            <div class="td">{{ a.baseline_sum?.toFixed(1) || '-' }} mm</div>
            <div class="td">{{ a.current_sum?.toFixed(1) || '-' }} mm</div>
            <div class="td" :style="{ color: changeColor(a.change_percent) }">
              {{ a.change_percent?.toFixed(1) }}%
            </div>
            <div class="td">
              <div class="compare-cell">
                <div class="compare-item">
                  <span class="source-label">程序</span>
                  <span class="badge" :class="badgeClass(a.target_status)">{{ shortStatus(a.target_status) }}</span>
                </div>
                <div class="compare-item" v-if="a.manual_target_status">
                  <span class="source-label">人工</span>
                  <span class="badge" :class="badgeClass(a.manual_target_status)">{{ shortStatus(a.manual_target_status) }}</span>
                </div>
                <div class="compare-item" v-else>
                  <span class="source-label">人工</span>
                  <span class="no-data">-</span>
                </div>
              </div>
            </div>
            <div class="td">
              <div class="compare-cell">
                <div class="compare-item">
                  <span class="source-label">程序</span>
                  <span class="badge" :class="badgeClass(a.non_target_status)">{{ shortStatus(a.non_target_status) }}</span>
                </div>
                <div class="compare-item" v-if="a.manual_non_target_status">
                  <span class="source-label">人工</span>
                  <span class="badge" :class="badgeClass(a.manual_non_target_status)">{{ shortStatus(a.manual_non_target_status) }}</span>
                </div>
                <div class="compare-item" v-else>
                  <span class="source-label">人工</span>
                  <span class="no-data">-</span>
                </div>
              </div>
            </div>
            <div class="td">
              <div class="compare-cell">
                <div class="compare-item">
                  <span class="source-label">程序</span>
                  <span :class="a.has_new_lesion ? 'new-lesion-yes' : 'new-lesion-no'">{{ a.has_new_lesion ? '有' : '无' }}</span>
                </div>
                <div class="compare-item" v-if="a.manual_has_new_lesion !== undefined">
                  <span class="source-label">人工</span>
                  <span :class="a.manual_has_new_lesion ? 'new-lesion-yes' : 'new-lesion-no'">{{ a.manual_has_new_lesion ? '有' : '无' }}</span>
                </div>
                <div class="compare-item" v-else>
                  <span class="source-label">人工</span>
                  <span class="no-data">-</span>
                </div>
              </div>
            </div>
            <div class="td">
              <div class="compare-cell">
                <div class="compare-item">
                  <span class="source-label">程序</span>
                  <span class="badge" :class="badgeClass(a.overall_status)">{{ shortStatus(a.overall_status) }}</span>
                </div>
                <div class="compare-item" v-if="a.manual_overall_status">
                  <span class="source-label">人工</span>
                  <span class="badge" :class="badgeClass(a.manual_overall_status)">{{ shortStatus(a.manual_overall_status) }}</span>
                </div>
                <div class="compare-item" v-else>
                  <span class="source-label">人工</span>
                  <span class="no-data">-</span>
                </div>
              </div>
            </div>
            <div class="td reason">{{ a.overall_reason }}</div>
          </div>
        </div>
        <el-pagination v-if="sortedAssessments.length > pageSize" class="pager" background layout="total, sizes, prev, pager, next" :total="sortedAssessments.length" :page-size="pageSize" :page-sizes="[5, 10, 15, 20]" v-model:current-page="page" @size-change="(s) => { pageSize = s; page = 1 }" />
      </div>

      <el-alert
        v-if="!hasAnyLesionDetail"
        class="lesion-tip"
        type="warning"
        :closable="false"
        show-icon
        title="本批次未包含靶/非靶病灶逐病灶明细"
        description="当前导入数据缺少『靶病灶_基线 / 靶病灶 / 非靶病灶_基线 / 非靶病灶 / 新病灶』sheet 中的直径、器官、描述等信息，故下方仅展示 人工评估结论。如需查看逐病灶对比表与按直径的程序评估，请使用含上述 sheet 的完整 EDC Excel 重新导入。"
      />

      <div v-for="a in sortedAssessments" :key="`detail-${a.id}`" class="assessment-detail">
        <h4>📋 {{ a.cycle_number === 1 ? '周期一（基线）病灶明细' : (a.timepoint || `周期${a.cycle_number}`) + ' 病灶明细' }}</h4>

        <el-alert
          v-if="(a.overall_status === 'PD' || a.overall_status === '疾病进展') && a.has_new_lesion"
          type="error"
          :closable="false"
          show-icon
          class="pd-new-lesion-banner"
          title="新病灶触发 PD"
          description="检出新病灶，整体疗效自动判定为疾病进展（PD）。依据 RECIST 1.1：任何新病灶均一票否决为 PD。"
        />

        <!-- 靶病灶：基线 vs 当前 -->
        <div class="detail-block detail-block-full">
          <h5>🎯 靶病灶（基线 vs 当前）</h5>
          <el-table v-if="a.target_lesions?.length" :data="a.target_lesions" border size="small" class="lesion-detail-table">
            <el-table-column label="编号" width="80" align="center" fixed>
              <template #default="{ row }">{{ row.lesion_id || (row.notes || '').replace('EDC编号:', '').trim() || '-' }}</template>
            </el-table-column>
            <el-table-column prop="location" label="所在器官" width="100" />
            <el-table-column prop="description" label="器官具体描述" min-width="120" />
            <!-- 是否检查：基线 / 当前 -->
            <el-table-column label="是否检查" align="center">
              <el-table-column label="基线" width="70" align="center">
                <template #default="{ row }"><span :class="row.is_checked ? 'check-yes' : 'check-no'">{{ row.is_checked ? '是' : (row.is_checked === false ? '否' : '-') }}</span></template>
              </el-table-column>
              <el-table-column label="当前" width="70" align="center">
                <template #default="{ row }"><span :class="row.current_is_checked ? 'check-yes' : 'check-no'">{{ row.current_is_checked ? '是' : (row.current_is_checked === false ? '否' : '-') }}</span></template>
              </el-table-column>
            </el-table-column>
            <!-- 检查日期：基线 / 当前 -->
            <el-table-column label="检查日期" align="center">
              <el-table-column label="基线" width="95" align="center" prop="exam_date" />
              <el-table-column label="当前" width="95" align="center" prop="current_exam_date" />
            </el-table-column>
            <!-- 检查方法：基线 / 当前 -->
            <el-table-column label="检查方法" align="center">
              <el-table-column label="基线" width="95" align="center" prop="exam_method" />
              <el-table-column label="当前" width="95" align="center" prop="current_exam_method" />
            </el-table-column>
            <!-- 其他检查方法：基线 / 当前 -->
            <el-table-column label="其他检查方法" align="center">
              <el-table-column label="基线" width="100" align="center">
                <template #default="{ row }">{{ row.other_exam_method || '-' }}</template>
              </el-table-column>
              <el-table-column label="当前" width="100" align="center">
                <template #default="{ row }">{{ row.current_other_exam_method || '-' }}</template>
              </el-table-column>
            </el-table-column>
            <!-- 分裂/融合：基线 / 当前 -->
            <el-table-column label="分裂/融合" align="center">
              <el-table-column label="基线" width="85" align="center">
                <template #default="{ row }">{{ row.is_split_fused || '-' }}</template>
              </el-table-column>
              <el-table-column label="当前" width="85" align="center">
                <template #default="{ row }">{{ row.current_is_split_fused || '-' }}</template>
              </el-table-column>
            </el-table-column>
            <!-- 靶病灶直径（EDC「所有靶病灶直径和（只读）」汇总值） -->
            <el-table-column align="center">
              <template #header>
                <div class="col-header">
                  <div class="col-title">靶病灶直径</div>
                  <div class="col-sub">= 所有靶病灶直径和(EDC)</div>
                </div>
              </template>
              <el-table-column label="基线" width="100" align="center">
                <template #default="{ row }"><span>{{ fmtNum(a.baseline_sum) }}</span><span class="unit-text">{{ row.size_unit || 'mm' }}</span></template>
              </el-table-column>
              <el-table-column label="当前" width="100" align="center">
                <template #default="{ row }"><span>{{ fmtNum(a.current_sum) }}</span><span class="unit-text">{{ row.size_unit || 'mm' }}</span></template>
              </el-table-column>
            </el-table-column>
            <!-- 最长直径（非淋巴结）/最短直径（淋巴结）：基线 / 当前 -->
            <el-table-column align="center">
              <template #header>
                <div class="col-header">
                  <div class="col-title">最长直径（非淋巴结）/最短直径（淋巴结）</div>
                  <div class="col-sub">= 单病灶实测径(EDC)</div>
                </div>
              </template>
              <el-table-column label="基线" width="105" align="center">
                <template #default="{ row }"><span>{{ fmtNum(row.baseline_size) }}</span><span class="unit-text">{{ row.size_unit || 'mm' }}</span></template>
              </el-table-column>
              <el-table-column label="当前" width="105" align="center">
                <template #default="{ row }"><span>{{ fmtNum(row.current_size) }}</span><span class="unit-text">{{ row.size_unit || 'mm' }}</span></template>
              </el-table-column>
            </el-table-column>
            <el-table-column label="变化" width="75" align="center">
              <template #default="{ row }">{{ lesionChange(row) }}<span class="unit-text">mm</span></template>
            </el-table-column>
            <el-table-column label="变化率" width="80" align="center">
              <template #default="{ row }">
                <span :style="{ color: changeColor(lesionChangePctNum(row)) }">{{ lesionChangePct(row) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="程序判定" width="95" align="center">
              <template #default>
                <span class="badge" :class="badgeClass(a.target_status)" :title="a.target_reason">{{ shortStatus(a.target_status) }}</span>
              </template>
            </el-table-column>
          </el-table>
          <div v-else class="no-lesion">
            <span class="no-data">无逐病灶记录</span>
            <span v-if="a.manual_target_status" class="manual-badge">
              人工评估：<span class="badge" :class="badgeClass(a.manual_target_status)">{{ getStatusText(a.manual_target_status) }}</span>
            </span>
            <span v-else class="no-data">（未提供靶病灶评估）</span>
          </div>
        </div>

        <!-- 非靶病灶：基线 vs 当前 -->
        <div class="detail-block detail-block-full">
          <h5>📍 非靶病灶（基线 vs 当前）</h5>
          <el-table v-if="a.non_target_lesions?.length" :data="a.non_target_lesions" border size="small" class="lesion-detail-table">
            <el-table-column label="编号" width="90" align="center">
              <template #default="{ row }">{{ row.lesion_id || (row.notes || '').replace('EDC编号:', '').trim() || '-' }}</template>
            </el-table-column>
            <el-table-column prop="location" label="所在器官" width="100" />
            <el-table-column prop="description" label="器官具体描述" min-width="120" />
            <!-- 是否检查：基线 / 当前 -->
            <el-table-column label="是否检查" align="center">
              <el-table-column label="基线" width="70" align="center">
                <template #default="{ row }"><span :class="row.baseline_is_checked ? 'check-yes' : 'check-no'">{{ row.baseline_is_checked ? '是' : (row.baseline_is_checked === false ? '否' : '-') }}</span></template>
              </el-table-column>
              <el-table-column label="当前" width="70" align="center">
                <template #default="{ row }"><span :class="row.current_is_checked ? 'check-yes' : 'check-no'">{{ row.current_is_checked ? '是' : (row.current_is_checked === false ? '否' : '-') }}</span></template>
              </el-table-column>
            </el-table-column>
            <!-- 检查日期：基线 / 当前 -->
            <el-table-column label="检查日期" align="center">
              <el-table-column label="基线" width="95" align="center" prop="exam_date" />
              <el-table-column label="当前" width="95" align="center" prop="current_exam_date" />
            </el-table-column>
            <!-- 检查方法：基线 / 当前 -->
            <el-table-column label="检查方法" align="center">
              <el-table-column label="基线" width="95" align="center" prop="exam_method" />
              <el-table-column label="当前" width="95" align="center" prop="current_exam_method" />
            </el-table-column>
            <!-- 状态：基线 / 当前 -->
            <el-table-column label="状态" align="center">
              <el-table-column label="基线" width="90" align="center">
                <template #default="{ row }"><span class="ntl-base">{{ row.baseline_status || '持续存在' }}</span></template>
              </el-table-column>
              <el-table-column label="当前" width="90" align="center">
                <template #default="{ row }"><span class="ntl-status" :class="ntlStatusClass(row.status)">{{ row.status }}</span></template>
              </el-table-column>
            </el-table-column>
            <el-table-column label="程序判定" width="100" align="center">
              <template #default>
                <span class="badge" :class="badgeClass(a.non_target_status)" :title="a.non_target_reason">{{ shortStatus(a.non_target_status) }}</span>
              </template>
            </el-table-column>
          </el-table>
          <div v-else class="no-lesion">
            <span class="no-data">无逐病灶记录</span>
            <span v-if="a.manual_non_target_status" class="manual-badge">
              人工评估：<span class="badge" :class="badgeClass(a.manual_non_target_status)">{{ getStatusText(a.manual_non_target_status) }}</span>
            </span>
            <span v-else class="no-data">（未提供非靶病灶评估）</span>
          </div>
        </div>

        <!-- 新病灶 -->
        <div class="detail-block detail-block-full">
          <h5>✨ 新病灶</h5>
          <div class="new-lesion-info">
            <div class="nl-row">
              <span class="nl-label">程序判定：</span>
              <span :class="a.has_new_lesion ? 'new-lesion-yes' : 'new-lesion-no'">{{ a.has_new_lesion ? '有' : '无' }}</span>
            </div>
            <div class="nl-row" v-if="a.manual_has_new_lesion !== undefined">
              <span class="nl-label">人工判定：</span>
              <span :class="a.manual_has_new_lesion ? 'new-lesion-yes' : 'new-lesion-no'">{{ a.manual_has_new_lesion ? '有' : '无' }}</span>
            </div>
            <span v-if="a.has_new_lesion || a.manual_has_new_lesion" class="new-lesion-note">依据 RECIST 1.1：新病灶出现即判定为 PD</span>
          </div>
          <!-- 优先使用 API 返回的 new_lesions 关联数据，回退到 raw_data -->
          <el-table v-if="(a.new_lesions && a.new_lesions.length) || (a.raw_data?.new_lesion_details?.length)" :data="(a.new_lesions && a.new_lesions.length) ? a.new_lesions : a.raw_data.new_lesion_details" border size="small" class="nl-table lesion-detail-table">
            <el-table-column label="编号" width="90" align="center">
              <template #default="{ row }">{{ row.lesion_id || (row.notes || '').replace('EDC编号:', '') || '-' }}</template>
            </el-table-column>
            <el-table-column prop="location" label="所在器官" width="130" />
            <el-table-column prop="description" label="器官具体描述" min-width="150" />
            <el-table-column prop="exam_date" label="检查日期" width="100" align="center" />
            <el-table-column prop="exam_method" label="检查方法" width="110" align="center" />
            <el-table-column label="其他检查方法" width="120" align="center">
              <template #default="{ row }">{{ row.other_exam_method || '-' }}</template>
            </el-table-column>
          </el-table>
          <div v-else-if="!(a.has_new_lesion || a.manual_has_new_lesion)" class="no-data small">本周期未检出新病灶</div>
        </div>
      </div>
    </div>

    <div v-else class="empty">
      <el-empty description="未找到受试者" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Loading } from '@element-plus/icons-vue'
import { subjectApi } from '../api'
import { getStatusText, getStatusColor } from '../utils/recist'
import ExportMenu from '../components/ExportMenu.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const subject = ref(null)
const page = ref(1)
const pageSize = ref(10)

// SLD Tooltip 状态
const sldTooltip = reactive({
  visible: false,
  type: 'baseline',  // 'baseline' | 'current'
  title: '',
  style: { top: '0px', left: '0px' },
})

const showSldTooltip = (event, type) => {
  const rect = event.target.getBoundingClientRect()
  sldTooltip.type = type
  sldTooltip.title = type === 'baseline' ? '基线 SLD 解释' : '当前 SLD 解释'
  sldTooltip.style = {
    top: (rect.bottom + window.scrollY + 8) + 'px',
    left: (rect.left + window.scrollX - 100) + 'px',
  }
  sldTooltip.visible = true
}

const hideSldTooltip = () => {
  sldTooltip.visible = false
}

const routeBatchId = computed(() => {
  const b = route.query.batch
  return b !== undefined && b !== null && b !== '' ? Number(b) : null
})

const formatDate = (dt) => {
  if (!dt) return '-'
  return new Date(dt).toLocaleDateString('zh-CN')
}

const loadSubject = async () => {
  // keep-alive 下从详情导航到列表（/subjects，无 id 参数）时 route.params.id 为 undefined，跳过请求
  if (!route.params.id) {
    loading.value = false
    return
  }
  loading.value = true
  try {
    subject.value = await subjectApi.get(route.params.id, { batch_id: routeBatchId.value })
  } catch (e) {
    console.error(e)
    ElMessage.error('加载受试者详情失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => { loadSubject() })

// 因 Layout 使用 <keep-alive> 缓存路由组件，onMounted 只在首次挂载时执行一次。
// 若用户在同一缓存实例内切换不同受试者（route.params.id 变化），必须重新拉取，
// 否则会展示上一次加载的受试者（头像/标题/各周期病灶明细全部错乱）。
watch(
  () => route.params.id,
  (id) => {
    if (!id) return
    page.value = 1
    loadSubject()
  }
)

const sortedAssessments = computed(() => {
  if (!subject.value?.assessments) return []
  let list = [...subject.value.assessments]
  if (routeBatchId.value !== null) {
    list = list.filter(a => a.batch_id === routeBatchId.value)
  }
  list.sort((a, b) => (a.cycle_number || 0) - (b.cycle_number || 0))
  return list.map(a => ({ ...a, timepoint: a.raw_data?.timepoint || `周期${a.cycle_number}` }))
})

// 最近一次评估（用于"最近评估"日期与"总体疗效评估"展示）
const latestAssessment = computed(() => {
  const list = sortedAssessments.value
  return list.length ? list[list.length - 1] : null
})

// Excel 中的"总体疗效评估"（人工判定），缺省时回退到程序判定
const latestOverallStatus = computed(() => {
  const a = latestAssessment.value
  if (!a) return null
  return a.manual_overall_status || a.overall_status || null
})

const latestOverallText = computed(() => {
  const s = latestOverallStatus.value
  return s ? getStatusText(s) : '-'
})

// 本受试者是否存在任何逐病灶明细（决定是否显示"无明细"引导）
const hasAnyLesionDetail = computed(() =>
  sortedAssessments.value.some(a =>
    (a.target_lesions && a.target_lesions.length) ||
    (a.non_target_lesions && a.non_target_lesions.length) ||
    (a.new_lesions && a.new_lesions.length) ||
    ((a.raw_data?.new_lesion_details || []).length)
  )
)

const pagedAssessments = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return sortedAssessments.value.slice(start, start + pageSize.value)
})

const shortStatus = (s) => {
  const map = {
    '完全缓解': 'CR', '部分缓解': 'PR', '疾病稳定': 'SD', '疾病进展': 'PD',
    '无法评估': 'NE', '非完全缓解/非疾病进展': '非完全缓解(Non-CR)/非疾病进展(Non-PD)', 'Non-CR/Non-PD': '非完全缓解(Non-CR)/非疾病进展(Non-PD)', '不适用': 'N/A'
  }
  return map[getStatusText(s)] || s || 'NE'
}

const badgeClass = (status) => {
  const map = { CR: 'badge-cr', PR: 'badge-pr', SD: 'badge-sd', PD: 'badge-pd', NE: 'badge-ne', 'Non-CR/Non-PD': 'badge-ncnp', '非完全缓解(Non-CR)/非疾病进展(Non-PD)': 'badge-ncnp', '不适用': 'badge-na', '不适用（NA）': 'badge-na' }
  return map[status] || 'badge-ne'
}

const changeColor = (percent) => {
  if (percent <= -30) return '#67c23a'
  if (percent >= 20) return '#f56c6c'
  return '#e6a23c'
}

// 病灶明细辅助
const fmtNum = (v) => (v !== null && v !== undefined && v !== '') ? Number(v).toFixed(1) : '-'

const lesionChange = (row) => {
  const b = Number(row.baseline_size) || 0
  const c = Number(row.current_size) || 0
  const d = c - b
  if (!d) return '0.0'
  return (d > 0 ? '+' : '') + d.toFixed(1)
}

const lesionChangePct = (row) => {
  const b = Number(row.baseline_size) || 0
  const c = Number(row.current_size) || 0
  if (!b) return '0.0%'
  const pct = ((c - b) / b) * 100
  return (pct > 0 ? '+' : '') + pct.toFixed(1) + '%'
}

// 返回数值（用于颜色判断）
const lesionChangePctNum = (row) => {
  const b = Number(row.baseline_size) || 0
  const c = Number(row.current_size) || 0
  if (!b) return 0
  return ((c - b) / b) * 100
}

const ntlStatusClass = (status) => {
  if (status === '消失') return 'ntl-gone'
  if (status === '进展') return 'ntl-prog'
  return 'ntl-persist'
}

const showAssessmentDetail = (a) => {}

const exportRows = computed(() => sortedAssessments.value.map(a => {
  const hasManual = !!(a.manual_overall_status || a.manual_target_status || a.manual_non_target_status)
  const overallMatch = hasManual ? (a.overall_status === a.manual_overall_status) : undefined
  return { ...a, subject_id: subject.value?.subject_id, subject_name: subject.value?.name, has_manual_data: hasManual, overall_match: overallMatch }
}))

const exportFilename = computed(() => `受试者${subject.value?.subject_id || '未知'}_详细数据`)
const exportTitle = computed(() => `受试者 ${subject.value?.subject_id || '未知'} 评估报告`)
const exportSubtitle = computed(() => {
  const s = subject.value
  if (!s) return ''
  const gender = s.gender || '-'
  const age = s.age ? s.age + '岁' : '-'
  const diagnosis = s.diagnosis || '-'
  return `诊断：${diagnosis}`
})
</script>

<style scoped>
.report-container {
  max-width: 1400px;
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
  flex: 1;
  font-size: 28px;
  color: var(--text-primary);
  margin: 0;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.loading, .empty {
  text-align: center;
  padding: 80px;
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.subject-info-card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-lg);
  border: 1px solid var(--border-light);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-md);
  border-bottom: 2px solid var(--border-light);
}

.card-icon { font-size: 24px; }
.card-header h3 { font-size: 18px; color: var(--text-primary); margin: 0; font-weight: 600; }

.info-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-lg);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-label { font-size: 13px; color: var(--text-secondary); }
.info-value { font-size: 16px; color: var(--text-primary); font-weight: 500; }

.gender-male { color: var(--primary-color); }
.gender-female { color: var(--danger-color); }

.timepoint-section {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-lg);
  border: 1px solid var(--border-light);
}

.section-header h3 {
  font-size: 18px;
  color: var(--text-primary);
  margin-bottom: var(--spacing-lg);
  font-weight: 600;
}

.timepoint-table {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.table-header-row, .table-row {
  display: grid;
  grid-template-columns: 90px 100px 90px 70px 160px 160px 90px 120px 1fr;
  align-items: stretch;
}

.table-header-row {
  background: var(--bg-color);
  font-weight: 600;
  color: var(--text-regular);
  font-size: 13px;
}

.table-row {
  background: #fff;
  cursor: pointer;
  transition: background 0.2s;
}

.table-row:hover { background: #fafafa; }

.th {
  padding: 10px 10px;
  border-right: 1px solid #c0c4cc;
  border-bottom: 1px solid #c0c4cc;
  display: block;
  text-align: center;
  min-height: 48px;
  line-height: 1.6;
}

.td {
  padding: 10px 10px;
  border-right: 1px solid #c0c4cc;
  border-bottom: 1px solid #c0c4cc;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
}

.td:last-child, .th:last-child { border-right: none; }
.table-row:last-child .td { border-bottom: none; }

.td.reason {
  justify-content: flex-start;
  color: #606266;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}

.compare-cell { 
  display: flex; 
  align-items: center; 
  justify-content: center;
  gap: 12px; 
}

.compare-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
}

.source-label { font-size: 10px; color: #909399; line-height: 1; }

.th-sub-inline { 
  font-size: 11px; 
  font-weight: 400; 
  color: #909399;
}

.no-data {
  font-size: 12px;
  color: #c0c4cc;
}

.new-lesion-yes {
  color: #f56c6c;
  font-weight: 600;
  font-size: 12px;
}

.new-lesion-no {
  color: #67c23a;
  font-weight: 600;
  font-size: 12px;
}

.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  padding: 3px 8px;
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
.badge-pd { background: #f5f7fa; color: #f56c6c; border: 1px solid #f56c6c; }
.badge-ne { background: #909399; }
.badge-ncnp { background: #9ca3af; }
.badge-na { background: #c0c4cc; }

.pager { margin-top: 20px; justify-content: flex-end; }

.assessment-detail {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-lg);
  border: 1px solid var(--border-light);
}

.assessment-detail h4 {
  font-size: 16px;
  margin-bottom: var(--spacing-lg);
  color: var(--text-primary);
  border-left: 4px solid var(--primary-color);
  padding-left: 12px;
  font-weight: 600;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-xl);
}

.detail-block h5 {
  font-size: 14px;
  color: var(--text-regular);
  margin-bottom: var(--spacing-md);
  font-weight: 500;
}

.no-data {
  text-align: center;
  padding: 24px;
  background: var(--bg-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
}

.new-lesion-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: var(--spacing-md);
  background: var(--danger-light);
  border-radius: var(--radius-md);
}

.no-lesion {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: var(--spacing-md);
  background: var(--bg-color);
  border-radius: var(--radius-md);
}

.manual-badge {
  font-size: 13px;
  color: var(--text-regular);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.nl-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.nl-label {
  color: var(--text-secondary);
  font-size: 13px;
}

.new-lesion-note {
  font-size: 13px;
  color: var(--text-secondary);
}

.detail-block-full {
  width: 100%;
  margin-bottom: var(--spacing-lg);
}

.detail-block-full h5 {
  font-size: 14px;
  color: var(--text-regular);
  margin-bottom: var(--spacing-md);
  font-weight: 500;
}

.lesion-tip {
  margin-bottom: var(--spacing-lg);
}

.pd-new-lesion-banner {
  margin-bottom: var(--spacing-lg);
}

.nl-table {
  margin-top: var(--spacing-md);
}

.no-data.small {
  padding: 12px;
  font-size: 13px;
}

.ntl-base {
  color: var(--text-secondary);
  font-size: 13px;
}

.ntl-status { font-size: 13px; font-weight: 600; }
.ntl-gone { color: #67c23a; }
.ntl-persist { color: #e6a23c; }
.ntl-prog { color: #f56c6c; }

/* ===== SLD Tooltip ===== */
.sld-tooltip-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 11px;
  font-weight: bold;
  cursor: help;
  margin-left: 4px;
  vertical-align: middle;
  line-height: 1;
}

.sld-tooltip {
  position: absolute;
  z-index: 9999;
  width: 380px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  box-shadow: 0 8px 30px rgba(0,0,0,0.15);
  padding: 0;
  overflow: hidden;
  animation: sld-fade-in 0.15s ease-out;
}

@keyframes sld-fade-in {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.sld-tooltip-title {
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
  padding: 10px 14px;
  font-size: 14px;
  font-weight: 600;
}

.sld-tooltip-content {
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.7;
  color: #303133;
}

.sld-tooltip-content p { margin: 6px 0; }
.sld-tooltip-content strong { color: #409eff; }
.sld-tooltip-content ul { margin: 6px 0; padding-left: 18px; }
.sld-tooltip-content li { margin: 3px 0; }
.sld-tooltip-content hr { border: none; border-top: 1px solid #ebeef5; margin: 8px 0; }

.sld-tip-formula {
  background: #f5f7fa;
  padding: 6px 10px;
  border-radius: 6px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #606266;
  text-align: center;
  margin: 8px 0;
}

/* ===== 病灶详情表格增强 ===== */
.lesion-detail-table .el-table__cell { padding: 4px 0 !important; }
.unit-text { font-size: 11px; color: #909399; margin-left: 2px; }

.col-header { display: flex; flex-direction: column; align-items: center; justify-content: center; line-height: 1.25; }
.col-title { font-size: 13px; font-weight: 600; }
.col-sub { font-size: 11px; color: #909399; margin-top: 2px; font-weight: 400; }

.check-yes { color: #67c23a; font-weight: 500; font-size: 13px; }
.check-no { color: #f56c6c; font-weight: 500; font-size: 13px; }

@media (max-width: 1200px) {
  .info-grid { grid-template-columns: repeat(3, 1fr); }
  .table-header, .table-row { grid-template-columns: 100px 120px 80px 80px 70px 120px 90px 120px 1fr; }
  .detail-grid { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .info-grid { grid-template-columns: repeat(2, 1fr); }
  .table-header, .table-row { display: block; }
  .table-header { display: none; }
  .table-row { margin-bottom: 12px; border: 1px solid #ebeef5; border-radius: 8px; }
}
</style>