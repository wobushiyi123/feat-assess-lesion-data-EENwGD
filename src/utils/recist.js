// RECIST 1.1 标准 — 与后端 recist_engine.py 对齐
// 整体疗效只有 CR / PR / SD / PD / NE 五种
// Non-CR/Non-PD 仅用于非靶病灶单独评估，不出现在整体疗效中

export const RECIST_STATUS = {
  CR: '完全缓解',
  PR: '部分缓解',
  SD: '疾病稳定',
  PD: '疾病进展',
  NE: '无法评估',
  'Non-CR/Non-PD': '非完全缓解/非疾病进展',  // 仅非靶病灶表述
  '不适用': '不适用'
}

// 靶病灶评估（对齐后端 assess_target_lesions）
// options.nadirSum: 历史最低 SLD，PD 时从 nadir 比较而非基线
export function calculateTargetAssessment(baselineSum, currentSum, hasNewLesion, options = {}) {
  const { nadirSum = null, isEmpty = false } = options

  // 无靶病灶（受试者基线就无靶病灶）
  if (isEmpty) {
    return { status: '不适用', reason: '基线无靶病灶' }
  }

  if (baselineSum === 0) {
    return { status: 'NE', reason: '基线数据缺失' }
  }

  // 新病灶 → 最高优先级 PD
  if (hasNewLesion) {
    return { status: 'PD', reason: '出现新病灶' }
  }

  // 所有靶病灶消失
  if (currentSum === 0) {
    return { status: 'CR', reason: '所有靶病灶消失' }
  }

  // 部分缓解（较基线减少 ≥30%）
  const changeFromBaseline = ((currentSum - baselineSum) / baselineSum) * 100

  // 疾病进展判定：优先从 nadir（最低点）比较
  if (nadirSum !== null && nadirSum > 0) {
    const changeFromNadir = ((currentSum - nadirSum) / nadirSum) * 100
    const nadirAbsoluteChange = Math.abs(currentSum - nadirSum)
    if (changeFromNadir >= 20 && nadirAbsoluteChange >= 5) {
      return {
        status: 'PD',
        reason: `最长径总和较最低点(${nadirSum}mm)增加${changeFromNadir.toFixed(1)}%（≥20%）` +
          `且绝对值增加${nadirAbsoluteChange.toFixed(1)}mm（≥5mm）`
      }
    }
  }

  // 较基线 PD（无 nadir 时回退）
  const absChange = Math.abs(currentSum - baselineSum)
  if (changeFromBaseline >= 20 && absChange >= 5) {
    return {
      status: 'PD',
      reason: `最长径总和增加${changeFromBaseline.toFixed(1)}%（≥20%）且绝对值增加${absChange.toFixed(1)}mm（≥5mm）`
    }
  }

  // 较基线 PR
  if (changeFromBaseline <= -30) {
    return { status: 'PR', reason: `最长径总和较基线减少${Math.abs(changeFromBaseline).toFixed(1)}%（≥30%）` }
  }

  // SD
  return { status: 'SD', reason: `最长径总和变化${changeFromBaseline.toFixed(1)}%，介于PR和PD之间` }
}

// 非靶病灶评估（对齐后端 assess_non_target_lesions）
export function calculateNonTargetAssessment(nonTargetStatus, tumorMarkerNormal, options = {}) {
  const { isEmpty = false } = options

  // 基线无此病灶类型
  if (isEmpty) {
    return { status: '不适用', reason: '基线无非靶病灶' }
  }

  if (!nonTargetStatus && !isEmpty) {
    return { status: 'NE', reason: '非靶病灶状态数据缺失' }
  }

  // 任何一个明确进展 → PD
  if (nonTargetStatus === '进展') {
    return { status: 'PD', reason: '至少一个非靶病灶出现明确进展' }
  }

  // 全部消失 + 肿瘤标志物正常 → CR
  if (nonTargetStatus === '消失' && tumorMarkerNormal) {
    return { status: 'CR', reason: '所有非靶病灶消失且肿瘤标志物正常' }
  }

  // 消失但肿瘤标志物未正常 → Non-CR/Non-PD（非靶病灶层面）
  if (nonTargetStatus === '消失' && !tumorMarkerNormal) {
    return { status: 'Non-CR/Non-PD', reason: '非靶病灶消失但肿瘤标志物未恢复正常' }
  }

  // 持续存在但无进展 → Non-CR/Non-PD（非靶病灶层面）
  if (nonTargetStatus === '持续存在') {
    return { status: 'Non-CR/Non-PD', reason: '非靶病灶持续存在但无明确进展' }
  }

  return { status: 'Non-CR/Non-PD', reason: '非靶病灶未完全消失且无明确进展' }
}

// 整体疗效评价（对齐后端 RECIST 1.1 决策矩阵）
// 关键修复：不再返回 Non-CR/Non-PD 作为整体疗效
export function calculateOverallAssessment(targetResult, nonTargetResult, hasNewLesion) {
  // 任何新病灶 → PD（最高优先级）
  if (hasNewLesion) {
    return { status: 'PD', reason: '出现新病灶' }
  }

  // 靶病灶或非靶病灶 PD → PD
  if (nonTargetResult.status === 'PD') {
    return { status: 'PD', reason: '非靶病灶明确进展' }
  }
  if (targetResult.status === 'PD') {
    return { status: 'PD', reason: '靶病灶疾病进展' }
  }

  // 双方都不可评估
  if (targetResult.status === 'NE' && nonTargetResult.status === 'NE') {
    return { status: 'NE', reason: '靶病灶和非靶病灶评估均无法进行' }
  }

  // 无靶病灶（not_applicable）：整体跟随非靶病灶
  if (targetResult.status === '不适用') {
    if (nonTargetResult.status === 'CR') return { status: 'CR', reason: '无非靶病灶，靶病灶全部消失 → CR' }
    if (nonTargetResult.status === 'PD') return { status: 'PD', reason: '非靶病灶明确进展' }
    if (nonTargetResult.status === 'Non-CR/Non-PD') return { status: 'NE', reason: '靶病灶不适用，非靶病灶不能判为CR → 无法确定总体疗效' }
    return { status: 'NE', reason: '靶病灶不适用' }
  }

  // 无非靶病灶（not_applicable）：整体跟随靶病灶
  if (nonTargetResult.status === '不适用') {
    const reasonMap = {
      CR: '受试者无非靶病灶，靶病灶全部消失 → CR',
      PR: '受试者无非靶病灶，靶病灶充分缩小 → PR',
      SD: '受试者无非靶病灶，靶病灶变化未达PR或PD → SD',
      PD: '受试者无非靶病灶，靶病灶进展 → PD'
    }
    return { status: targetResult.status, reason: reasonMap[targetResult.status] || `受试者无非靶病灶，靶病灶${targetResult.status}` }
  }

  // 靶病灶可评估 + 非靶能评估
  // CR + CR → CR
  if (targetResult.status === 'CR' && nonTargetResult.status === 'CR') {
    return { status: 'CR', reason: '靶病灶和非靶病灶均完全缓解' }
  }

  // CR + Non-CR/Non-PD → PR（不能判 CR）
  if (targetResult.status === 'CR' && nonTargetResult.status === 'Non-CR/Non-PD') {
    return { status: 'PR', reason: '靶病灶CR但非靶病灶持续存在，不能判为CR → PR' }
  }

  // PR + ... → PR
  if (targetResult.status === 'PR' && ['CR', 'Non-CR/Non-PD'].includes(nonTargetResult.status)) {
    return { status: 'PR', reason: '靶病灶部分缓解' }
  }

  // SD + ... → SD
  if (targetResult.status === 'SD' && ['CR', 'Non-CR/Non-PD'].includes(nonTargetResult.status)) {
    return { status: 'SD', reason: '靶病灶病情稳定' }
  }

  return { status: 'NE', reason: '无法综合判断' }
}

// 获取状态颜色
export function getStatusColor(status) {
  const colors = {
    CR: '#67c23a',
    PR: '#409eff',
    SD: '#e6a23c',
    PD: '#f56c6c',
    NE: '#909399',
    'Non-CR/Non-PD': '#9ca3af',
    '不适用': '#c0c4cc'
  }
  return colors[status] || '#909399'
}

// 获取 Element Plus tag 类型
export function getStatusTagType(status) {
  const map = {
    CR: 'success',
    PR: 'primary',
    SD: 'warning',
    PD: 'danger',
    NE: 'info',
    'Non-CR/Non-PD': 'info',
    '不适用': 'info'
  }
  return map[status] || 'info'
}

// 获取状态中文文本
export function getStatusText(status) {
  return RECIST_STATUS[status] || status || '无法评估'
}
