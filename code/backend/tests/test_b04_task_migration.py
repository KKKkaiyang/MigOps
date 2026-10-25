"""b04 任务迁移管理功能测试：默认模板、模板驱动导入(覆盖/增量)、5维状态、批量状态、备注、自定义台账、扩展字段。

兼容《任务迁移-任务台账数据模型重构需求》D1~D7：
- 导入列由空间模板生成（默认模板 14 基础字段 + 9 必填锁定，含数据校验结果）；
- 状态改为 5 个独立维度，互不约束；
- 扩展字段按空间模板动态加列 f_n。
"""

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


# ── 默认模板（14 基础字段，顺序同 seed_default_template） ──
DEF_HEADERS = [
    "项目名称", "任务名称", "迁移负责人", "任务活跃状态", "迁移状态",
    "双跑调度状态", "数据校验状态", "客户验收状态", "工作流名称", "归属环境",
    "归属业务", "任务类型", "备注信息", "数据校验结果",
]


def _row(**kw) -> list:
    """按 DEF_HEADERS 顺序构造一行，必填项给默认值。"""
    defaults = {
        "项目名称": "default",
        "任务名称": "task",
        "迁移负责人": "张三",
        "任务活跃状态": "草稿",
        "迁移状态": "未开始",
        "双跑调度状态": "未调度",
        "数据校验状态": "校验通过",
        "客户验收状态": "通过",
        "工作流名称": "wf",
        "归属环境": "生产",
        "归属业务": "",
        "任务类型": "",
        "备注信息": "",
        "数据校验结果": "无校验结果",
    }
    defaults.update(kw)
    return [defaults[h] for h in DEF_HEADERS]


def _import_tasks(client, admin_headers, scenario, headers, rows, mode="overwrite", ext="xlsx"):
    files = xlsx_upload(headers, rows) if ext == "xlsx" else csv_upload(headers, rows)
    return client.post(
        f"{API}/b04/scenarios/{scenario['id']}/tasks/import", headers=admin_headers,
        params={"space_id": scenario["space_id"], "mode": mode}, files=files,
    )


def test_default_template_seeded(client, admin_headers, test_space):
    """空间初始化后应有默认迁移模板（14 字段 + 9 必填锁定，数据校验结果必选但列表默认不展示）。"""
    space_id = test_space["id"]
    resp = client.get(f"{API}/b04/spaces/{space_id}/template", headers=admin_headers,
                      params={"space_id": space_id})
    body = assert_ok(resp)
    cfg = body["data"]["config_json"]
    fields = cfg["fields"]
    assert len(fields) == 14
    required = {f["field_key"] for f in fields if f["is_required"]}
    assert required == {
        "project_name", "task_name", "migration_owner", "active_status",
        "migration_status", "dualrun_status", "check_status", "acceptance_status",
        "check_result",
    }
    check_result = next(f for f in fields if f["field_key"] == "check_result")
    assert check_result["display_in_list"] is False
    orders = [f["order"] for f in fields]
    assert len(set(orders)) == len(orders)


def test_import_tasks_overwrite_and_incremental(client, admin_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    row = _row(项目名称="default", 任务名称="task1", 工作流名称="wf1", 迁移负责人="张三")
    resp = _import_tasks(client, admin_headers, scenario, DEF_HEADERS, [row])
    body = assert_ok(resp)
    assert body["data"]["inserted"] == 1 and body["data"]["updated"] == 0

    # 覆盖模式：同 task_uri 改 迁移负责人 → updated
    row2 = _row(项目名称="default", 任务名称="task1", 工作流名称="wf1", 迁移负责人="李四", 迁移状态="已完成")
    resp = _import_tasks(client, admin_headers, scenario, DEF_HEADERS, [row2], mode="overwrite")
    body = assert_ok(resp)
    assert body["data"]["updated"] == 1
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "keyword": "task1"})
    task = assert_ok(resp)["data"]["list"][0]
    assert task["migration_owner"] == "李四"
    assert task["task_uri"] == "default://task1@wf1"

    # 增量模式：同 task_uri → skipped，迁移负责人不变
    row3 = _row(项目名称="default", 任务名称="task1", 工作流名称="wf1", 迁移负责人="王五", 迁移状态="已完成")
    resp = _import_tasks(client, admin_headers, scenario, DEF_HEADERS, [row3], mode="incremental")
    body = assert_ok(resp)
    assert body["data"]["skipped"] == 1 and body["data"]["updated"] == 0
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "keyword": "task1"})
    assert assert_ok(resp)["data"]["list"][0]["migration_owner"] == "李四"


def test_import_tasks_validation(client, admin_headers, scenario):
    # 非法迁移状态 → 错误行
    resp = _import_tasks(client, admin_headers, scenario, DEF_HEADERS,
                         [_row(任务名称="task_x", 迁移状态="非法状态")])
    body = assert_ok(resp)
    assert body["data"]["inserted"] == 0 and len(body["data"]["errors"]) == 1
    # 必填列缺失：仅给非必填的 工作流名称 → 必填字段缺失（行级错误，非顶层业务错误）
    resp = _import_tasks(client, admin_headers, scenario, ["工作流名称"], [["wf1"]])
    body = assert_ok(resp)
    assert any("必填字段" in e["message"] for e in body["data"]["errors"])
    # 非法导入模式
    resp = client.post(
        f"{API}/b04/scenarios/{scenario['id']}/tasks/import", headers=admin_headers,
        params={"space_id": scenario["space_id"], "mode": "nonsense"},
        files=xlsx_upload(DEF_HEADERS, [_row(任务名称="t")]),
    )
    assert_biz_error(resp, CODE_BIZ, "非法的导入模式")


def test_task_list_filters(client, admin_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    rows = [
        _row(项目名称="default", 任务名称="ta", 迁移负责人="甲", 迁移状态="未开始", 工作流名称="wfA"),
        _row(项目名称="default", 任务名称="tb", 迁移负责人="乙", 迁移状态="已完成", 工作流名称="wfb"),
    ]
    _import_tasks(client, admin_headers, scenario, DEF_HEADERS, rows)
    # keyword
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "keyword": "ta"})
    assert assert_ok(resp)["data"]["total"] == 1
    # migration_status
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "migration_status": "已完成"})
    body = assert_ok(resp)
    assert all(t["migration_status"] == "已完成" for t in body["data"]["list"])
    # migration_owner
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "migration_owner": "甲"})
    assert assert_ok(resp)["data"]["total"] == 1
    # 分页
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "page": 1, "page_size": 1})
    body = assert_ok(resp)
    assert body["data"]["page_size"] == 1


def test_task_list_tag_filter(client, admin_headers, scenario):
    """验证「含全部标签」(AND) 与「含任一标签」(OR) 筛选语义（需求 F1 / D10）。"""
    space_id, sc_id = scenario["space_id"], scenario["id"]
    rows = [
        _row(任务名称="tagtask1", 迁移负责人="甲"),
        _row(任务名称="tagtask2", 迁移负责人="乙"),
        _row(任务名称="tagtask3", 迁移负责人="丙"),
    ]
    _import_tasks(client, admin_headers, scenario, DEF_HEADERS, rows)

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

    assert ids_by_tag([tag_a, tag_b], "all") == {t1}
    assert ids_by_tag([tag_a, tag_b], "any") == {t1, t2}
    assert ids_by_tag([tag_a], "all") == {t1, t2}
    assert ids_by_tag([tag_b], "any") == {t1}


def test_task_status_dimensions(client, admin_headers, scenario):
    """5 维状态独立更新：各维度互不约束，非法取值被拒。"""
    space_id, sc_id = scenario["space_id"], scenario["id"]
    _import_tasks(client, admin_headers, scenario, DEF_HEADERS,
                  [_row(任务名称="tstatus", 工作流名称="wfX")])
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "keyword": "tstatus"})
    task_id = assert_ok(resp)["data"]["list"][0]["id"]

    def change(**dims):
        return client.post(f"{API}/b04/tasks/{task_id}/status", headers=admin_headers,
                           params={"space_id": space_id}, json=dims)

    # 各维度独立更新
    assert_ok(change(migration_status="已完成"))
    assert_ok(change(active_status="正常调度"))
    assert_ok(change(dualrun_status="调度中"))
    # 校验：读取明细，各维度已更新
    resp = client.get(f"{API}/b04/tasks/{task_id}", headers=admin_headers,
                      params={"space_id": space_id})
    t = assert_ok(resp)["data"]
    assert t["migration_status"] == "已完成"
    assert t["active_status"] == "正常调度"
    assert t["dualrun_status"] == "调度中"
    # 非法取值 → 参数校验错误（Schema 层拦截）
    assert_biz_error(change(migration_status="非法状态"), CODE_PARAM)
    # 空 payload → 业务错误
    assert_biz_error(change(), CODE_BIZ, "未提供")


def test_batch_status(client, admin_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    _import_tasks(client, admin_headers, scenario, DEF_HEADERS,
                  [_row(任务名称="b1", 工作流名称="wfB"),
                   _row(任务名称="b2", 工作流名称="wfB")])
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "workflow_name": "wfB"})
    ids = [t["id"] for t in assert_ok(resp)["data"]["list"]]
    # 按维度批量更新 → affected=2
    resp = client.post(f"{API}/b04/scenarios/{sc_id}/tasks/batch-status", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"ids": ids, "dimension": "migration_status", "value": "已完成"})
    assert assert_ok(resp)["data"]["affected"] == 2
    # 非法取值 → 整体拒绝（Schema 层拦截）
    resp = client.post(f"{API}/b04/scenarios/{sc_id}/tasks/batch-status", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"ids": ids, "dimension": "migration_status", "value": "非法"})
    assert_biz_error(resp, CODE_PARAM)
    # 非法维度（Schema 层拦截）
    resp = client.post(f"{API}/b04/scenarios/{sc_id}/tasks/batch-status", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"ids": ids, "dimension": "unknown", "value": "x"})
    assert_biz_error(resp, CODE_PARAM)


def test_task_notes(client, admin_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    _import_tasks(client, admin_headers, scenario, DEF_HEADERS,
                  [_row(任务名称="tnote", 工作流名称="wfN")])
    task_id = assert_ok(client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                                   params={"space_id": space_id, "keyword": "tnote"}))["data"]["list"][0]["id"]
    resp = client.post(f"{API}/b04/tasks/{task_id}/notes", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"note_kind": "troubleshoot", "problem_desc": "调度失败", "fix_plan": "重试"})
    body = assert_ok(resp, 201)
    assert body["data"]["note_kind"] == "troubleshoot"
    # 列表
    resp = client.get(f"{API}/b04/tasks/{task_id}/notes", headers=admin_headers, params={"space_id": space_id})
    assert len(assert_ok(resp)["data"]) >= 1


def test_task_by_key(client, admin_headers, scenario):
    """GET /b04/tasks/by-key：按 项目名称+任务名称 定位任务（D5 血缘任务名直达）。"""
    space_id, sc_id = scenario["space_id"], scenario["id"]
    _import_tasks(client, admin_headers, scenario, DEF_HEADERS,
                  [_row(项目名称="projX", 任务名称="taskX", 工作流名称="wfX")])
    bk = client.get(f"{API}/b04/tasks/by-key", headers=admin_headers,
                    params={"space_id": space_id, "project_name": "projX", "task_name": "taskX"})
    body = assert_ok(bk)
    assert body["data"]["task_name"] == "taskX"
    assert body["data"]["project_name"] == "projX"

    # 未命中 → 业务码 40400
    resp = client.get(f"{API}/b04/tasks/by-key", headers=admin_headers,
                      params={"space_id": space_id, "project_name": "projX", "task_name": "nope"})
    assert_biz_error(resp, CODE_NOT_FOUND)


def test_template_import_excel(client, admin_headers, scenario):
    """下载的导入模板 Excel 首列应为模板第一个字段（项目名称）。"""
    space_id, sc_id = scenario["space_id"], scenario["id"]
    resp = client.get(f"{API}/b04/spaces/{space_id}/template/import-excel", headers=admin_headers,
                      params={"space_id": space_id})
    assert resp.status_code == 200
    assert read_xlsx(resp.content)[0][0] == "项目名称"


def test_saved_views(client, admin_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    _import_tasks(client, admin_headers, scenario, DEF_HEADERS,
                  [_row(任务名称="v1", 迁移负责人="甲", 迁移状态="未开始", 工作流名称="wfV"),
                   _row(任务名称="v2", 迁移负责人="乙", 迁移状态="已完成", 工作流名称="wfV")])
    resp = client.post(f"{API}/b04/scenarios/{sc_id}/saved-views", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"name": uid("未开始台账"), "description": "只看未开始",
                             "filter_config": {"migration_status": "未开始", "junk": "x", "keyword": "v1"}})
    body = assert_ok(resp, 201)
    view_id = body["data"]["id"]
    resp = client.get(f"{API}/b04/saved-views/{view_id}", headers=admin_headers, params={"space_id": space_id})
    cfg = assert_ok(resp)["data"]["filter_config"]
    assert "junk" not in cfg and cfg.get("migration_status") == "未开始"
    assert assert_ok(resp)["data"]["task_count"] == 1
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/saved-views", headers=admin_headers, params={"space_id": space_id})
    items = assert_ok(resp)["data"]
    assert any(v["id"] == view_id for v in items)
    listed = next(v for v in items if v["id"] == view_id)
    assert listed["view_mode"] in ("dynamic", "fixed")
    resp = client.get(f"{API}/b04/saved-views/{view_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id})
    body = assert_ok(resp)
    assert body["data"]["total"] == 1
    resp = client.put(f"{API}/b04/saved-views/{view_id}", headers=admin_headers,
                      params={"space_id": space_id}, json={"filter_config": {"migration_status": "未开始"}})
    resp = client.get(f"{API}/b04/saved-views/{view_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id})
    assert assert_ok(resp)["data"]["total"] == 1
    resp = client.get(f"{API}/b04/saved-views/{view_id}/tasks/export", headers=admin_headers,
                      params={"space_id": space_id})
    assert resp.status_code == 200
    assert read_xlsx(resp.content)[0][0] == "项目名称"
    resp = client.delete(f"{API}/b04/saved-views/{view_id}", headers=admin_headers, params={"space_id": space_id})
    assert_ok(resp)
    resp = client.get(f"{API}/b04/saved-views/{view_id}", headers=admin_headers, params={"space_id": space_id})
    assert_biz_error(resp, CODE_NOT_FOUND, "自定义台账不存在")


def test_create_saved_view_with_members_is_fixed_ledger(client, admin_headers, scenario):
    """R3：勾选具体任务创建台账 → 固化台账，仅含所选成员。"""
    space_id, sc_id = scenario["space_id"], scenario["id"]
    _import_tasks(client, admin_headers, scenario, DEF_HEADERS,
                  [_row(任务名称="m1", 迁移负责人="甲", 迁移状态="未开始", 工作流名称="wfM"),
                   _row(任务名称="m2", 迁移负责人="乙", 迁移状态="已完成", 工作流名称="wfM"),
                   _row(任务名称="m3", 迁移负责人="丙", 迁移状态="未开始", 工作流名称="wfM")])
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id})
    tasks = assert_ok(resp)["data"]["list"]
    ids = [t["id"] for t in tasks if t["task_name"] in ("m1", "m2")]

    resp = client.post(f"{API}/b04/scenarios/{sc_id}/saved-views", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"name": uid("固化台账"), "description": "勾选创建", "member_ids": ids})
    body = assert_ok(resp, 201)
    view_id = body["data"]["id"]
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
    """R4：从(动态)台账移除任务后转为固化台账，被移除任务不再出现。"""
    space_id, sc_id = scenario["space_id"], scenario["id"]
    _import_tasks(client, admin_headers, scenario, DEF_HEADERS,
                  [_row(任务名称="r1", 迁移负责人="甲", 迁移状态="未开始", 工作流名称="wfR"),
                   _row(任务名称="r2", 迁移负责人="乙", 迁移状态="未开始", 工作流名称="wfR")])
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id})
    tasks = assert_ok(resp)["data"]["list"]
    r1_id = next(t["id"] for t in tasks if t["task_name"] == "r1")

    resp = client.post(f"{API}/b04/scenarios/{sc_id}/saved-views", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"name": uid("动态台账"), "filter_config": {"migration_status": "未开始"}})
    view_id = assert_ok(resp, 201)["data"]["id"]
    resp = client.get(f"{API}/b04/saved-views/{view_id}", headers=admin_headers,
                      params={"space_id": space_id})
    assert assert_ok(resp)["data"]["view_mode"] == "dynamic"
    assert assert_ok(resp)["data"]["task_count"] == 2

    resp = client.post(f"{API}/b04/saved-views/{view_id}/remove-members", headers=admin_headers,
                       params={"space_id": space_id}, json={"task_ids": [r1_id]})
    assert_ok(resp)
    resp = client.get(f"{API}/b04/saved-views/{view_id}", headers=admin_headers,
                      params={"space_id": space_id})
    body = assert_ok(resp)["data"]
    assert body["view_mode"] == "fixed"
    assert body["task_count"] == 1
    resp = client.get(f"{API}/b04/saved-views/{view_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id})
    remain = assert_ok(resp)["data"]["list"]
    assert len(remain) == 1 and remain[0]["task_name"] == "r2"


def test_add_members_to_saved_view(client, admin_headers, scenario):
    """补充需求：向台账补充新增任务；动态台账自动固化为成员集合。"""
    space_id, sc_id = scenario["space_id"], scenario["id"]
    _import_tasks(client, admin_headers, scenario, DEF_HEADERS,
                  [_row(任务名称="a1", 迁移负责人="甲", 迁移状态="未开始", 工作流名称="wfA"),
                   _row(任务名称="a2", 迁移负责人="乙", 迁移状态="未开始", 工作流名称="wfA"),
                   _row(任务名称="a3", 迁移负责人="丙", 迁移状态="已完成", 工作流名称="wfA")])
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id})
    tasks = assert_ok(resp)["data"]["list"]
    a1 = next(t["id"] for t in tasks if t["task_name"] == "a1")
    a2 = next(t["id"] for t in tasks if t["task_name"] == "a2")
    a3 = next(t["id"] for t in tasks if t["task_name"] == "a3")

    resp = client.post(f"{API}/b04/scenarios/{sc_id}/saved-views", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"name": uid("动态台账"), "filter_config": {"migration_status": "未开始"}})
    view_id = assert_ok(resp, 201)["data"]["id"]
    resp = client.get(f"{API}/b04/saved-views/{view_id}", headers=admin_headers,
                      params={"space_id": space_id})
    assert assert_ok(resp)["data"]["task_count"] == 2

    resp = client.post(f"{API}/b04/saved-views/{view_id}/add-members", headers=admin_headers,
                       params={"space_id": space_id}, json={"task_ids": [a3]})
    assert_ok(resp)
    resp = client.get(f"{API}/b04/saved-views/{view_id}", headers=admin_headers,
                      params={"space_id": space_id})
    body = assert_ok(resp)["data"]
    assert body["view_mode"] == "fixed"
    assert body["task_count"] == 3

    resp = client.post(f"{API}/b04/saved-views/{view_id}/add-members", headers=admin_headers,
                      params={"space_id": space_id}, json={"task_ids": [a1, a2]})
    assert_ok(resp)
    resp = client.get(f"{API}/b04/saved-views/{view_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id})
    names = {t["task_name"] for t in assert_ok(resp)["data"]["list"]}
    assert names == {"a1", "a2", "a3"}


def test_extension_field_template_and_import(client, admin_headers, scenario):
    """扩展字段：模板追加 enum 扩展字段 → 动态加列 f_1；导入写入；列表/明细返回 ext。"""
    space_id, sc_id = scenario["space_id"], scenario["id"]
    # 取当前默认模板，追加一个 enum 扩展字段「任务分级」
    resp = client.get(f"{API}/b04/spaces/{space_id}/template", headers=admin_headers,
                      params={"space_id": space_id})
    cfg = assert_ok(resp)["data"]["config_json"]
    fields = cfg["fields"]
    max_order = max(f["order"] for f in fields)
    fields.append({
        "field_key": "ext_1", "field_label": "任务分级", "field_source": "extension",
        "is_required": False, "display_in_list": True, "order": max_order + 1,
        "ext_type": "enum", "enum_options": [{"code": "P0", "label": "P0"}],
    })
    resp = client.post(f"{API}/b04/spaces/{space_id}/template", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"name": "带扩展字段模板", "config_json": {"fields": fields}})
    assert_ok(resp, 201)

    headers = DEF_HEADERS + ["任务分级"]
    row = _row(任务名称="exttask", 工作流名称="wfE") + ["P0"]
    resp = _import_tasks(client, admin_headers, scenario, headers, [row])
    assert_ok(resp)["data"]["inserted"] == 1

    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "keyword": "exttask"})
    task = assert_ok(resp)["data"]["list"][0]
    assert task["ext"].get("f_1") == "P0"


def test_member_read_and_outsider_forbidden(client, admin_headers, member_headers, outsider_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=member_headers, params={"space_id": space_id})
    assert_ok(resp)
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=outsider_headers, params={"space_id": space_id})
    assert_biz_error(resp, CODE_FORBIDDEN, "无权访问")


def test_scenario_delete_cascades(client, admin_headers, test_space):
    space_id = test_space["id"]
    resp = client.post(f"{API}/b04/scenarios", headers=admin_headers, params={"space_id": space_id},
                       json={"name": uid("b04级联场景")})
    sc_id = assert_ok(resp, 201)["data"]["id"]
    _import_tasks(client, admin_headers, {"id": sc_id, "space_id": space_id}, DEF_HEADERS,
                  [_row(任务名称="ct", 工作流名称="wfC")])
    resp = client.delete(f"{API}/b04/scenarios/{sc_id}", headers=admin_headers, params={"space_id": space_id})
    assert_ok(resp)
    body = assert_ok(client.get(f"{API}/b04/scenarios", headers=admin_headers, params={"space_id": space_id}))
    assert all(s["id"] != sc_id for s in body["data"])


def test_import_row_limit_50000(client, admin_headers, scenario):
    """导入基础数据单文件上限 50000 行（b04 专用；超过即拒绝，且不写库）。"""
    space_id, sc_id = scenario["space_id"], scenario["id"]
    rows = [_row(任务名称=f"bulk{i}", 工作流名称="wfBulk") for i in range(50001)]
    resp = _import_tasks(client, admin_headers, scenario, DEF_HEADERS, rows)
    assert_biz_error(resp, CODE_BIZ, "50000")
    # 拒绝后库中无任何写入
    body = assert_ok(client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                                params={"space_id": space_id, "keyword": "bulk"}))["data"]
    assert body["total"] == 0


def test_import_relaxed_required_fields(client, admin_headers, scenario):
    """B04-08：导入仅强制 项目名称/任务名称，其余字段留空落 NULL；覆盖可用空值清空。"""
    space_id, sc_id = scenario["space_id"], scenario["id"]
    # 仅填 项目名称/任务名称/工作流名称，其余全空 → 正常导入且落 NULL
    row = _row(项目名称="default", 任务名称="relaxed1", 工作流名称="wfR", 迁移负责人="",
               任务活跃状态="", 迁移状态="", 双跑调度状态="", 数据校验状态="", 客户验收状态="",
               归属环境="", 归属业务="", 任务类型="", 备注信息="", 数据校验结果="")
    resp = _import_tasks(client, admin_headers, scenario, DEF_HEADERS, [row])
    body = assert_ok(resp)
    assert body["data"]["inserted"] == 1 and not body["data"]["errors"]

    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "keyword": "relaxed1"})
    task = assert_ok(resp)["data"]["list"][0]
    assert task["task_uri"] == "default://relaxed1@wfR"
    for f in ("migration_owner", "active_status", "migration_status", "dualrun_status",
              "env", "check_status", "acceptance_status", "check_result"):
        assert task[f] is None, f"{f} 应落 NULL"

    # 两项关键字段任一缺失 → 行级错误
    resp = _import_tasks(client, admin_headers, scenario, DEF_HEADERS, [
        _row(项目名称="", 任务名称="noproj", 工作流名称="wfN"),
        _row(项目名称="default", 任务名称="", 工作流名称="wfN"),
    ])
    body = assert_ok(resp)
    assert body["data"]["inserted"] == 0 and len(body["data"]["errors"]) == 2
    assert all("必填字段" in e["message"] for e in body["data"]["errors"])

    # 覆盖导入：先填值，再用空值覆盖 → 清空为 NULL
    _import_tasks(client, admin_headers, scenario, DEF_HEADERS,
                  [_row(项目名称="default", 任务名称="relaxed1", 工作流名称="wfR",
                        迁移负责人="张三", 归属环境="生产", 迁移状态="已完成")])
    resp = _import_tasks(client, admin_headers, scenario, DEF_HEADERS, [row])
    assert assert_ok(resp)["data"]["updated"] == 1
    resp = client.get(f"{API}/b04/scenarios/{sc_id}/tasks", headers=admin_headers,
                      params={"space_id": space_id, "keyword": "relaxed1"})
    task = assert_ok(resp)["data"]["list"][0]
    assert task["migration_owner"] is None and task["env"] is None and task["migration_status"] is None


def test_template_reorder_drives_import_template_order(client, admin_headers, scenario):
    """B04-07：模版顺序决定导入模板列顺序；保存后 order 连续唯一。"""
    space_id = scenario["space_id"]
    resp = client.get(f"{API}/b04/spaces/{space_id}/template", headers=admin_headers,
                      params={"space_id": space_id})
    tpl = assert_ok(resp)["data"]
    fields = tpl["config_json"]["fields"]
    original_keys = [f["field_key"] for f in fields]

    def _save(ordered):
        payload = [dict(f) for f in ordered]
        for i, f in enumerate(payload, start=1):
            f["order"] = i
        return client.post(f"{API}/b04/spaces/{space_id}/template", headers=admin_headers,
                           params={"space_id": space_id},
                           json={"name": tpl["name"], "config_json": {"fields": payload}})

    try:
        # 反转字段顺序并保存
        reordered = list(reversed(fields))
        assert_ok(_save(reordered), 201)
        resp = client.get(f"{API}/b04/spaces/{space_id}/template", headers=admin_headers,
                          params={"space_id": space_id})
        got = assert_ok(resp)["data"]["config_json"]["fields"]
        assert [f["field_key"] for f in got] == list(reversed(original_keys))
        assert [f["order"] for f in got] == list(range(1, len(got) + 1))

        # 导入模板列顺序跟随模版顺序
        resp = client.get(f"{API}/b04/spaces/{space_id}/template/import-excel", headers=admin_headers,
                          params={"space_id": space_id})
        assert resp.status_code == 200
        assert read_xlsx(resp.content)[0] == [f["field_label"] for f in reversed(fields)]

        # 按新列顺序导入仍可按标签正确解析（覆盖基础+扩展全部列）
        headers = [f["field_label"] for f in reversed(fields)]
        base_labels = [f["field_label"] for f in fields if f["field_source"] == "base"]
        row_vals = _row(项目名称="default", 任务名称="reorder1", 工作流名称="wfRe")
        values = dict(zip(base_labels, row_vals))
        for f in fields:
            if f["field_source"] == "extension":
                values[f["field_label"]] = "P0"
        resp = _import_tasks(client, admin_headers, scenario, headers, [[values[h] for h in headers]])
        assert assert_ok(resp)["data"]["inserted"] == 1
    finally:
        # 恢复默认顺序，避免影响其他用例
        restored = sorted(fields, key=lambda f: original_keys.index(f["field_key"]))
        _save(restored)
