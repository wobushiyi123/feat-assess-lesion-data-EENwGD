import json
import time
import urllib.request
import urllib.error
import urllib.parse

BASE = "http://127.0.0.1:8099"
SUBJECT_ID = "TEST_CYC_GRRP_" + time.strftime("%H%M%S")


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
    # 登录
    lr = urllib.request.Request(
        BASE + "/api/auth/login",
        data=urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(lr, timeout=20) as resp:
        token = json.loads(resp.read())["access_token"]
    print("login OK")

    st, subj = req("POST", "/api/subjects", token, {"subject_id": SUBJECT_ID, "name": SUBJECT_ID})
    sid = subj["id"]
    print("subject", sid)

    try:
        # 1) 新建评估 A（周期2，检查日 2026-07-10），含 1 条非靶
        ntl1 = [{"name": "肝转移", "location": "肝", "organ": "肝", "lesion_id": "NT1",
                 "baseline_status": "持续存在", "status": "持续存在",
                 "baseline_is_checked": True, "current_is_checked": True,
                 "exam_date": "2026-06-01", "exam_method": "增强CT",
                 "current_exam_date": "2026-07-10", "current_exam_method": "增强CT"}]
        st, a = req("POST", "/api/assessments", token, {
            "subject_id": sid, "cycle_number": 2, "assessment_date": "2026-07-10",
            "non_target_lesions": ntl1})
        assert st in (200, 201), f"create A failed {st} {a}"
        aid = a["id"]
        print("评估A id=", aid, "cycle=", a["cycle_number"], "date=", a["assessment_date"][:10])

        # 2) 模拟前端“新增病灶·同日期 2026-07-10”→ 应追加到评估A（复用周期2），不新建周期
        st, add = req("POST", f"/api/assessments/{aid}/non-target-lesions", token, {
            "name": "腹膜后淋巴结", "location": "腹膜后", "organ": "腹膜后", "lesion_id": "NT2",
            "baseline_status": "持续存在", "status": "持续存在",
            "baseline_is_checked": True, "current_is_checked": True,
            "exam_date": "2026-06-01", "exam_method": "增强CT",
            "current_exam_date": "2026-07-10", "current_exam_method": "增强CT"})
        assert st in (200, 201), f"append failed {st} {add}"

        # 校验：受试者下评估数仍为 1，且该评估含 2 条非靶
        st, det = req("GET", f"/api/subjects/{sid}", token, )
        evals = det.get("assessments", [])
        assert len(evals) == 1, f"评估数应为1（归并同日期），实际 {len(evals)}"
        ev = evals[0]
        ncount = len(ev.get("non_target_lesions") or [])
        assert ncount == 2, f"非靶应为2条（追加），实际 {ncount}"
        assert ev["cycle_number"] == 2, f"周期应仍为2，实际 {ev['cycle_number']}"
        print("OK 同日期归并: 评估数=1, 非靶=2, 周期=2 ✓")

        # 3) 模拟前端“新增病灶·新日期 2026-08-15”→ 应新建周期3
        st, b = req("POST", "/api/assessments", token, {
            "subject_id": sid, "cycle_number": 3, "assessment_date": "2026-08-15",
            "non_target_lesions": [{"name": "肺转移", "location": "肺", "organ": "肺",
                "lesion_id": "NT3", "baseline_status": "持续存在", "status": "进展",
                "baseline_is_checked": True, "current_is_checked": True,
                "exam_date": "2026-06-01", "exam_method": "增强CT",
                "current_exam_date": "2026-08-15", "current_exam_method": "增强CT"}]})
        assert st in (200, 201), f"create B failed {st} {b}"
        print("评估B id=", b["id"], "cycle=", b["cycle_number"], "date=", b["assessment_date"][:10])

        st, det2 = req("GET", f"/api/subjects/{sid}", token)
        evals2 = det2.get("assessments", [])
        assert len(evals2) == 2, f"评估数应为2，实际 {len(evals2)}"
        by_cycle = sorted(evals2, key=lambda x: x["cycle_number"])
        assert by_cycle[0]["cycle_number"] == 2 and by_cycle[1]["cycle_number"] == 3
        print("OK 新日期新建: 评估数=2, 周期=[2,3] ✓")

        print("\n=== 周期归并逻辑校验通过 ===")
    finally:
        req("DELETE", f"/api/subjects/{sid}", token)
        print("cleanup done")


if __name__ == "__main__":
    main()
