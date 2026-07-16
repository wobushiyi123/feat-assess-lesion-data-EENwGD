<template>
  <div class="standard-container">
    <div class="page-header">
      <h2>RECIST 1.1 评估标准</h2>
      <p class="header-subtitle">实体瘤疗效评价标准（Response Evaluation Criteria in Solid Tumors）第 1.1 版</p>
    </div>

    <div class="standard-content">

      <!-- ═══════════════ 6.1 靶病灶判定 ═══════════════ -->
      <div class="section target-section">
        <h3 class="section-title">6.1 靶病灶判定</h3>

        <!-- 判定标准表 -->
        <div class="standard-table">
          <table>
            <thead>
              <tr><th>类别</th><th>判定标准</th></tr>
            </thead>
            <tbody>
              <tr>
                <td><span class="badge cr">CR 完全缓解</span></td>
                <td>所有靶病灶消失；所有病理淋巴结短轴 &lt; 10 mm</td>
              </tr>
              <tr>
                <td><span class="badge pr">PR 部分缓解</span></td>
                <td>靶病灶 SLD 较基线下降 ≥30%</td>
              </tr>
              <tr>
                <td><span class="badge sd">SD 疾病稳定</span></td>
                <td>既达不到 PR（缩小不足），也未达 PD（增大不足），介于两者之间</td>
              </tr>
              <tr>
                <td><span class="badge pd">PD 疾病进展</span></td>
                <td>
                  满足以下任一：<br/>
                  ① SLD 较研究期间最小值（nadir，含基线）增加 <strong>≥20%</strong> 且绝对值增加 <strong>≥5 mm</strong>；<br/>
                  ② 出现新病灶
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 公式框 -->
        <div class="formula-box">
          <div class="formula-line"><code>SLD_baseline = Σ 各靶病灶最长径（基线）</code></div>
          <div class="formula-line"><code>SLD_nadir = min(SLD_baseline, SLD_followup_1, SLD_followup_2, …)</code></div>
          <div class="formula-line"><code>PR：(SLD_baseline − SLD_now) / SLD_baseline ≥ 0.30</code></div>
          <div class="formula-line"><code>PD：(SLD_now − SLD_nadir) / SLD_nadir ≥ 0.20 AND (SLD_now − SLD_nadir) ≥ 5 mm → 或 出现新病灶</code></div>
        </div>

        <!-- 三个极易出错的细节 -->
        <div class="warning-box">
          <h4>⚠️ 三个极易出错的细节</h4>
          <ol>
            <li><strong>PD 参照是 nadir（最低值），不是基线。</strong><br/>
              例：基线 100 → 最低 50 → 复查 60：相对最低值 +20%（=+60）且绝对 +10mm≥5 → 判 PD。<br/>
              若回升到 58（+16%&lt;20%）则仍 SD。
            </li>
            <li><strong>PD 双条件缺一不可：</strong>既需相对 +20%，又需绝对 +5 mm。<br/>小病灶微小波动不应误判为进展。</li>
            <li><strong>新病灶 = PD，</strong>无论大小、无论出现在何处（含 FDG-PET 发现）。</li>
          </ol>
        </div>
      </div>

      <!-- ═══════════════ 6.2 非靶病灶判定 ═══════════════ -->
      <div class="section non-target-section">
        <h3 class="section-title">6.2 非靶病灶判定</h3>

        <div class="standard-table">
          <table>
            <thead>
              <tr><th>类别</th><th>判定标准</th></tr>
            </thead>
            <tbody>
              <tr>
                <td><span class="badge cr">CR</span></td>
                <td>所有非靶病灶消失；所有淋巴结短轴 &lt; 10 mm</td>
              </tr>
              <tr>
                <td><span class="badge sd">非CR/非PD (IR/SD)</span></td>
                <td>存在 ≥1 个非靶病灶，或肿瘤标志物持续高于正常</td>
              </tr>
              <tr>
                <td><span class="badge pd">PD</span></td>
                <td>已有非靶病灶明确进展，或出现任何新病灶</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="note-box">
          <p><strong>非靶 PD 的"明确"二字：</strong>非靶病灶的轻微增大不构成 PD，必须是<strong>明确（unequivocal）进展</strong>（如胸水从少量到大量、淋巴管炎从局限到弥漫）。系统实现时切忌把非靶尺寸小幅变化自动判为 PD。</p>
        </div>
      </div>

      <!-- ═══════════════ 6.3 确认规则 ═══════════════ -->
      <div class="section confirmation-section">
        <h3 class="section-title">6.3 确认规则（Confirmation）</h3>

        <ul class="confirm-list">
          <li>在<strong>非随机试验</strong>中，<strong>CR 与 PR</strong>须在治疗后 <strong>≥4 周</strong>复查确认。</li>
          <li><strong>随机试验</strong>可由方案决定是否需确认（多数不强制），但确认性的 PR 在后续访视中视为<strong>"持续 PR"</strong>，直至满足 PD 标准——后续判定参照 <strong>nadir 而非基线</strong>。</li>
          <li><strong>PD 一般不需确认</strong>（除非征象模棱两可）。</li>
        </ul>
      </div>

      <!-- ═══════════════ 判定流程图（图1）═══════════════ -->
      <div class="section flowchart-section">
        <h3 class="section-title">图 1 · 靶病灶疗效判定流程图</h3>

        <div class="flowchart">
          <div class="fc-node fc-start">计算 SLD（最长径之和）</div>
          <div class="fc-arrow-down"></div>

          <div class="fc-row">
            <div class="fc-branch fc-question">所有靶病灶消失？</div>
            <div class="fc-arrow-right"></div>
            <div class="fc-result fc-cr">CR（节点 &lt;10mm）</div>
          </div>
          <div class="fc-arrow-down fc-from-left"></div>

          <div class="fc-row">
            <div class="fc-branch fc-question">SLD 较基线 ↓≥30%？</div>
            <div class="fc-arrow-right"></div>
            <div class="fc-result fc-pr">PR</div>
          </div>
          <div class="fc-arrow-down fc-from-left"></div>

          <div class="fc-row">
            <div class="fc-branch fc-question">较 nadir ↑≥20% 且 绝对↑≥5mm<br/>或新病灶？</div>
            <div class="fc-arrow-right"></div>
            <div class="fc-result fc-pd">PD</div>
          </div>
          <div class="fc-arrow-down fc-from-left"></div>
          <div class="fc-row">
            <div class="fc-branch fc-empty"></div>
            <div class="fc-arrow-right"></div>
            <div class="fc-result fc-sd">SD（介于 PR 与 PD 之间）</div>
          </div>
          <div class="fc-arrow-down"></div>

          <div class="fc-node fc-end">再与非靶病灶结果合并 → 总体疗效</div>
        </div>

        <p class="flowchart-note">靶病灶疗效判定依赖 <strong>SLD 与 nadir 的比较</strong>：CR 优先判定，其次依次为 PR、PD，余者为 SD。</p>
      </div>

      <!-- ═══════════════ 整体评价决策矩阵 ═══════════════ -->
      <div class="section matrix-section">
        <h3 class="section-title">整体评价决策矩阵</h3>

        <div class="standard-table matrix-table">
          <table>
            <thead>
              <tr>
                <th>Target 靶病灶</th>
                <th>Non-Target 非靶病灶</th>
                <th>New Lesion 新病灶</th>
                <th>Overall 整体疗效</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>CR</td><td>CR</td><td>No</td><td><span class="badge cr">CR</span></td></tr>
              <tr><td>CR</td><td>Non-CR/Non-PD</td><td>No</td><td><span class="badge pr">PR</span></td></tr>
              <tr><td>PR</td><td>Non-CR/Non-PD or CR</td><td>No</td><td><span class="badge pr">PR</span></td></tr>
              <tr><td>SD</td><td>Non-CR/Non-PD or CR</td><td>No</td><td><span class="badge sd">SD</span></td></tr>
              <tr><td>PD</td><td>Any</td><td>No / Yes</td><td><span class="badge pd">PD</span></td></tr>
              <tr><td>Any</td><td>PD</td><td>No / Yes</td><td><span class="badge pd">PD</span></td></tr>
              <tr><td>Any</td><td>Any</td><td>Yes</td><td><span class="badge pd">PD</span> ← 最高优先级</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ═══════════════ 关键概念 ═══════════════ -->
      <div class="section concepts-section">
        <h3 class="section-title">关键概念</h3>
        <div class="concept-grid">
          <div class="concept-card">
            <h4>SLD（最长径之和）</h4>
            <p>Sum of Longest Diameters —— 所有靶病灶最长直径之和。每次访视计算一次，用于与基线和历史最低值比较。</p>
          </div>
          <div class="concept-card">
            <h4>Nadir（研究期间最低值）</h4>
            <p>SLD_nadir = min(基线, 第1次随访, 第2次随访, ...)。PD 判定的参照基准是 <strong>nadir 不是基线</strong>。</p>
          </div>
          <div class="concept-card">
            <h4>明确进展（Unequivocal）</h4>
            <p>仅用于非靶病灶 PD 判定。要求"明确"的客观进展证据（如胸水明显增多），轻微尺寸变化不构成 PD。</p>
          </div>
          <div class="concept-card">
            <h4>新病灶（New Lesion）</h4>
            <p>治疗过程中新出现的任何病灶，无论大小、位置、发现方式（含 FDG-PET）。一旦确认即判为 PD（最高优先级一票否决）。</p>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
// RECIST 1.1 标准展示页 — 完全对齐用户提供的 6.1/6.2/6.3 三张标准图
</script>

<style scoped>
.standard-container {
  max-width: 960px;
  margin: 0 auto;
  padding-bottom: 40px;
}

.page-header {
  text-align: center;
  margin-bottom: var(--spacing-xl);
}
.page-header h2 {
  font-size: 26px;
  color: var(--text-primary);
  font-weight: 700;
  margin-bottom: 8px;
}
.header-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
}

.standard-content {
  background: var(--card-bg);
  padding: var(--spacing-xl);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-light);
}

.section {
  margin-bottom: 36px;
}
.section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--primary-color);
}

/* ── 表格 ── */
.standard-table { overflow-x: auto; }
.standard-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.standard-table th, .standard-table td {
  padding: 12px 16px;
  border: 1px solid var(--border-color);
  text-align: left;
  vertical-align: top;
}
.standard-table th {
  background: #f5f7fa;
  font-weight: 600;
  white-space: nowrap;
}
.standard-table td { color: var(--text-regular); line-height: 1.6; }

.matrix-table td, .matrix-table th { text-align: center; }

/* ── Badge ── */
.badge {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}
.badge.cr  { background: #f0f9eb; color: #67c23a; }
.badge.pr  { background: #ecf5ff; color: #409eff; }
.badge.sd  { background: #fdf6ec; color: #e6a23c; }
.badge.pd  { background: #fef0f0; color: #f56c6c; }

/* ── 公式框 ── */
.formula-box {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 18px 22px;
  border-radius: 8px;
  font-family: 'Courier New', Consolas, monospace;
  font-size: 13.5px;
  line-height: 1.9;
  margin-top: 16px;
}
.formula-line { margin: 4px 0; }
.formula-box code { color: #ce9178; }

/* ── 警告框 ── */
.warning-box {
  background: #fdf6ec;
  border: 1px solid #faecd8;
  border-radius: 8px;
  padding: 16px 20px;
  margin-top: 16px;
}
.warning-box h4 {
  color: #e6a23c;
  font-size: 15px;
  margin: 0 0 10px;
}
.warning-box ol {
  margin: 0;
  padding-left: 20px;
  color: var(--text-regular);
  font-size: 14px;
  line-height: 1.75;
}
.warning-box li { margin-bottom: 8px; }
.warning-box li:last-child { margin-bottom: 0; }

/* ── 提示框 ── */
.note-box {
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  border-radius: 8px;
  padding: 14px 18px;
  margin-top: 16px;
  font-size: 14px;
  line-height: 1.65;
  color: var(--text-regular);
}

/* ── 确认规则列表 ── */
.confirm-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.confirm-list li {
  position: relative;
  padding: 10px 0 10px 24px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-regular);
  border-bottom: 1px dashed var(--border-light);
}
.confirm-list li:last-child { border-bottom: none; }
.confirm-list li::before {
  content: '•';
  position: absolute;
  left: 8px;
  color: var(--primary-color);
  font-weight: bold;
  font-size: 16px;
}

/* ── 流程图 ── */
.flowchart {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 0;
  gap: 4px;
}
.fc-node {
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: white;
  padding: 12px 28px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 14.5px;
  text-align: center;
  min-width: 220px;
}
.fc-end {
  background: linear-gradient(135deg, #303133, #1d1e1f);
}
.fc-arrow-down {
  width: 0; height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-top: 12px solid #909399;
  margin: 4px 0;
}
.fc-arrow-down.fc-from-left { margin-left: calc(50% - 160px); }

.fc-row {
  display: flex;
  align-items: center;
  gap: 0;
}
.fc-branch {
  min-width: 260px;
  padding: 11px 18px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  text-align: center;
  background: #f5f7fa;
  border: 1px solid #dcdfe6;
  color: var(--text-primary);
  line-height: 1.5;
}
.fc-empty { visibility: hidden; }
.fc-arrow-right {
  width: 0; height: 0;
  border-top: 8px solid transparent;
  border-bottom: 8px solid transparent;
  border-left: 14px solid #909399;
}
.fc-result {
  min-width: 100px;
  padding: 10px 20px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 14px;
  text-align: center;
  color: white;
}
.fc-cr   { background: #67c23a; }
.fc-pr   { background: #409eff; }
.fc-sd   { background: #e6a23c; }
.fc-pd   { background: #f56c6c; }

.flowchart-note {
  margin-top: 14px;
  font-size: 13px;
  color: var(--text-secondary);
  text-align: center;
  line-height: 1.6;
}

/* ── 概念网格 ── */
.concept-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.concept-card {
  background: var(--bg-color);
  border: 1px solid var(--border-light);
  border-radius: 8px;
  padding: 16px 18px;
}
.concept-card h4 {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--primary-color);
  margin: 0 0 8px;
}
.concept-card p {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.65;
  margin: 0;
}

@media (max-width: 768px) {
  .concept-grid { grid-template-columns: 1fr; }
  .fc-row { flex-direction: column; }
  .fc-arrow-right { display: none; }
  .fc-arrow-down.fc-from-left { margin-left: 0; }
  .standard-table table { font-size: 13px; }
}
</style>
