/**
 * 导出工具模块
 * 支持 Excel（xlsx 库）和 PDF（浏览器打印）两种格式
 * Excel 导出支持通过 File System Access API 选择保存位置（不支持的浏览器自动回退为直接下载）
 */
import * as XLSX from 'xlsx'
import { getStatusText } from './recist'

// ---- 内部辅助 ----

// 状态码 → 完整中文名称（含代码）
function statusLabel(status) {
  if (!status) return '-'
  const chinese = getStatusText(status)
  const codeMap = {
    '完全缓解': 'CR',
    '部分缓解': 'PR',
    '疾病稳定': 'SD',
    '疾病进展': 'PD',
    '无法评估': 'NE',
    '非完全缓解/非疾病进展': 'Non-CR/Non-PD',
    '不适用': '不适用'
  }
  const code = codeMap[chinese] || status
  // 如果传入的已经是中文，直接返回
  if (chinese === status) return status
  return `${chinese}(${code})`
}

// 一致性文本
function matchLabel(row) {
  if (row.overall_match === true) return '一致'
  if (row.overall_match === false) return '不一致'
  return '无人工数据'
}

// 新病灶文本
function newLesionLabel(row, field) {
  const val = row[field]
  if (val === undefined || val === null) return '-'
  return val ? '有' : '无'
}

// 将评估行转换为扁平对象（供 Excel / PDF 复用）
export function flattenAssessmentRow(row) {
  return {
    '受试者编号': row.subject_id || '-',
    '时间点': row.timepoint || (row.cycle_number ? `周期${row.cycle_number}` : '-'),
    '靶病灶评估(程序)': statusLabel(row.target_status),
    '靶病灶评估(人工)': row.manual_target_status ? statusLabel(row.manual_target_status) : '-',
    '非靶病灶评估(程序)': statusLabel(row.non_target_status),
    '非靶病灶评估(人工)': row.manual_non_target_status ? statusLabel(row.manual_non_target_status) : '-',
    '新病灶(程序)': newLesionLabel(row, 'has_new_lesion'),
    '新病灶(人工)': row.has_manual_data !== false ? newLesionLabel(row, 'manual_has_new_lesion') : '-',
    '总体疗效评估(程序)': statusLabel(row.overall_status),
    '总体疗效评估(人工)': row.manual_overall_status ? statusLabel(row.manual_overall_status) : '-',
    '是否一致': matchLabel(row),
    '程序判定理由': row.overall_reason || '-'
  }
}

// 受试者概览扁平化（按受试者 + 时间点展开）
export function flattenSubjectRows(subjectRows) {
  const data = []
  subjectRows.forEach(subj => {
    ;(subj.timepoints || []).forEach(tp => {
      data.push(flattenAssessmentRow({
        ...tp,
        subject_id: subj.subject_id,
        subject_name: subj.subject_name
      }))
    })
  })
  return data
}

// 根据内容计算 Excel 列宽
function computeCols(data) {
  const headers = Object.keys(data[0] || {})
  return headers.map(h => {
    let maxLen = h.length * 2
    data.forEach(row => {
      const val = String(row[h] || '')
      const len = [...val].reduce((acc, ch) => acc + (ch.charCodeAt(0) > 127 ? 2 : 1), 0)
      if (len > maxLen) maxLen = len
    })
    return { wch: Math.min(Math.max(maxLen + 2, 10), 60) }
  })
}

// 构建 workbook
function buildWorkbook(data, sheetName) {
  const ws = XLSX.utils.json_to_sheet(data)
  ws['!cols'] = computeCols(data)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, sheetName)
  return wb
}

// ---- Excel 导出 ----

/**
 * 通用 Excel 导出：优先让用户选择保存位置，失败/不支持则直接下载
 * @returns {'picker'|'download'|'cancelled'|'empty'}
 */
export async function exportToExcelWithPicker(data, filename, sheetName = '数据') {
  if (!data || data.length === 0) {
    alert('没有可导出的数据')
    return 'empty'
  }
  const wb = buildWorkbook(data, sheetName)

  // 现代浏览器：弹出原生保存对话框，可选位置与文件名
  if (typeof window !== 'undefined' && window.showSaveFilePicker) {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: filename,
        types: [{
          description: 'Excel 工作簿',
          accept: { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] }
        }]
      })
      const arrayBuffer = XLSX.write(wb, { bookType: 'xlsx', type: 'array' })
      const writable = await handle.createWritable()
      await writable.write(arrayBuffer)
      await writable.close()
      return 'picker'
    } catch (e) {
      if (e && e.name === 'AbortError') return 'cancelled' // 用户取消
      // 其它异常回退到直接下载
      console.warn('showSaveFilePicker failed, fallback to download', e)
    }
  }

  // 回退：浏览器默认下载到"下载"目录
  XLSX.writeFile(wb, filename)
  return 'download'
}

/**
 * 导出评估数据到 Excel（带位置选择）
 */
export async function exportAssessmentsToExcelPicker(rows, filename = '评估数据.xlsx', sheetName = '评估数据') {
  return exportToExcelWithPicker(rows.map(flattenAssessmentRow), filename, sheetName)
}

/**
 * 导出受试者概览到 Excel（带位置选择）
 */
export async function exportSubjectsToExcelPicker(subjectRows, filename = '受试者概览.xlsx') {
  return exportToExcelWithPicker(flattenSubjectRows(subjectRows), filename, '受试者概览')
}

// 兼容旧调用（直接下载）
export function exportAssessmentsToExcel(rows, filename = '评估数据.xlsx', sheetName = '评估数据') {
  const data = rows.map(flattenAssessmentRow)
  XLSX.writeFile(buildWorkbook(data, sheetName), filename)
}

export function exportSubjectsToExcel(subjectRows, filename = '受试者概览.xlsx') {
  const data = flattenSubjectRows(subjectRows)
  XLSX.writeFile(buildWorkbook(data, '受试者概览'), filename)
}

// ---- PDF 导出（浏览器打印） ----

/**
 * 通用 PDF 导出（通过浏览器打印为 PDF，用户可在打印对话框中选择"另存为 PDF"并指定位置）
 * @param {string} title  报告标题
 * @param {Object[]} data  扁平对象数组
 * @param {string} [subtitle]  副标题
 */
export function exportToPDF(title, data, subtitle = '') {
  if (!data || data.length === 0) {
    alert('没有可导出的数据')
    return
  }

  const headers = Object.keys(data[0])
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  const dateStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`

  const thHtml = headers.map(h => `<th>${h}</th>`).join('')
  const trHtml = data.map(row =>
    `<tr>${headers.map(h => {
      const val = row[h] || ''
      const isReason = h.includes('理由')
      return `<td${isReason ? ' class="reason-col"' : ''}>${escapeHtml(val)}</td>`
    }).join('')}</tr>`
  ).join('')

  const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>${title}</title>
<style>
  @page { size: landscape; margin: 12mm; }
  * { box-sizing: border-box; }
  body { font-family: "Microsoft YaHei", "SimSun", sans-serif; margin: 0; padding: 24px; color: #303133; }
  .report-title { font-size: 22px; font-weight: 700; text-align: center; margin-bottom: 6px; }
  .report-subtitle { font-size: 14px; color: #606266; text-align: center; margin-bottom: 4px; }
  .report-meta { font-size: 12px; color: #909399; text-align: center; margin-bottom: 20px; }
  .stats-row { display: flex; gap: 24px; justify-content: center; margin-bottom: 16px; }
  .stat-item { font-size: 13px; color: #606266; }
  .stat-item strong { color: #409eff; font-size: 16px; margin-right: 4px; }
  table { width: 100%; border-collapse: collapse; font-size: 11px; }
  th { background: #409eff; color: #fff; padding: 7px 5px; text-align: center; border: 1px solid #d0d0d0; white-space: nowrap; }
  td { padding: 5px 4px; border: 1px solid #e0e0e0; text-align: center; }
  tr:nth-child(even) { background: #f7f9fc; }
  .reason-col { text-align: left; max-width: 320px; word-break: break-word; white-space: normal; }
  .footer { margin-top: 16px; font-size: 11px; color: #c0c4cc; text-align: center; }
  @media print { body { padding: 0; } .no-print { display: none; } }
</style>
</head>
<body>
  <div class="report-title">${title}</div>
  ${subtitle ? `<div class="report-subtitle">${subtitle}</div>` : ''}
  <div class="report-meta">导出时间：${dateStr}　|　共 ${data.length} 条记录</div>
  <table>
    <thead><tr>${thHtml}</tr></thead>
    <tbody>${trHtml}</tbody>
  </table>
  <div class="footer">本报告由 RECIST 病灶评估系统自动生成</div>
  <script>
    window.onload = function() {
      setTimeout(function() { window.print(); }, 300);
    };
    window.onafterprint = function() { window.close(); };
  <\/script>
</body>
</html>`

  const win = window.open('', '_blank')
  if (!win) {
    alert('请允许弹出窗口以导出PDF')
    return
  }
  win.document.write(html)
  win.document.close()
}

/**
 * 导出评估数据到 PDF
 */
export function exportAssessmentsToPDF(title, rows, subtitle = '') {
  const data = rows.map(flattenAssessmentRow)
  exportToPDF(title, data, subtitle)
}

/**
 * 导出受试者概览到 PDF
 */
export function exportSubjectsToPDF(subjectRows, subtitle = '') {
  const data = flattenSubjectRows(subjectRows)
  exportToPDF('受试者概览', data, subtitle)
}

// HTML 转义
function escapeHtml(str) {
  const s = String(str)
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}
