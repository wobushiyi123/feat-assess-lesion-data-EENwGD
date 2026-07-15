"""智能分析服务 - AI预测、趋势分析、风险评估"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def simple_linear_regression(x: List[float], y: List[float]):
    """纯Python实现简单线性回归，返回斜率和截距"""
    n = len(x)
    if n < 2:
        return 0.0, 0.0
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0, y_mean
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    return float(slope), float(intercept)


class IntelligentAnalyzer:
    """智能分析器 - 提供AI驱动的医学数据分析"""

    @staticmethod
    def calculate_risk_score(assessment_data: Dict[str, Any]) -> float:
        """
        计算风险评分 (0-100)

        基于以下因素:
        - 变化率绝对值
        - 新病灶出现
        - 非靶病灶状态
        - 肿瘤标志物
        """
        score = 0.0

        change_percent = abs(assessment_data.get("change_percent", 0))
        if change_percent < 20:
            score += 10
        elif change_percent < 50:
            score += 30
        else:
            score += 50

        if assessment_data.get("has_new_lesion"):
            score += 30

        non_target_status = assessment_data.get("non_target_status", "")
        if non_target_status == "PD":
            score += 25
        elif non_target_status == "SD":
            score += 10

        if not assessment_data.get("tumor_marker_normal", True):
            score += 15

        return min(score, 100.0)

    @staticmethod
    def predict_next_status(history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        基于历史数据预测下一次评估结果

        综合 RECIST 1.1 标准的多维度预测：
        1. 靶病灶SLD变化趋势（线性回归）
        2. nadir追踪：距PD阈值(+20%)的距离
        3. 新病灶出现历史
        4. 非靶病灶进展状态
        """
        if len(history) < 2:
            return {
                "predicted_status": "NE",
                "confidence": 0.0,
                "method": "insufficient_data",
                "message": "历史数据不足，无法预测"
            }

        try:
            sorted_history = sorted(history, key=lambda x: x.get("cycle_number", 0))
            cycles = [float(h.get("cycle_number", i)) for i, h in enumerate(sorted_history)]
            changes = [float(h.get("change_percent", 0)) for h in sorted_history]
            sld_values = [h.get("current_sld") for h in sorted_history if h.get("current_sld") is not None]

            slope, intercept = simple_linear_regression(cycles, changes)

            next_cycle = float(max(cycles)) + 1
            predicted_change = slope * next_cycle + intercept

            # --- RECIST 1.1 多维度判定 ---
            # 1. 基于 nadir 的 PD 判定
            nadir_sld = None
            if sld_values:
                valid_sld = [v for v in sld_values if v and v > 0]
                if valid_sld:
                    nadir_sld = min(valid_sld)

            latest = sorted_history[-1]
            latest_sld = latest.get("current_sld")
            latest_has_new_lesion = latest.get("has_new_lesion", False)
            latest_ntl_status = latest.get("non_target_status", "")

            # 2. 检查是否有新病灶历史趋势
            new_lesion_count = sum(1 for h in sorted_history if h.get("has_new_lesion"))

            # 3. 基于变化率预测
            if predicted_change <= -30:
                predicted_status = "PR"
                confidence = 0.8
            elif predicted_change >= 20:
                predicted_status = "PD"
                confidence = 0.85
            else:
                predicted_status = "SD"
                confidence = 0.7

            # 4. 基于 nadir 修正预测
            if nadir_sld and latest_sld and nadir_sld > 0:
                change_from_nadir = (latest_sld - nadir_sld) / nadir_sld * 100
                # 如果接近 PD 阈值，提高 PD 预测置信度
                if change_from_nadir >= 15 and slope > 0:
                    predicted_status = "PD"
                    confidence = max(confidence, 0.85)
                # 如果持续缩小，可能达到 CR
                elif change_from_nadir < -30 and slope < 0:
                    predicted_status = "PR"
                    confidence = max(confidence, 0.8)

            # 5. 基于新病灶趋势修正
            if new_lesion_count > 0 and latest_has_new_lesion:
                predicted_status = "PD"
                confidence = 0.9

            # 6. 基于非靶病灶修正
            if latest_ntl_status == "PD":
                predicted_status = "PD"
                confidence = 0.9

            if slope < -1:
                trend = "improving"
            elif slope > 1:
                trend = "worsening"
            else:
                trend = "stable"

            return {
                "predicted_status": predicted_status,
                "predicted_change_percent": float(predicted_change),
                "trend": trend,
                "confidence": float(confidence),
                "method": "recist_linear_regression",
                "slope": float(slope),
                "nadir_sld": float(nadir_sld) if nadir_sld else None,
                "change_from_nadir_pct": float((latest_sld - nadir_sld) / nadir_sld * 100) if (nadir_sld and latest_sld) else None
            }
        except Exception as e:
            logger.error(f"预测失败: {e}")
            return {
                "predicted_status": "NE",
                "confidence": 0.0,
                "method": "error",
                "message": str(e)
            }

    @staticmethod
    def analyze_trend(history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析历史趋势

        Returns:
            包含趋势方向、平均变化率、改善/恶化周期数等
        """
        if not history:
            return {"error": "无历史数据"}

        sorted_history = sorted(history, key=lambda x: x.get("cycle_number", 0))

        status_counts = {}
        for h in sorted_history:
            s = h.get("overall_status", "NE")
            status_counts[s] = status_counts.get(s, 0) + 1

        changes = [float(h.get("change_percent", 0)) for h in sorted_history]
        n = len(changes)
        avg_change = sum(changes) / n if n > 0 else 0.0
        variance = sum((c - avg_change) ** 2 for c in changes) / n if n > 0 else 0.0
        std_change = variance ** 0.5
        max_change = max(changes) if changes else 0.0
        min_change = min(changes) if changes else 0.0

        improving_cycles = 0
        worsening_cycles = 0
        stable_cycles = 0

        for i in range(1, len(changes)):
            if changes[i] < changes[i-1] - 5:
                improving_cycles += 1
            elif changes[i] > changes[i-1] + 5:
                worsening_cycles += 1
            else:
                stable_cycles += 1

        if worsening_cycles > improving_cycles:
            trend_direction = "worsening"
        elif improving_cycles > worsening_cycles:
            trend_direction = "improving"
        else:
            trend_direction = "stable"

        return {
            "trend_direction": trend_direction,
            "status_distribution": status_counts,
            "avg_change_percent": round(avg_change, 2),
            "std_change_percent": round(std_change, 2),
            "max_change_percent": round(max_change, 2),
            "min_change_percent": round(min_change, 2),
            "improving_cycles": improving_cycles,
            "worsening_cycles": worsening_cycles,
            "stable_cycles": stable_cycles,
            "total_cycles": len(changes)
        }

    @staticmethod
    def generate_recommendations(
        current_status: str,
        risk_score: float,
        trend: Dict[str, Any]
    ) -> List[str]:
        """
        生成智能建议
        """
        recommendations = []

        if current_status == "PD":
            recommendations.append("⚠️ 病情进展，建议及时调整治疗方案")
            recommendations.append("建议进行更详细的影像学检查确认")
            recommendations.append("考虑多学科会诊（MDT）讨论后续治疗策略")
        elif current_status == "PR":
            recommendations.append("✓ 当前治疗有效，建议继续当前方案")
            recommendations.append("建议密切随访，监测疗效持续性")
        elif current_status == "SD":
            recommendations.append("→ 病情稳定，可继续观察")
            recommendations.append("建议按计划进行下一次评估")
        elif current_status == "CR":
            recommendations.append("✓ 完全缓解，建议巩固治疗")
            recommendations.append("定期复查，监测复发风险")

        if risk_score >= 70:
            recommendations.append("🔴 高风险，建议加强监测频率")
        elif risk_score >= 40:
            recommendations.append("🟡 中等风险，建议按标准方案随访")
        else:
            recommendations.append("🟢 低风险，按常规方案随访")

        if trend.get("trend_direction") == "worsening":
            recommendations.append("📈 数据显示病情有恶化趋势，建议提前介入")
        elif trend.get("trend_direction") == "improving":
            recommendations.append("📉 数据显示病情持续改善，治疗反应良好")

        return recommendations

    @staticmethod
    def detect_anomalies(assessments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        异常检测 - 发现异常数据点
        """
        if len(assessments) < 3:
            return []

        sorted_assessments = sorted(assessments, key=lambda x: x.get("cycle_number", 0))
        changes = [float(a.get("change_percent", 0)) for a in sorted_assessments]
        n = len(changes)
        mean_change = sum(changes) / n if n > 0 else 0.0
        variance = sum((c - mean_change) ** 2 for c in changes) / n if n > 0 else 0.0
        std_change = variance ** 0.5

        anomalies = []

        for i, change in enumerate(changes):
            z_score = abs((change - mean_change) / std_change) if std_change > 0 else 0
            if z_score > 2.0:
                anomalies.append({
                    "type": "change_percent_outlier",
                    "cycle": i + 1,
                    "value": float(change),
                    "z_score": float(z_score),
                    "severity": "high" if z_score > 3 else "medium",
                    "message": f"第{i+1}周期变化率{change:.1f}%异常偏离正常范围"
                })

        return anomalies

    @staticmethod
    def calculate_response_rate(assessments: List[Dict[str, Any]]) -> float:
        """
        计算客观缓解率 (ORR = CR + PR)
        """
        if not assessments:
            return 0.0

        latest_assessments = {}
        for a in assessments:
            sid = a.get("subject_id")
            if sid not in latest_assessments or a.get("cycle_number", 0) > latest_assessments[sid].get("cycle_number", 0):
                latest_assessments[sid] = a

        if not latest_assessments:
            return 0.0

        responders = sum(
            1 for a in latest_assessments.values()
            if a.get("overall_status") in ["CR", "PR"]
        )

        return round(responders / len(latest_assessments) * 100, 2)

    @staticmethod
    def calculate_disease_control_rate(assessments: List[Dict[str, Any]]) -> float:
        """
        计算疾病控制率 (DCR = CR + PR + SD)
        """
        if not assessments:
            return 0.0

        latest_assessments = {}
        for a in assessments:
            sid = a.get("subject_id")
            if sid not in latest_assessments or a.get("cycle_number", 0) > latest_assessments[sid].get("cycle_number", 0):
                latest_assessments[sid] = a

        if not latest_assessments:
            return 0.0

        controlled = sum(
            1 for a in latest_assessments.values()
            if a.get("overall_status") in ["CR", "PR", "SD"]
        )

        return round(controlled / len(latest_assessments) * 100, 2)