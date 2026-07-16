# RECIST 1.1 算法规则与评估引擎说明

> 本文档对照后端 `backend/app/services/recist_engine.py` 的实现，完整说明系统对**每个受试者每次评估**所采用的判定规则、计算公式、决策矩阵与理由生成逻辑。
> 标准依据：RECIST 1.1（实体瘤疗效评价标准第 1.1 版）§6.1 靶病灶 / §6.2 非靶病灶 / §6.3 确认规则。

---

## 1. 总览：评估如何被触发

系统对**每个受试者每次评估（基线、每周期复查、人工新增/编辑/删除病灶）**都会调用同一个引擎，确保标准一致：

| 触发路径 | 入口 | 说明 |
|---|---|---|
| EDC / Excel 批量导入 | `app/api/data_io.py` → `RecistEngine.perform_assessment` | 导入时即按标准计算每个受试者每期疗效 |
| 靶/非靶/新病灶 新增、编辑、删除 | `app/api/assessments.py` 的 `_recompute_assessment` | 任意病灶变更后自动重算该受试者当前期评估 |
| 人工分类（无逐病灶尺寸）综合评估 | `assess_comprehensive` | 只有 Excel「人工(靶/非靶/新病灶)分类」而无尺寸明细时使用 |

**结论**：不存在"绕过引擎"的评估。所有存储的 `target_status / non_target_status / overall_status / *_reason` 都来自本引擎。

---

## 2. 核心概念

| 概念 | 含义 |
|---|---|
| **SLD (Sum of Longest Diameters)** | 所有靶病灶最长径（淋巴结取短轴）之和。 |
| **Baseline SLD** | 筛选期（基线）各靶病灶最长径之和，后续比较的基准。 |
| **Nadir SLD** | 研究期间出现的**最低** SLD 值（含基线）。**PD 判定与之比较，而非与基线比较**。 |
| **Target Lesions** | 可测量病灶（通常每个器官最多选 2 个，最多 5 个总计）。 |
| **Non-Target Lesions** | 不可测量病灶（如胸腔积液、骨转移、淋巴管播散等）。 |
| **New Lesion** | 治疗过程中新出现的任何病灶，出现即判为 PD（无论大小、位置、发现方式）。 |
| **Unequivocal Progression** | 非靶病灶的"明确"进展（如胸水少量→大量、淋巴管炎局限→弥漫）；**轻微增大不构成 PD**。 |

---

## 3. 靶病灶判定（§6.1）

### 3.1 阈值常量

| 常量 | 值 | 含义 |
|---|---|---|
| `PR_THRESHOLD` | **−30%** | SLD 较基线下降 ≥30% → PR |
| `PD_PERCENT_THRESHOLD` | **+20%** | SLD 较 nadir 增加 ≥20% → PD 条件一 |
| `PD_ABSOLUTE_THRESHOLD` | **+5 mm** | SLD 较 nadir 绝对值增加 ≥5 mm → PD 条件二 |
| `LYMPH_NODE_SHORT_AXIS_MAX` | **10 mm** | 判定 CR 时病理/淋巴结短轴须 < 10 mm |

### 3.2 判定分支（按优先级顺序）

| 结果 | 判定条件 |
|---|---|
| **CR 完全缓解** | 所有靶病灶消失（SLD_当前 = 0），且病理淋巴结短轴 < 10 mm。 |
| **PD 疾病进展** | 满足以下**任一**：① SLD 较 nadir 增加 ≥20% **且** 绝对值增加 ≥5 mm；② 出现任何新病灶。 |
| **PR 部分缓解** | 靶病灶 SLD 较基线下降 ≥30%（在已排除新病灶与 CR 之后）。 |
| **SD 疾病稳定** | 既达不到 PR（缩小不足），也未达 PD（增大不足），介于两者之间。 |
| **NE 无法评估** | 受试者无靶病灶（参与整体评估时记为不适用 NA）、基线 SLD 为 0、或无靶病灶数据。 |

### 3.3 公式

```
SLD_baseline = Σ 各靶病灶最长径（基线）
SLD_nadir    = min(SLD_baseline, SLD_followup_1, SLD_followup_2, ...)

PR: (SLD_baseline − SLD_now) / SLD_baseline ≥ 0.30
PD: (SLD_now − SLD_nadir) / SLD_nadir ≥ 0.20  AND  (SLD_now − SLD_nadir) ≥ 5 mm
    或  出现新病灶
```

### 3.4 三个极易出错的细节（已在引擎与理由中显式处理）

1. **PD 参照是 nadir（最低值），不是基线。** 例：基线 100 → 最低 50 → 复查 60：相对最低值 +20%（=60）且绝对 +10 mm ≥ 5 → 判 PD；若回升到 58（+16% < 20%）则仍 SD。
2. **PD 双条件缺一不可**：既需相对 +20%，又需绝对 +5 mm。小病灶微小波动不应误判为进展。
3. **新病灶 = PD**，无论大小、无论出现在何处（含 FDG-PET 发现）。

---

## 4. 非靶病灶判定（§6.2）

> 非靶病灶**不计算尺寸百分比**，只按"状态"分类判定。

| 输入状态 | 判定结果 |
|---|---|
| 任一病灶为「进展（unequivocal）」 | **PD**（明确进展，一票否决） |
| 全部「消失」且肿瘤标志物正常 | **CR** |
| 全部「消失」但肿瘤标志物未正常 | **Non-CR/Non-PD** |
| 存在「持续存在」且无明确进展 | **Non-CR/Non-PD** |
| 混合/其他（未完全消失、无明确进展） | **Non-CR/Non-PD** |
| 无数据 / 受试者无此类病灶 | **NE** |

⚠️ **"明确"二字是关键**：非靶病灶轻微增大**不构成 PD**，必须是明确进展（胸水少量→大量、淋巴管炎局限→弥漫）。系统不会把尺寸小幅变化自动判为 PD。

---

## 5. 确认规则（§6.3）

| 规则 | 说明 |
|---|---|
| 非随机试验 | CR 与 PR 须在治疗后 **≥4 周**复查确认。 |
| 随机试验 | 可由方案决定是否需确认（多数不强制）。 |
| 持续性 PR | 确认后的 PR 后续访视视为"持续 PR"，直至满足 PD 标准——**后续判定参照 nadir 而非基线**。 |
| PD | 一般不需确认（除非影像模棱两可）。 |

**系统实现**：`build_confirmation()` 依据该受试者全部评估时间线，对当前 CR/PR 判定确认状态：

- 找到当前评估后 **≥28 天**的首次后续访视；
- 若后续为 CR/PR/SD → `confirmed = True`（持续缓解）；
- 若后续为 PD → `confirmed = False`（未确认最佳缓解，但记录最佳总体仍为该 CR/PR，并标注未确认）；
- 若无后续 ≥4 周访视 → `confirmed = None`（待确认/首次判定）。

确认说明通过 `confirmation_note()` 追加到 `overall_reason` **末尾**，**不改变存储状态**。

---

## 6. 整体疗效评价（决策矩阵）

### 6.1 决策优先级（高 → 低）

1. **新病灶出现 → PD**（最高优先级，一票否决，覆盖其他一切）
2. 非靶病灶明确（unequivocal）进展 → PD
3. 靶病灶 PD（较 nadir ↑≥20% 且 绝对 ↑≥5 mm）→ PD
4. 标准矩阵匹配 → CR / PR / SD / PD / NE

### 6.2 决策矩阵

| Target | Non-Target | New Lesion | Overall |
|---|---|---|---|
| CR | CR | No | **CR** |
| CR | Non-CR/Non-PD | No | **PR** |
| PR | Non-CR/Non-PD 或 CR | No | **PR** |
| SD | Non-CR/Non-PD 或 CR | No | **SD** |
| PD | Any | Any | **PD** |
| Any | PD | Any | **PD** |
| Any | Any | Yes | **PD** |

### 6.3 "不适用（NA）"与"NE"区分

- **NA（Not Applicable）**：受试者基线无此类病灶（如无可测量靶病灶）。该维度不参与整体评估——无靶病灶时整体跟随非靶病灶；无非靶病灶时整体跟随靶病灶。
- **NE（Not Evaluable）**：该维度存在但数据不足以判定 → 整体按保守/降级处理（如靶病灶 CR 但非靶 NE → 降级为 PR；靶病灶 NE 且非靶 CR → NE 因无法确认完全缓解）。

---

## 7. 判定流程图（图 1）

```
1. 计算 SLD（最长径之和）
2. 所有靶病灶消失？
     ├─ 是 → CR（淋巴结短轴 < 10 mm）
     └─ 否 → 继续
3. SLD 较基线 ↓ ≥ 30%？
     ├─ 是 → PR
     └─ 否 → 继续
4. 较 nadir ↑ ≥ 20% 且 绝对 ↑ ≥ 5 mm，或出现新病灶？
     ├─ 是 → PD
     └─ 否 → SD（介于 PR 与 PD 之间）
5. 再与非靶病灶结果合并 → 总体疗效
```

---

## 8. 详尽理由生成机制（每条评估都给出可复核的过程）

引擎为每个维度生成**结构化的理由文本**，包含：标题、判定公式、逐病灶明细、代入实际数值的算术过程、阈值比较与结论。前端"评估报告/评估页"直接展示 `target_reason / non_target_reason / overall_reason`。

**示例：靶病灶 PD 理由**
```
【靶病灶评估 · RECIST 1.1 §6.1】
计算公式：PD ⇒ (SLD_当前 − SLD_最低点) / SLD_最低点 × 100% ≥ 20% 且 (SLD_当前 − SLD_最低点) ≥ 5 mm
病灶明细（最长径，单位 mm）：
  · 淋巴结：基线 100.0 → 当前 62.0 mm
SLD_基线 = 100.0 mm
SLD_最低点(nadir，含基线及历史各期最小值) = 50.0 mm
SLD_当前 = 62.0 mm
(SLD_当前 − SLD_最低点) / SLD_最低点 × 100% = (62.0 − 50.0) / 50.0 × 100% = 24.0%
SLD_当前 − SLD_最低点 = 62.0 − 50.0 = 12.0 mm
24.0% ≥ 20% 且 12.0 mm ≥ 5 mm ⇒ 满足 PD 双条件。
依据 RECIST 1.1 §6.1：靶病灶 SLD 较研究期间最低点增加 ≥20% 且绝对值增加 ≥5 mm（参照 nadir 而非基线），判定为疾病进展(PD)。
```

**示例：整体疗效（含确认规则）**
```
【总体疗效评估 · RECIST 1.1 决策矩阵】
综合输入：靶病灶=CR，非靶病灶=Non-CR/Non-PD，新病灶=无。
决策规则：CR + Non-CR/Non-PD → PR。
靶病灶 CR 但非靶病灶持续存在，不能判为 CR → 整体 PR。
【确认规则 · RECIST 1.1 §6.3】CR/PR 须在治疗后 ≥4 周复查确认（非随机试验）。
当前为首次/未确认判定，待后续 ≥4 周访视确认；若届时仍为 CR/PR/SD，则确认为该状态。
```

---

## 9. 人工分类综合评估（无逐病灶尺寸时）

当导入数据只含 Excel「人工(靶/非靶/新病灶)分类」而无尺寸明细，`assess_comprehensive` 按 REClST 1.1 决策矩阵综合推导：

- 维度为「不适用（NA）」→ 该维度受试者基线无此类病灶；
- CR / PR / SD / PD → 该维度对应状态；
- NE 或未知 → 该维度不可评估（NE）；
- 新病灶（布尔）→ 参与总体决策矩阵（任何新病灶 → PD）。

避免了"基线无病灶 → 一概 NE"的误判。

---

## 10. 引擎 API 速查（`RecistEngine`）

| 方法 | 用途 | 返回 |
|---|---|---|
| `calculate_sum(lesions, field)` | 计算最长径之和 | `float` |
| `assess_target_lesions(...)` | 靶病灶判定 + 理由 | `(status, reason, baseline_sum, current_sum, change_percent, change_from_nadir_pct, not_applicable)` |
| `assess_non_target_lesions(...)` | 非靶病灶判定 + 理由 | `(status, reason, not_applicable)` |
| `assess_overall(...)` | 决策矩阵 + 确认规则 | `(status, reason)` |
| `confirmation_note(status, conf)` | 生成 §6.3 确认说明 | `str` |
| `build_confirmation(...)` | 基于时间线判定确认状态 | `dict \| None` |
| `assess_comprehensive(...)` | 人工分类综合评估 | `dict` |
| `perform_assessment(...)` | **总入口**：完整评估 | `AssessmentResult` |
| `get_algorithm_summary()` | 结构化算法说明（供前端/API/报告 Tooltip） | `dict` |

---

## 11. 与前端/报告的衔接

- 前端"评估标准"页（`Standard.vue`）与"算法"接口（`GET /api/assessments/algorithm`）展示的就是 `get_algorithm_summary()` 的内容，与本文档第 3/4/5/6/7 节一致。
- 评估/报告页的"理由"列直接渲染 `*_reason` 字段，即第 8 节格式的详细过程。
- 报告页 SLD 列旁 ⓘ Tooltip 解释 RECIST 1.1 算法（nadir / 双条件 / 确认规则）。

---

*文档生成时间：2026-07-16 · 对应代码分支 feat-assess-lesion-data-EENwGD*
