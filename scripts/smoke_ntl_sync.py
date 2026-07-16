import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8099"
import time
SUBJECT_ID = "TEST_NTL_SYNC_" + time.strftime("%H%M%S")


def req(method, path, token=None, body=None):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8")
            return e.code, json.loads(raw) if raw.strip() else {}
        except Exception:
            return e.code, {}


def main():
    # 1) 登录（OAuth2 表单格式）
    import urllib.parse
    login_url = BASE + "/api/auth/login"
    login_data = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode("utf-8")
    lr = urllib.request.Request(login_url, data=login_data,
                                headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(lr, timeout=20) as resp:
        login = json.loads(resp.read().decode("utf-8"))
    st = 200
    assert "access_token" in login, f"login failed: {login}"
    token = login["access_token"]
    print("login OK")

    # 2) 建受试者
    st, subj = req("POST", "/api/subjects", token, {"subject_id": SUBJECT_ID, "name": SUBJECT_ID})
    assert st in (200, 201), f"create subject failed: {st} {subj}"
    subject_db_id = subj["id"]
    print("subject created id=", subject_db_id)

    try:
        # 3) 建评估 + 1 个非靶病灶（current_exam_date=2026-07-10, status=持续存在）
        ntl = [{
            "name": "肝多发转移",
            "location": "肝",
            "organ": "肝",
            "lesion_id": "NT1",
            "baseline_status": "持续存在",
            "status": "持续存在",
            "baseline_is_checked": True,
            "current_is_checked": True,
            "exam_date": "2026-06-01",
            "exam_method": "增强CT",
            "current_exam_date": "2026-07-10",
            "current_exam_method": "增强CT",
        }]
        st, a = req("POST", "/api/assessments", token, {
            "subject_id": subject_db_id,
            "cycle_number": 2,
            "assessment_date": "2026-07-10",  # AssessmentCreate 必填，与初始非靶 current_exam_date 对齐
            "non_target_lesions": ntl,
        })
        assert st in (200, 201), f"create assessment failed: {st} {a}"
        aid = a["id"]
        print("assessment created id=", aid)
        print("FULL assessment:", json.dumps(a, ensure_ascii=False)[:1200])

        # 核对：日期已同步 + 非靶评估实际生成
        adate = (a.get("assessment_date") or "")[:10]
        assert adate == "2026-07-10", f"assessment_date 未同步到非靶 current_exam_date: {adate}"
        assert a["non_target_status"] == "Non-CR/Non-PD", f"非靶状态异常: {a['non_target_status']}"
        assert a["overall_status"] == "Non-CR/Non-PD", f"整体状态异常: {a['overall_status']}"
        print("OK 初始: assessment_date=", adate,
              "non_target_status=", a["non_target_status"], "overall=", a["overall_status"])

        # 4) 再追加一个更晚日期的非靶病灶（current_exam_date=2026-08-15）
        st, add = req("POST", f"/api/assessments/{aid}/non-target-lesions", token, {
            "name": "腹膜后淋巴结",
            "location": "腹膜后",
            "organ": "腹膜后",
            "lesion_id": "NT2",
            "baseline_status": "持续存在",
            "status": "进展",
            "baseline_is_checked": True,
            "current_is_checked": True,
            "exam_date": "2026-06-01",
            "exam_method": "增强CT",
            "current_exam_date": "2026-08-15",
            "current_exam_method": "增强CT",
        })
        assert st in (200, 201), f"add ntl failed: {st} {add}"

        st, a2 = req("GET", f"/api/assessments/{aid}", token)
        adate2 = (a2.get("assessment_date") or "")[:10]
        assert adate2 == "2026-08-15", f"assessment_date 未更新到更晚的非靶 current_exam_date: {adate2}"
        # 第2个非靶病灶明确进展 → 整体应为 PD
        assert a2["non_target_status"] == "PD", f"非靶状态应为PD: {a2['non_target_status']}"
        assert a2["overall_status"] == "PD", f"整体状态应为PD: {a2['overall_status']}"
        print("OK 追加后: assessment_date=", adate2,
              "non_target_status=", a2["non_target_status"], "overall=", a2["overall_status"])

        print("\n=== 全部校验通过 ===")
    finally:
        req("DELETE", f"/api/subjects/{subject_db_id}", token)
        print("cleanup done")


if __name__ == "__main__":
    main()
