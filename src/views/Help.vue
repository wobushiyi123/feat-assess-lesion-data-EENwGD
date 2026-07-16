<template>
  <div class="help-container">
    <div class="page-header">
      <h2>使用帮助</h2>
      <p class="header-subtitle">RECIST 病灶评估系统 · 操作指引与常见问题</p>
      <div class="header-actions">
        <el-button type="primary" :icon="Document" @click="onDownloadDoc">下载 DOC</el-button>
      </div>
    </div>

    <div class="help-content" ref="printArea">

      <!-- 1. 系统简介 -->
      <div class="card-wrapper">
        <h2 class="section-title">一、系统简介</h2>
        <p>
          RECIST 病灶评估系统是一套基于 <strong>RECIST 1.1（实体瘤疗效评价标准第 1.1 版）</strong>
          的肿瘤疗效评估平台。系统支持从 Excel 批量导入临床随访数据，自动计算靶病灶最长径之和（SLD）、
          与基线 / 最低点（nadir）比较，得出 CR / PR / SD / PD / NE 等疗效结论，并生成可下载的
          评估报告。
        </p>
        <table>
          <thead>
            <tr><th>功能模块</th><th>入口</th><th>主要用途</th></tr>
          </thead>
          <tbody>
            <tr><td>数据导入</td><td>顶部「数据导入」</td><td>上传 Excel，解析并写入受试者、评估与病灶数据</td></tr>
            <tr><td>受试者</td><td>顶部「受试者」</td><td>按批次查看受试者列表，进入单个受试者控制台</td></tr>
            <tr><td>智能分析</td><td>顶部「智能分析」</td><td>疗效统计、状态分布、各维度下钻明细</td></tr>
            <tr><td>评估标准</td><td>顶部「评估标准」</td><td>查看 RECIST 1.1 靶 / 非靶 / 确认规则与决策矩阵</td></tr>
            <tr><td>评估报告</td><td>受试者控制台 → 报告</td><td>查看单个受试者的详细评估，导出 Excel / PDF</td></tr>
          </tbody>
        </table>
      </div>

      <!-- 2. 登录与账号 -->
      <div class="card-wrapper">
        <h2 class="section-title">二、登录与账号</h2>
        <ol>
          <li>打开系统首页，进入登录页，输入<strong>用户名</strong>与<strong>密码</strong>。</li>
          <li>登录成功后进入「首页」，顶部导航栏显示当前账号，点击右上角可<strong>退出登录</strong>。</li>
          <li>系统按登录账号<strong>隔离数据</strong>：每个账号只能看到自己导入 / 新增的数据。若登录后看不到预期数据，请确认是否使用了正确的账号导入。</li>
        </ol>
        <div class="help-callout">
          <strong>提示：</strong>系统内置默认账号（如 admin / doctor），上线后请尽快修改为强口令。默认账号仅用于演示，不应在生产环境长期使用。
        </div>
      </div>

      <!-- 3. 数据导入 -->
      <div class="card-wrapper">
        <h2 class="section-title">三、数据导入</h2>
        <h3>3.1 支持的格式</h3>
        <p>系统支持两类 Excel 导入：</p>
        <ul>
          <li><strong>EDC 多周期格式</strong>：含多个工作表（受试者、靶病灶、非靶病灶、新病灶、肿瘤评估等），可一次性导入同一受试者的多个访视周期。</li>
          <li><strong>简化汇总格式</strong>：单行汇总每个评估周期的关键字段，适合快速录入。</li>
        </ul>

        <h3>3.2 关键字段说明</h3>
        <table>
          <thead>
            <tr><th>对象</th><th>关键字段</th><th>说明</th></tr>
          </thead>
          <tbody>
            <tr><td>受试者</td><td>受试者编号、周期编号</td><td>用于唯一标识一次评估（受试者 + 周期 + 批次）</td></tr>
            <tr><td>靶病灶</td><td>器官 / 具体部位 / 基线直径 / 当前直径 / 是否为淋巴结</td><td>系统按最长径（淋巴结取短轴）计算 SLD</td></tr>
            <tr><td>非靶病灶</td><td>器官 / 具体部位 / 基线状态 / 当前状态</td><td>状态含：消失、持续存在、明确进展</td></tr>
            <tr><td>新病灶</td><td>器官 / 具体部位 / 发现日期 / 检查方法</td><td>任何新病灶出现即判为 PD</td></tr>
          </tbody>
        </table>

        <h3>3.3 导入步骤</h3>
        <ol>
          <li>点击顶部「数据导入」，进入上传页。</li>
          <li>点击「选择文件」或直接拖拽 Excel 到上传区。</li>
          <li>点击「解析导入」，系统会校验并写入数据。</li>
          <li>导入完成后自动跳转首页，可在「受试者」中查看结果。</li>
        </ol>
        <div class="help-callout">
          <strong>注意：</strong>重复导入同一文件会生成<strong>新的批次</strong>，不会对旧批次做覆盖；历史批次可在首页顶部的批次选择器中切换查看，也可单独删除或一键清空。
        </div>
      </div>

      <!-- 4. 批次筛选 -->
      <div class="card-wrapper">
        <h2 class="section-title">四、批次筛选（全局视图）</h2>
        <p>
          首页顶部提供<strong>批次选择器</strong>，显示每次导入的「导入时间」与「Excel 名称」。
          选择一个批次后，<strong>受试者、评估、分析、报告</strong>等所有页面都只显示该批次的数据。
          这是系统统一的全局筛选器。
        </p>
        <ul>
          <li>切换批次：在首页点击批次选择器，选择目标批次即可。</li>
          <li>历史记录：点击批次选择器旁的历史图标，可查看 / 删除历史批次，或一键清空当前账号的全部数据。</li>
          <li>新增数据归属：手动新增的受试者 / 评估会自动归入当前选中的批次，确保各页面同步可见。</li>
        </ul>
      </div>

      <!-- 5. 受试者管理 -->
      <div class="card-wrapper">
        <h2 class="section-title">五、受试者管理</h2>
        <ol>
          <li>点击顶部「受试者」，查看当前批次下的受试者列表（含基本信息、最新评估结论）。</li>
          <li>点击某一行，进入<strong>受试者控制台</strong>，查看该受试者的全部评估周期与病灶明细。</li>
          <li><strong>新增受试者</strong>：在列表页点击「添加受试者」，填写编号等信息，将归属当前批次。</li>
          <li><strong>新增 / 编辑病灶</strong>：在受试者控制台或评估页，可对任意评估周期新增或编辑靶病灶、非靶病灶、新病灶，并补充器官、检查方法、分裂融合等医学字段。</li>
        </ol>
        <div class="help-callout">
          <strong>提示：</strong>编辑或新增病灶后，系统会<strong>自动重新计算</strong>该次评估的疗效结论与理由，无需手动触发。
        </div>
      </div>

      <!-- 6. 评估与病灶编辑 -->
      <div class="card-wrapper">
        <h2 class="section-title">六、评估计算与人工修正</h2>
        <p>
          每次评估都依据 RECIST 1.1 标准自动计算：
        </p>
        <div class="formula-box">
          SLD<sub>基线</sub> = Σ 各靶病灶最长径（基线）<br/>
          SLD<sub>最低点</sub> = min(SLD<sub>基线</sub>, 各次随访 SLD)<br/>
          PR：(SLD<sub>基线</sub> − SLD<sub>当前</sub>) / SLD<sub>基线</sub> ≥ 30%<br/>
          PD：(SLD<sub>当前</sub> − SLD<sub>最低点</sub>) / SLD<sub>最低点</sub> ≥ 20% 且 (SLD<sub>当前</sub> − SLD<sub>最低点</sub>) ≥ 5mm，或 出现新病灶
        </div>
        <ul>
          <li><strong>靶病灶</strong>：所有病灶消失 → CR；较基线缩小 ≥30% → PR；较最低点增大达双条件 → PD；其余 → SD。</li>
          <li><strong>非靶病灶</strong>：全部消失 → 非靶 CR；持续存在但无明确进展 → Non-CR / Non-PD；明确（unequivocal）进展 → PD。</li>
          <li><strong>新病灶</strong>：任何新病灶出现，整体疗效直接判为 PD（一票否决）。</li>
          <li><strong>人工评估</strong>：当 Excel 中记录了临床人工判读结论时，以人工结论为优先（临床记录为金标准），系统仍保留自动计算值并在理由中说明。</li>
        </ul>
        <p>
          评估理由会展示<strong>所用公式、代入实际数值的算术过程、阈值比较与结论</strong>，并附逐病灶明细，
          可在评估页与报告页查看。
        </p>
      </div>

      <!-- 7. 智能分析 -->
      <div class="card-wrapper">
        <h2 class="section-title">七、智能分析</h2>
        <ol>
          <li>点击顶部「智能分析」，查看当前批次的疗效统计概览（受试者数、各结论占比等）。</li>
          <li>查看靶病灶 / 非靶病灶 / 新病灶各维度的<strong>状态分布</strong>。</li>
          <li>点击分布图中的某一项，可<strong>下钻</strong>查看属于该状态的受试者 / 评估明细。</li>
        </ol>
      </div>

      <!-- 8. 评估报告与导出 -->
      <div class="card-wrapper">
        <h2 class="section-title">八、评估报告与导出</h2>
        <ol>
          <li>在「受试者」中进入某受试者控制台，点击「报告」查看该受试者的完整评估明细。</li>
          <li>报告含靶 / 非靶 / 新病灶明细表（基线 / 当前两级分组）、SLD 解释、各次评估结论与理由。</li>
          <li>
            导出：点击报告页的<strong>导出菜单</strong>：
            <ul>
              <li><strong>导出 Excel</strong>：点击直接下载，并弹出窗口选择保存位置。</li>
              <li><strong>导出 PDF</strong>：生成打印视图，在打印对话框中选择「另存为 PDF」并指定保存位置。</li>
            </ul>
          </li>
        </ol>
      </div>

      <!-- 9. 评估标准 -->
      <div class="card-wrapper">
        <h2 class="section-title">九、评估标准参考</h2>
        <p>
          系统所依据的 RECIST 1.1 完整标准（靶病灶判定、非靶病灶判定、确认规则、决策矩阵、判定流程图）
          可在顶部「评估标准」页查看。如需调整评估口径，请参见该页说明。
        </p>
        <div class="help-callout">
          <strong>关键概念：</strong>
          <ul>
            <li><strong>SLD</strong>：靶病灶最长径（淋巴结取短轴）之和。</li>
            <li><strong>Nadir（最低点）</strong>：研究期间 SLD 的最小值，PD 判定以 nadir 而非基线为参照。</li>
            <li><strong>Unequivocal 进展</strong>：非靶病灶须为"明确"进展才判 PD，轻微增大不构成 PD。</li>
            <li><strong>确认规则</strong>：CR / PR 通常需在治疗后 ≥4 周再次评估确认。</li>
          </ul>
        </div>
      </div>

      <!-- 10. 常见问题 -->
      <div class="card-wrapper">
        <h2 class="section-title">十、常见问题（FAQ）</h2>
        <h4>Q1：导入时报 500 错误？</h4>
        <p>多为数据库写入权限问题。请确认服务运行用户对数据目录有写权限；本地开发通常不会遇到，线上部署需检查文件属主。</p>
        <h4>Q2：登录后看不到之前导入的数据？</h4>
        <p>系统按账号隔离数据。请确认你使用了<strong>导入数据时相同的账号</strong>登录；不同账号的数据互不可见。</p>
        <h4>Q3：为什么手动新增的受试者 / 病灶在别处看不到？</h4>
        <p>它们归当前选中的批次所有。请确认首页批次选择器选中的是新增时所在的批次；切换批次即可看到。</p>
        <h4>Q4：修改病灶后结论没变？</h4>
        <p>系统会在保存后自动重算。若仍未变化，请检查是否处于正确的批次 / 评估周期，或刷新页面重试。</p>
        <h4>Q5：导出 PDF 没反应？</h4>
        <p>导出 PDF 会打开新窗口并触发打印对话框，请<strong>允许浏览器弹出窗口</strong>，并在对话框中选择"另存为 PDF"。</p>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import { exportHtmlToDoc } from '../utils/export'

const printArea = ref(null)

const onDownloadDoc = async () => {
  if (!printArea.value) {
    ElMessage.error('导出内容未就绪')
    return
  }
  const res = await exportHtmlToDoc('RECIST 病灶评估系统 · 使用帮助', printArea.value.innerHTML)
  if (res === 'cancelled') {
    ElMessage.info('已取消下载')
  } else {
    ElMessage.success(res === 'picker' ? '已选择保存位置并下载 DOC 文档' : '已下载 DOC 文档')
  }
}
</script>

<style scoped>
.help-container {
  max-width: 1400px;
  margin: 0 auto;
  padding-bottom: 40px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  animation: slideIn 0.4s ease;
}

.page-header h2 {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: -0.5px;
}

.header-subtitle {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0;
  align-self: center;
}

.header-actions {
  margin-left: auto;
}

.help-content :deep(h3) {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 18px 0 8px;
}

.help-content :deep(h4) {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-regular);
  margin: 14px 0 4px;
}

.help-content :deep(p) {
  margin: 8px 0;
  color: var(--text-regular);
}

.help-content :deep(ul),
.help-content :deep(ol) {
  padding-left: 22px;
  margin: 8px 0;
  color: var(--text-regular);
}

.help-content :deep(li) {
  margin: 4px 0;
}

.help-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 13px;
}

.help-content :deep(th) {
  background: var(--primary-color);
  color: #fff;
  padding: 9px 12px;
  border: 1px solid #cfd8e3;
  text-align: left;
  font-weight: 600;
}

.help-content :deep(td) {
  padding: 8px 12px;
  border: 1px solid var(--border-light);
  color: var(--text-regular);
  vertical-align: top;
}

.help-callout {
  background: var(--primary-light);
  border-left: 4px solid var(--primary-color);
  padding: 12px 16px;
  border-radius: var(--radius-md);
  margin: 12px 0;
  color: var(--text-regular);
}

.help-callout :deep(ul) {
  margin: 6px 0 0;
}

.formula-box {
  background: #0f172a;
  color: #e2e8f0;
  padding: 14px 18px;
  border-radius: var(--radius-md);
  margin: 12px 0;
  font-family: Consolas, "Courier New", monospace;
  font-size: 13px;
  line-height: 1.9;
}

.formula-box :deep(sub) {
  font-size: 0.75em;
}
</style>
