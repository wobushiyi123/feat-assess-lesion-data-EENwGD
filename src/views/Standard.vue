<template>
  <div class="standard-container">
    <div class="page-header">
      <h2>RECIST评估标准</h2>
    </div>

    <div class="standard-content">
      <div class="intro-section">
        <h3>关于RECIST标准</h3>
        <p>
          RECIST (Response Evaluation Criteria in Solid Tumors) 是用于评估实体肿瘤治疗效果的标准。
          该标准通过测量肿瘤病灶的大小变化来判断治疗反应。
        </p>
      </div>

      <div class="criteria-section">
        <h3>评估类别定义</h3>
        <div class="criteria-grid">
          <div class="criteria-card cr">
            <div class="criteria-code">CR</div>
            <div class="criteria-name">完全缓解</div>
            <div class="criteria-desc">所有靶病灶消失，且持续至少4周</div>
          </div>
          <div class="criteria-card pr">
            <div class="criteria-code">PR</div>
            <div class="criteria-name">部分缓解</div>
            <div class="criteria-desc">靶病灶最长径总和减少≥30%，持续至少4周</div>
          </div>
          <div class="criteria-card sd">
            <div class="criteria-code">SD</div>
            <div class="criteria-name">病情稳定</div>
            <div class="criteria-desc">靶病灶变化介于PR和PD之间</div>
          </div>
          <div class="criteria-card pd">
            <div class="criteria-code">PD</div>
            <div class="criteria-name">疾病进展</div>
            <div class="criteria-desc">靶病灶最长径总和增加≥20%且绝对值增加≥5mm，或出现新病灶</div>
          </div>
        </div>
      </div>

      <div class="target-section">
        <h3>靶病灶评估标准</h3>
        <div class="standard-table">
          <table>
            <thead>
              <tr>
                <th>评估结果</th>
                <th>判断标准</th>
                <th>说明</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><span class="status-badge cr">CR</span></td>
                <td>所有靶病灶消失</td>
                <td>靶病灶最长径总和为0</td>
              </tr>
              <tr>
                <td><span class="status-badge pr">PR</span></td>
                <td>最长径总和减少≥30%</td>
                <td>与基线相比，减少≥30%</td>
              </tr>
              <tr>
                <td><span class="status-badge sd">SD</span></td>
                <td>变化介于PR和PD之间</td>
                <td>减少&lt;30%且增加&lt;20%</td>
              </tr>
              <tr>
                <td><span class="status-badge pd">PD</span></td>
                <td>最长径总和增加≥20%且绝对值增加≥5mm</td>
                <td>同时满足两个条件</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="non-target-section">
        <h3>非靶病灶评估标准</h3>
        <div class="standard-table">
          <table>
            <thead>
              <tr>
                <th>评估结果</th>
                <th>判断标准</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><span class="status-badge cr">CR</span></td>
                <td>所有非靶病灶消失，且肿瘤标志物水平正常</td>
              </tr>
              <tr>
                <td><span class="status-badge sd">SD</span></td>
                <td>存在一个或多个非靶病灶持续存在，或肿瘤标志物水平高于正常</td>
              </tr>
              <tr>
                <td><span class="status-badge pd">PD</span></td>
                <td>出现一个或多个新病灶，或明确的非靶病灶进展</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="new-lesion-section">
        <h3>新病灶评估标准</h3>
        <div class="standard-table">
          <table>
            <thead>
              <tr>
                <th>评估结果</th>
                <th>判断标准</th>
                <th>说明</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><span class="status-badge cr">未检出</span></td>
                <td>随访影像学检查未发现既往未记录的可疑病灶</td>
                <td>不影响整体疗效评价</td>
              </tr>
              <tr>
                <td><span class="status-badge pd">检出</span></td>
                <td>影像学发现既往未记录的可疑病灶</td>
                <td>新病灶一经确认，整体评价直接判定为 <span class="status-badge pd">PD</span></td>
              </tr>
              <tr>
                <td><span class="status-badge pd">确认</span></td>
                <td>后续评估中病灶持续存在或明确增大</td>
                <td>需排除假阳性或炎症性病灶；不纳入靶病灶最长径总和</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="overall-section">
        <h3>整体疗效评价规则</h3>
        <div class="rule-list">
          <div class="rule-item">
            <span class="rule-number">1</span>
            <span class="rule-text">只要出现新病灶，整体评价为 <span class="status-badge pd">PD</span></span>
          </div>
          <div class="rule-item">
            <span class="rule-number">2</span>
            <span class="rule-text">非靶病灶明确进展，整体评价为 <span class="status-badge pd">PD</span></span>
          </div>
          <div class="rule-item">
            <span class="rule-number">3</span>
            <span class="rule-text">靶病灶和非靶病灶均CR，整体评价为 <span class="status-badge cr">CR</span></span>
          </div>
          <div class="rule-item">
            <span class="rule-number">4</span>
            <span class="rule-text">靶病灶CR且非靶病灶未进展，整体评价为 <span class="status-badge cr">CR</span></span>
          </div>
          <div class="rule-item">
            <span class="rule-number">5</span>
            <span class="rule-text">靶病灶PR，整体评价为 <span class="status-badge pr">PR</span></span>
          </div>
          <div class="rule-item">
            <span class="rule-number">6</span>
            <span class="rule-text">靶病灶SD，整体评价为 <span class="status-badge sd">SD</span></span>
          </div>
          <div class="rule-item">
            <span class="rule-number">7</span>
            <span class="rule-text">靶病灶PD，整体评价为 <span class="status-badge pd">PD</span></span>
          </div>
        </div>
      </div>

      <div class="notes-section">
        <h3>注意事项</h3>
        <ul>
          <li>基线评估时需确定靶病灶（最多5个器官，每个器官最多2个病灶）</li>
          <li>靶病灶最长径总和用于评估，而非靶病灶仅做定性评估</li>
          <li>首次评估需在治疗开始后至少6-8周进行</li>
          <li>确认缓解需在首次评估后至少4周再次确认</li>
          <li>PD的确认也需要在首次评估后至少4周再次确认（除非出现危及生命的进展）</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.standard-container {
  max-width: 1000px;
  margin: 0 auto;
  padding-bottom: 40px;
}

.page-header h2 {
  font-size: 28px;
  color: var(--text-primary);
  margin-bottom: var(--spacing-xl);
  font-weight: 700;
  letter-spacing: -0.5px;
}

.standard-content {
  background: var(--card-bg);
  padding: var(--spacing-xl);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-light);
}

.intro-section, .criteria-section, .target-section, .non-target-section, .new-lesion-section, .overall-section, .notes-section {
  margin-bottom: var(--spacing-xl);
}

.intro-section h3, .criteria-section h3, .target-section h3, .non-target-section h3, .new-lesion-section h3, .overall-section h3, .notes-section h3 {
  font-size: 18px;
  color: var(--text-primary);
  margin-bottom: var(--spacing-md);
  padding-bottom: 8px;
  border-bottom: 2px solid var(--primary-color);
  font-weight: 600;
}

.intro-section p {
  font-size: 16px;
  color: var(--text-regular);
  line-height: 1.8;
}

.criteria-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-lg);
}

.criteria-card {
  padding: var(--spacing-xl);
  border-radius: var(--radius-lg);
  text-align: center;
  border: 1px solid var(--border-light);
}

.criteria-card.cr { background-color: var(--success-light); }
.criteria-card.pr { background-color: var(--primary-light); }
.criteria-card.sd { background-color: var(--warning-light); }
.criteria-card.pd { background-color: var(--danger-light); }

.criteria-code {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
}

.criteria-card.cr .criteria-code { color: var(--success-color); }
.criteria-card.pr .criteria-code { color: var(--primary-color); }
.criteria-card.sd .criteria-code { color: var(--warning-color); }
.criteria-card.pd .criteria-code { color: var(--danger-color); }

.criteria-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.criteria-desc {
  font-size: 13px;
  color: var(--text-regular);
  line-height: 1.5;
}

.standard-table table {
  width: 100%;
  border-collapse: collapse;
}

.standard-table th, .standard-table td {
  padding: 12px 16px;
  border: 1px solid var(--border-color);
  text-align: left;
}

.standard-table th {
  background-color: var(--bg-color);
  font-weight: 600;
  color: var(--text-primary);
}

.standard-table td {
  color: var(--text-regular);
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  color: white;
  font-size: 12px;
  font-weight: 600;
}

.status-badge.cr { background-color: var(--success-color); }
.status-badge.pr { background-color: var(--primary-color); }
.status-badge.sd { background-color: var(--warning-color); }
.status-badge.pd { background-color: var(--danger-color); }

.rule-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.rule-item {
  display: flex;
  align-items: flex-start;
  padding: var(--spacing-md);
  background-color: var(--bg-color);
  border-radius: var(--radius-md);
}

.rule-number {
  width: 28px;
  height: 28px;
  background: var(--primary-gradient);
  color: white;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  margin-right: var(--spacing-md);
  flex-shrink: 0;
}

.rule-text {
  font-size: 14px;
  color: var(--text-regular);
  line-height: 1.6;
}

.notes-section ul {
  list-style: none;
  padding: 0;
}

.notes-section li {
  position: relative;
  padding: 10px 0 10px 24px;
  font-size: 14px;
  color: var(--text-regular);
  border-bottom: 1px dashed var(--border-light);
}

.notes-section li:last-child {
  border-bottom: none;
}

.notes-section li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--primary-color);
  font-weight: bold;
}

@media (max-width: 768px) {
  .criteria-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .standard-table {
    overflow-x: auto;
  }
}
</style>