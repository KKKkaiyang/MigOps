"""b04 任务迁移管理功能测试：场景、任务台账导入(覆盖/增量)、状态机、批量状态、备注、自定义台账。"""

import pytest

from tests.conftest import (
    API,
    CODE_BIZ,
    CODE_FORBIDDEN,
    CODE_NOT_FOUND,
    CODE_PARAM,
    assert_biz_error,
    assert_ok,
    csv_upload,
    read_xlsx,
    uid,
    xlsx_upload,
)


@pytest.fixture(scope="function")
def scenario(client, admin_headers, test_space):
    space_id = test_space["id"]
    resp = client.post(f"{API}/b04/scenarios", headers=admin_headers, params={"space_id": space_id},
                       json={"name": uid("任务场景Hive2Hive"), "remark": "功能测试场景"})
    body = assert_ok(resp, 201)
    sc = {"id": body["data"]["id"], "name": body["data"]["name"]}
    yield {"space_id": space_id, "space_name": test_space["space_name"], **sc}
    client.delete(f"{API}/b04/scenarios/{sc['id']}", headers=admin_headers, params={"space_id": space_id})


def _import_tasks(client, admin_headers, scenario, headers, rows, mode="overwrite", ext="xlsx"):
    files = xlsx_upload(headers, rows) if ext == "xlsx" else csv_upload(headers, rows)
    return client.post(
        f"{API}/b04/scenarios/{scenario['id']}/tasks/import", headers=admin_headers,
        params={"space_id": scenario["space_id"], "mode": mode}, files=files,
    )


def _task_headers():
    return ["工作流名称", "任务名称", "脚本名称", "Owner", "迁移状态", "调度状态", "数据校验状态", "输入表", "输出表"]


def test_import_tasks_overwrite_and_incremental(client, admin_headers, scenario):
    space_id, sc_id, space_name = scenario["space_id"], scenario["id"], scenario["space_name"]
    h = _task_headers()
    row = ["wf1", "task1", "t1.sql", "张三", "未开始", "未提交", "未校验", "ods.a", "dwd.a"]
    resp = _import_tasks(client, admin_headers, scenario, h, [row])
    body = assert_ok(resp)
    assert body["data"]["inserted"] == 1 and body["data"]["updated"] == 0

    # 覆盖模式：同 task_uri 改 Owner → updated
    row2 = ["wf1", "task1", "t1.sql", "李四", "改造完成", "已提交", "未校验", "ods.a", "dwd.a"]
    resp = _import_tasks(client, admin_headers, scenario, h, [row2], mode="overwrite")
    body = assert_ok(resp)
    assert body["data"]["updated"] == 1
    # 校验 Owner 已覆盖
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "keyword": "task1"})
    task = assert_ok(resp)["data"]["list"][0]
    assert task["owner"] == "李四"
    assert task["task_uri"] == f"{space_name}://task1@wf1"

    # 增量模式：同 task_uri → skipped，Owner 不变
    row3 = ["wf1", "task1", "t1.sql", "王五", "调度成功", "调度中", "校验通过", "ods.a", "dwd.a"]
    resp = _import_tasks(client, admin_headers, scenario, h, [row3], mode="incremental")
    body = assert_ok(resp)
    assert body["data"]["skipped"] == 1 and body["data"]["updated"] == 0
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "keyword": "task1"})
    assert assert_ok(resp)["data"]["list"][0]["owner"] == "李四"


def test_import_tasks_validation(client, admin_headers, scenario):
    h = _task_headers()
    # 非法迁移状态 → 错误行
    resp = _import_tasks(client, admin_headers, scenario, h,
                         [["wf1", "task_x", "", "", "非法状态", "未提交", "未校验", "", ""]])
    body = assert_ok(resp)
    assert body["data"]["inserted"] == 0 and len(body["data"]["errors"]) == 1
    # 缺必需列
    resp = _import_tasks(client, admin_headers, scenario, ["工作流名称"], [["wf1"]])
    assert_biz_error(resp, CODE_BIZ, "缺少必需列")
    # 非法导入模式
    resp = _import_tasks(client, admin_headers, scenario, h, [["wf1", "t", "", "", "未开始", "未提交", "未校验", "", ""]])
    # 默认 mode=overwrite，需制造非法 mode 单独测
    resp = client.post(
        f"{API}/b04/scenarios/{scenario['id']}/tasks/import", headers=admin_headers,
        params={"space_id": scenario["space_id"], "mode": "nonsense"}, files=xlsx_upload(h, [["wf1", "t", "", "", "未开始", "未提交", "未校验", "", ""]]),
    )
    assert_biz_error(resp, CODE_BIZ, "非法的导入模式")


def test_task_list_filters(client, admin_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    h = _task_headers()
    rows = [
        ["wfA", "ta", "", "甲", "未开始", "未提交", "未校验", "", ""],
        ["wfb", "tb", "", "乙", "改造完成", "已提交", "未校验", "", ""],
    ]
    _import_tasks(client, admin_headers, scenario, h, rows)
    # keyword
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "keyword": "ta"})
    assert assert_ok(resp)["data"]["total"] == 1
    # migration_status
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "migration_status": "改造完成"})
    body = assert_ok(resp)
    assert all(t["migration_status"] == "改造完成" for t in body["data"]["list"])
    # owner
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "owner": "甲"})
    assert assert_ok(resp)["data"]["total"] == 1
    # 分页
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "page": 1, "page_size": 1})
    body = assert_ok(resp)
    assert body["data"]["page_size"] == 1


def test_task_list_tag_filter(client, admin_headers, scenario):
    """验证「含全部标签」(AND) 与「含任一标签」(OR) 筛选语义（需求 F1 / D10）。

    复现并守护此前「含全部标签查不到数据」的缺陷修复：
    多标签 AND 必须用 scalar_subquery 关联计数，否则 Python 层比较会被求值为 False。
    """
    space_id, sc_id = scenario["space_id"], scenario["id"]
    h = _task_headers()
    rows = [
        ["wfA", "tagtask1", "", "甲", "未开始", "未提交", "未校验", "", ""],
        ["wfb", "tagtask2", "", "乙", "未开始", "未提交", "未校验", "", ""],
        ["wfc", "tagtask3", "", "丙", "未开始", "未提交", "未校验", "", ""],
    ]
    _import_tasks(client, admin_headers, scenario, h, rows)

    def task_id(name: str) -> int:
        resp = client.get(
            f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
            params={"space_id": space_id, "keyword": name},
        )
        return assert_ok(resp)["data"]["list"][0]["id"]

    t1, t2, t3 = task_id("tagtask1"), task_id("tagtask2"), task_id("tagtask3")

    def create_tag(name: str) -> int:
        resp = client.post(
            f"{API}/b06/tags", headers=admin_headers,
            params={"space_id": space_id}, json={"tag_name": name},
        )
        return assert_ok(resp, 201)["data"]["id"]

    tag_a, tag_b = create_tag("标签A"), create_tag("标签B")

    # 打标：t1 同时拥有 A、B；t2 仅 A；t3 无标签
    assert_ok(client.put(
        f"{API}/b04/tasks/{t1}/tags", headers=admin_headers,
        params={"space_id": space_id}, json={"tag_ids": [tag_a, tag_b]}))
    assert_ok(client.put(
        f"{API}/b04/tasks/{t2}/tags", headers=admin_headers,
        params={"space_id": space_id}, json={"tag_ids": [tag_a]}))

    def ids_by_tag(tag_ids: list, tag_match: str) -> set:
        resp = client.get(
            f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
            params={
                "space_id": space_id,
                "tag_ids": ",".join(map(str, tag_ids)),
                "tag_match": tag_match,
            },
        )
        return {t["id"] for t in assert_ok(resp)["data"]["list"]}

    # 含全部标签（AND）：同时含 A、B → 仅 t1
    assert ids_by_tag([tag_a, tag_b], "all") == {t1}, "AND 多标签应仅命中同时含全部标签的任务"
    # 含任一标签（OR）：含 A 或 B → t1、t2
    assert ids_by_tag([tag_a, tag_b], "any") == {t1, t2}
    # 单标签 AND：含 A → t1、t2
    assert ids_by_tag([tag_a], "all") == {t1, t2}
    # 单标签 OR：含 B → t1
    assert ids_by_tag([tag_b], "any") == {t1}


def test_task_status_transitions(client, admin_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    h = _task_headers()
    _import_tasks(client, admin_headers, scenario, h,
                  [["wfX", "tstatus", "", "", "未开始", "未提交", "未校验", "", ""]])
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "keyword": "tstatus"})
    task_id = assert_ok(resp)["data"]["list"][0]["id"]

    def change(status):
        return client.post(f"{API}/b04/tasks/{task_id}/status", headers=admin_headers,
                           params={"space_id": space_id}, json={"status": status})

    # 合法链：未开始 → 改造完成 → 调度成功 → 数据校验不通过 → 调度成功(回退) → 数据校验通过
    assert_ok(change("改造完成"))
    assert_ok(change("调度成功"))
    assert_ok(change("数据校验不通过"))
    assert_ok(change("调度成功"))
    assert_ok(change("数据校验通过"))
    # 非法流转：数据校验通过 → 改造完成（不在允许集合）
    assert_biz_error(change("改造完成"), CODE_BIZ, "不能从")
    # 挂起 → 恢复
    assert_ok(change("挂起"))
    assert_ok(change("未开始"))
    # 废弃为终态
    assert_ok(change("废弃"))
    assert_biz_error(change("未开始"), CODE_BIZ, "不能从")


def test_batch_status(client, admin_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    h = _task_headers()
    _import_tasks(client, admin_headers, scenario, h,
                  [["wfB", "b1", "", "", "未开始", "未提交", "未校验", "", ""],
                   ["wfB", "b2", "", "", "未开始", "未提交", "未校验", "", ""]])
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "workflow_name": "wfB"})
    ids = [t["id"] for t in assert_ok(resp)["data"]["list"]]
    # 全部合法 → affected=2
    resp = client.post(f"{API}/b04/scenarios/{sc_id}/tasks/batch-status", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"ids": ids, "status": "改造完成"})
    assert assert_ok(resp)["data"]["affected"] == 2
    # 含非法（其一已改造完成，另一个也改造完成，均不可直接到“客户验收通过”但合法；故意混一非流转）
    # 取一个改造完成任务，批量到“数据校验通过”非法 → 整体拒绝
    resp = client.post(f"{API}/b04/scenarios/{sc_id}/tasks/batch-status", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"ids": ids, "status": "数据校验通过"})
    assert_biz_error(resp, CODE_BIZ, "不能流转为")
    # 非法状态值
    resp = client.post(f"{API}/b04/scenarios/{sc_id}/tasks/batch-status", headers=admin_headers,
                       params={"space_id": space_id}, json={"ids": ids, "status": "非法"})
    assert_biz_error(resp, CODE_BIZ, "非法的迁移状态")


def test_task_notes(client, admin_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    h = _task_headers()
    _import_tasks(client, admin_headers, scenario, h,
                  [["wfN", "tnote", "", "", "未开始", "未提交", "未校验", "", ""]])
    task_id = assert_ok(client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                                   params={"space_id": space_id, "keyword": "tnote"}))["data"]["list"][0]["id"]
    # 创建排查备注
    resp = client.post(f"{API}/b04/tasks/{task_id}/notes", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"note_kind": "troubleshoot", "problem_desc": "调度失败", "fix_plan": "重试"})
    body = assert_ok(resp, 201)
    assert body["data"]["note_kind"] == "troubleshoot"
    # 列表
    resp = client.get(f"{API}/b04/tasks/{task_id}/notes", headers=admin_headers, params={"space_id": space_id})
    assert len(assert_ok(resp)["data"]) >= 1
    # 备注会冗余到任务 latest_note
    resp = client.get(f"{API}/b04/tasks/{task_id}", headers=admin_headers, params={"space_id": space_id})
    assert "调度失败" in assert_ok(resp)["data"]["latest_note"]


def test_saved_views(client, admin_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    h = _task_headers()
    _import_tasks(client, admin_headers, scenario, h,
                  [["wfV", "v1", "", "甲", "未开始", "未提交", "未校验", "", ""],
                   ["wfV", "v2", "", "乙", "改造完成", "已提交", "未校验", "", ""]])
    # 创建自定义台账（含非法键应被清洗）
    resp = client.post(f"{API}/b04/scenarios/{sc_id}/saved-views", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"name": uid("未开始台账"), "description": "只看未开始",
                             "filter_config": {"migration_status": "未开始", "junk": "x", "keyword": "v1"}})
    body = assert_ok(resp, 201)
    view_id = body["data"]["id"]
    # 详情：非法键已被清洗
    resp = client.get(f"{API}/b04/saved-views/{view_id}", headers=admin_headers, params={"space_id": space_id})
    cfg = assert_ok(resp)["data"]["filter_config"]
    assert "junk" not in cfg and cfg.get("migration_status") == "未开始"
    # task_count 应为 1（仅 v1 满足 未开始 + keyword v1）
    assert assert_ok(resp)["data"]["task_count"] == 1
    # 列表
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/saved-views", headers=admin_headers, params={"space_id": space_id})
    items = assert_ok(resp)["data"]
    assert any(v["id"] == view_id for v in items)
    # 列表项须携带 view_mode（供前端「模式」列展示；曾遗漏导致列空白）
    listed = next(v for v in items if v["id"] == view_id)
    assert listed["view_mode"] in ("dynamic", "fixed")
    # 台账任务列表
    resp = client.get(f"{API}/b04/saved-views/{view_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id})
    body = assert_ok(resp)
    assert body["data"]["total"] == 1
    # 更新过滤条件 → count 变化（移除 keyword 限制 → 2 条未开始? 实际仅 v1 未开始，v2 改造完成）
    resp = client.put(f"{API}/b04/saved-views/{view_id}", headers=admin_headers,
                      params={"space_id": space_id}, json={"filter_config": {"migration_status": "未开始"}})
    resp = client.get(f"{API}/b04/saved-views/{view_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id})
    assert assert_ok(resp)["data"]["total"] == 1
    # 导出
    resp = client.get(f"{API}/b04/saved-views/{view_id}/tasks/export", headers=admin_headers,
                      params={"space_id": space_id})
    assert resp.status_code == 200
    assert read_xlsx(resp.content)[0][0] == "工作流名称"
    # 删除
    resp = client.delete(f"{API}/b04/saved-views/{view_id}", headers=admin_headers, params={"space_id": space_id})
    assert_ok(resp)
    resp = client.get(f"{API}/b04/saved-views/{view_id}", headers=admin_headers, params={"space_id": space_id})
    assert_biz_error(resp, CODE_NOT_FOUND, "自定义台账不存在")


def test_create_saved_view_with_members_is_fixed_ledger(client, admin_headers, scenario):
    """R3：勾选具体任务创建台账 → 视图模式为固化台账(view_mode=fixed)，且仅含所选成员。"""
    space_id, sc_id = scenario["space_id"], scenario["id"]
    h = _task_headers()
    _import_tasks(client, admin_headers, scenario, h,
                  [["wfM", "m1", "", "甲", "未开始", "未提交", "未校验", "", ""],
                   ["wfM", "m2", "", "乙", "改造完成", "已提交", "未校验", "", ""],
                   ["wfM", "m3", "", "丙", "未开始", "未提交", "未校验", "", ""]])
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id})
    tasks = assert_ok(resp)["data"]["list"]
    ids = [t["id"] for t in tasks if t["task_name"] in ("m1", "m2")]

    resp = client.post(f"{API}/b04/scenarios/{sc_id}/saved-views", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"name": uid("固化台账"), "description": "勾选创建", "member_ids": ids})
    body = assert_ok(resp, 201)
    view_id = body["data"]["id"]
    # R3：必须固化，且过滤条件清空
    resp = client.get(f"{API}/b04/saved-views/{view_id}", headers=admin_headers,
                      params={"space_id": space_id})
    detail = assert_ok(resp)["data"]
    assert detail["view_mode"] == "fixed"
    assert detail["filter_config"] == {}
    assert detail["task_count"] == 2

    resp = client.get(f"{API}/b04/saved-views/{view_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id})
    body = assert_ok(resp)
    assert body["data"]["total"] == 2
    assert {t["task_name"] for t in body["data"]["list"]} == {"m1", "m2"}


def test_remove_members_converts_dynamic_to_fixed(client, admin_headers, scenario):
    """R4：从(动态)台账移除任务后，不论原类型都转为固化台账，且被移除任务不再出现。"""
    space_id, sc_id = scenario["space_id"], scenario["id"]
    h = _task_headers()
    _import_tasks(client, admin_headers, scenario, h,
                  [["wfR", "r1", "", "甲", "未开始", "未提交", "未校验", "", ""],
                   ["wfR", "r2", "", "乙", "未开始", "未提交", "未校验", "", ""]])
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id})
    tasks = assert_ok(resp)["data"]["list"]
    r1_id = next(t["id"] for t in tasks if t["task_name"] == "r1")

    # 动态台账：所有未开始任务
    resp = client.post(f"{API}/b04/scenarios/{sc_id}/saved-views", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"name": uid("动态台账"), "filter_config": {"migration_status": "未开始"}})
    view_id = assert_ok(resp, 201)["data"]["id"]
    resp = client.get(f"{API}/b04/saved-views/{view_id}", headers=admin_headers,
                      params={"space_id": space_id})
    assert assert_ok(resp)["data"]["view_mode"] == "dynamic"
    assert assert_ok(resp)["data"]["task_count"] == 2

    # R4：移除 r1
    resp = client.post(f"{API}/b04/saved-views/{view_id}/remove-members", headers=admin_headers,
                       params={"space_id": space_id}, json={"task_ids": [r1_id]})
    assert_ok(resp)
    resp = client.get(f"{API}/b04/saved-views/{view_id}", headers=admin_headers,
                      params={"space_id": space_id})
    body = assert_ok(resp)["data"]
    # 不论原类型 → 固化
    assert body["view_mode"] == "fixed"
    assert body["task_count"] == 1
    resp = client.get(f"{API}/b04/saved-views/{view_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id})
    remain = assert_ok(resp)["data"]["list"]
    assert len(remain) == 1 and remain[0]["task_name"] == "r2"


def test_add_members_to_saved_view(client, admin_headers, scenario):
    """补充需求：向台账补充新增任务；固化台账直接加成员，动态台账自动固化为成员集合。"""
    space_id, sc_id = scenario["space_id"], scenario["id"]
    h = _task_headers()
    _import_tasks(client, admin_headers, scenario, h,
                  [["wfA", "a1", "", "甲", "未开始", "未提交", "未校验", "", ""],
                   ["wfA", "a2", "", "乙", "未开始", "未提交", "未校验", "", ""],
                   ["wfA", "a3", "", "丙", "改造完成", "已提交", "未校验", "", ""]])
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id})
    tasks = assert_ok(resp)["data"]["list"]
    a1 = next(t["id"] for t in tasks if t["task_name"] == "a1")
    a2 = next(t["id"] for t in tasks if t["task_name"] == "a2")
    a3 = next(t["id"] for t in tasks if t["task_name"] == "a3")

    # 动态台账：仅 a1/a2 满足未开始
    resp = client.post(f"{API}/b04/scenarios/{sc_id}/saved-views", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"name": uid("动态台账"), "filter_config": {"migration_status": "未开始"}})
    view_id = assert_ok(resp, 201)["data"]["id"]
    resp = client.get(f"{API}/b04/saved-views/{view_id}", headers=admin_headers,
                      params={"space_id": space_id})
    assert assert_ok(resp)["data"]["task_count"] == 2

    # 向动态台账补充 a3 → 自动固化为成员集合
    resp = client.post(f"{API}/b04/saved-views/{view_id}/add-members", headers=admin_headers,
                       params={"space_id": space_id}, json={"task_ids": [a3]})
    assert_ok(resp)
    resp = client.get(f"{API}/b04/saved-views/{view_id}", headers=admin_headers,
                      params={"space_id": space_id})
    body = assert_ok(resp)["data"]
    assert body["view_mode"] == "fixed"
    assert body["task_count"] == 3

    # 向固化台账再补充一条已有 a1（幂等）+ 验证成员完整
    resp = client.post(f"{API}/b04/saved-views/{view_id}/add-members", headers=admin_headers,
                       params={"space_id": space_id}, json={"task_ids": [a1, a2]})
    assert_ok(resp)
    resp = client.get(f"{API}/b04/saved-views/{view_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id})
    names = {t["task_name"] for t in assert_ok(resp)["data"]["list"]}
    assert names == {"a1", "a2", "a3"}


def test_member_read_and_outsider_forbidden(client, admin_headers, member_headers, outsider_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    # L2 成员可读列表
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=member_headers, params={"space_id": space_id})
    assert_ok(resp)
    # 非成员越权 → 403
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=outsider_headers, params={"space_id": space_id})
    assert_biz_error(resp, CODE_FORBIDDEN, "无权访问")


def test_scenario_delete_cascades(client, admin_headers, test_space):
    space_id = test_space["id"]
    resp = client.post(f"{API}/b04/scenarios", headers=admin_headers, params={"space_id": space_id},
                       json={"name": uid("b04级联场景")})
    sc_id = assert_ok(resp, 201)["data"]["id"]
    h = _task_headers()
    _import_tasks(client, admin_headers, {"id": sc_id, "space_id": space_id}, h,
                  [["wfC", "ct", "", "", "未开始", "未提交", "未校验", "", ""]])
    resp = client.delete(f"{API}/b04/scenarios/{sc_id}", headers=admin_headers, params={"space_id": space_id})
    assert_ok(resp)
    body = assert_ok(client.get(f"{API}/b04/scenarios", headers=admin_headers, params={"space_id": space_id}))
    assert all(s["id"] != sc_id for s in body["data"])
