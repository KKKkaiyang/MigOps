"""b05 数据校验管理功能测试：两种模板导入、数据日期落库、校验概览（最新/近7天）、任务数据校验结果刷新。

依据《数据校验-数据校验结果导入与刷新需求》V1.0：
- 导入支持默认模板（库名/表名/源端数据量/目标端数据量/结果）与腾讯数据校验工具模板
  （srcDatabase/srcTable/srcResult/dstResult/checkResult，true=通过）；
- 导入按所选数据日期批量落库，同日期同库表 upsert；
- 导入确认后按血缘输出正式表刷新 b04_task.check_result（多输出表全部通过才为通过）。
"""

from datetime import date, timedelta

from tests.conftest import (
    API,
    CODE_BIZ,
    CODE_FORBIDDEN,
    assert_biz_error,
    assert_ok,
    csv_upload,
    uid,
    xlsx_upload,
)

# 默认模板列
DEF_HEADERS = ["库名", "表名", "源端数据量", "目标端数据量", "结果"]
# 腾讯数据校验工具模板列
TENCENT_HEADERS = ["srcDatabase", "srcTable", "srcResult", "dstResult", "checkResult"]


def _today() -> date:
    """测试执行时取当天（避免跨午夜时模块级常量过期）。"""
    return date.today()


def _yesterday() -> date:
    return _today() - timedelta(days=1)


def _import(client, headers, space_id, headers_row, rows, data_date, template, ext="xlsx"):
    files = (
        xlsx_upload(headers_row, rows)
        if ext == "xlsx"
        else csv_upload(headers_row, rows, filename=f"import.{ext}")
    )
    return client.post(
        f"{API}/b05/checks/import",
        headers=headers,
        params={"space_id": space_id, "data_date": data_date.isoformat(), "template": template},
        files=files,
    )


def _make_b03_items(client, headers, space_id, tables):
    """建 b03 场景并入库表清单，返回 scenario_id。tables: [(db, table), ...]"""
    resp = client.post(
        f"{API}/b03/scenarios", headers=headers, params={"space_id": space_id},
        json={"name": uid("校验场景"), "remark": "数据校验测试"},
    )
    sc_id = assert_ok(resp, 201)["data"]["id"]
    rows = [[db, tbl, "", "", "内部表", 0, 1] for db, tbl in tables]
    resp = client.post(
        f"{API}/b03/scenarios/{sc_id}/table-items/import", headers=headers,
        params={"space_id": space_id}, files=xlsx_upload(
            ["库名", "表名", "目标库名", "目标表名", "表类型", "预估数据量", "分区数"], rows
        ),
    )
    assert_ok(resp)
    return sc_id


def _make_b04_task(client, headers, space_id, project, task, workflow):
    """建 b04 场景并导入单条任务。"""
    resp = client.post(
        f"{API}/b04/scenarios", headers=headers, params={"space_id": space_id},
        json={"name": uid("任务场景"), "remark": "数据校验测试"},
    )
    sc_id = assert_ok(resp, 201)["data"]["id"]
    row = [
        project, task, "张三", "草稿", "未开始", "未调度", "校验通过", "通过",
        workflow, "生产", "", "", "", "无校验结果",
    ]
    resp = client.post(
        f"{API}/b04/scenarios/{sc_id}/tasks/import", headers=headers,
        params={"space_id": space_id, "mode": "overwrite"},
        files=xlsx_upload(
            ["项目名称", "任务名称", "迁移负责人", "任务活跃状态", "迁移状态",
             "双跑调度状态", "数据校验状态", "客户验收状态", "工作流名称", "归属环境",
             "归属业务", "任务类型", "备注信息", "数据校验结果"],
            [row],
        ),
    )
    assert_ok(resp)
    return sc_id


def _make_lineage(client, headers, space_id, project, task, output_tables):
    """按任务导入血缘边（输出表均为正式表），返回工作流名（用于清理）。"""
    workflow = uid("wf_check")
    edges = [
        {"source": "ods.src", "target": t, "source_type": "正式表", "target_type": "正式表"}
        for t in output_tables
    ]
    resp = client.post(
        f"{API}/b07/lineages/import", headers=headers, params={"space_id": space_id},
        json={
            "workflow": workflow, "task": task, "project": project,
            "mode": "add", "edges": edges,
        },
    )
    assert_ok(resp)
    return workflow


def _drop_lineage(client, headers, space_id, workflows):
    """清理测试导入的血缘工作流（避免污染共享测试空间的其他用例）。"""
    for wf in workflows:
        client.delete(f"{API}/b07/lineages/workflows/{wf}", headers=headers,
                      params={"space_id": space_id})


def test_import_default_template_and_overview(client, admin_headers, test_space):
    """默认模板导入 → 按数据日期落库 → 概览展示最新结果与近 7 天序列。"""
    space_id = test_space["id"]
    db, tbl = uid("db"), uid("tbl")
    _make_b03_items(client, admin_headers, space_id, [(db, tbl)])

    # 昨天导入：不通过
    resp = _import(client, admin_headers, space_id, DEF_HEADERS,
                   [[db, tbl, "100", "99", "不通过"]], _yesterday(), "default")
    body = assert_ok(resp)
    assert body["data"]["inserted"] == 1

    # 今天再导入同一库表：通过（同日期 upsert 覆盖）
    resp = _import(client, admin_headers, space_id, DEF_HEADERS,
                   [[db, tbl, "100", "100", "通过"]], _today(), "default")
    assert assert_ok(resp)["data"]["inserted"] == 1

    # 概览：最新=通过（含今天）；近 7 天窗口为 T-7~T-1（不含今天，D8），含昨天(不通过)
    resp = client.get(f"{API}/b05/checks", headers=admin_headers,
                      params={"space_id": space_id, "keyword": tbl})
    body = assert_ok(resp)["data"]
    assert body["total"] >= 1
    row = next(r for r in body["list"] if r["db_name"] == db and r["table_name"] == tbl)
    assert row["latest_result"] == "通过"
    assert row["latest_src_volume"] == 100 and row["latest_dst_volume"] == 100
    recent = row["recent_days"]
    assert len(recent) == 7
    days = {str(d["data_date"]): d for d in recent}
    assert _yesterday().isoformat() in days and days[_yesterday().isoformat()]["result"] == "不通过"
    # 不含今天（D8）：今天与 7 天前之外不在窗口内
    assert _today().isoformat() not in days
    assert (_today() - timedelta(days=7)).isoformat() in days
    assert (_today() - timedelta(days=8)).isoformat() not in days
    # 降序：索引 0 = 昨天（最近在左，D8）
    assert str(recent[0]["data_date"]) == _yesterday().isoformat()
    assert str(recent[6]["data_date"]) == (_today() - timedelta(days=7)).isoformat()

    # 同日再次导入 → updated
    resp = _import(client, admin_headers, space_id, DEF_HEADERS,
                   [[db, tbl, "200", "200", "通过"]], _today(), "default")
    assert assert_ok(resp)["data"]["updated"] == 1

    # 结果过滤：通过
    resp = client.get(f"{API}/b05/checks", headers=admin_headers,
                      params={"space_id": space_id, "keyword": tbl, "result": "通过"})
    assert assert_ok(resp)["data"]["total"] == 1
    # 结果过滤：不通过（无数据）
    resp = client.get(f"{API}/b05/checks", headers=admin_headers,
                      params={"space_id": space_id, "keyword": tbl, "result": "不通过"})
    assert assert_ok(resp)["data"]["total"] == 0


def test_import_tencent_template(client, admin_headers, test_space):
    """腾讯数据校验工具模板导入（csv）：checkResult=true 为通过，否则不通过。"""
    space_id = test_space["id"]
    db = uid("db")
    _make_b03_items(client, admin_headers, space_id, [(db, "t1"), (db, "t2")])

    resp = _import(
        client, admin_headers, space_id, TENCENT_HEADERS,
        [[db, "t1", "10", "10", "true"], [db, "t2", "20", "19", "false"]],
        _today(), "tencent", ext="csv",
    )
    body = assert_ok(resp)
    assert body["data"]["inserted"] == 2

    resp = client.get(f"{API}/b05/checks", headers=admin_headers,
                      params={"space_id": space_id, "keyword": db})
    rows = {r["table_name"]: r for r in assert_ok(resp)["data"]["list"]}
    assert rows["t1"]["latest_result"] == "通过"
    assert rows["t2"]["latest_result"] == "不通过"
    assert rows["t2"]["latest_src_volume"] == 20 and rows["t2"]["latest_dst_volume"] == 19

    # 缺少必要列 → 业务错误
    resp = _import(client, admin_headers, space_id, ["srcTable", "checkResult"],
                   [["t1", "true"]], _today(), "tencent")
    assert_biz_error(resp, CODE_BIZ, "缺少必要列")


def test_import_refreshes_task_check_result(client, admin_headers, test_space):
    """导入后按血缘输出正式表刷新任务数据校验结果：多输出表全部通过才为通过。"""
    space_id = test_space["id"]
    project = uid("proj")
    db = uid("db")
    workflows = []
    try:
        # 任务 single：单输出表；任务 multi：两个输出表
        _make_b04_task(client, admin_headers, space_id, project, "task_single", "wf_single")
        _make_b04_task(client, admin_headers, space_id, project, "task_multi", "wf_multi")
        _make_b03_items(client, admin_headers, space_id,
                        [(db, "single_t"), (db, "multi_a"), (db, "multi_b")])
        workflows.append(_make_lineage(client, admin_headers, space_id, project,
                                       "task_single", [f"{db}.single_t"]))
        workflows.append(_make_lineage(client, admin_headers, space_id, project, "task_multi",
                                       [f"{db}.multi_a", f"{db}.multi_b"]))

        # single 通过、multi 仅一张通过 → single=通过，multi=不通过
        resp = _import(client, admin_headers, space_id, DEF_HEADERS,
                       [[db, "single_t", "1", "1", "通过"],
                        [db, "multi_a", "2", "2", "通过"],
                        [db, "multi_b", "3", "3", "不通过"]], _today(), "default")
        body = assert_ok(resp)
        assert body["data"]["refreshed_tasks"] == 2

        results = _task_check_results(client, admin_headers, space_id, project)
        assert results["task_single"] == "通过"
        assert results["task_multi"] == "不通过"

        # 修复 multi_b 后重新导入 → multi 转为通过
        resp = _import(client, admin_headers, space_id, DEF_HEADERS,
                       [[db, "multi_b", "3", "3", "通过"]], _today(), "default")
        assert_ok(resp)
        results = _task_check_results(client, admin_headers, space_id, project)
        assert results["task_multi"] == "通过"

        # 无血缘输出表的任务不受刷新影响（保持无校验结果）
        _make_b04_task(client, admin_headers, space_id, project, "task_nolineage", "wf_nl")
        _import(client, admin_headers, space_id, DEF_HEADERS,
                [[db, "single_t", "1", "1", "通过"]], _today(), "default")
        results = _task_check_results(client, admin_headers, space_id, project)
        assert results["task_nolineage"] == "无校验结果"
    finally:
        _drop_lineage(client, admin_headers, space_id, workflows)


def test_full_space_refresh_recomputes_all_tasks(client, admin_headers, test_space):
    """B05-04：全空间刷新覆盖增量刷新未触及的任务（任务/血缘在导入之后建立）。"""
    space_id = test_space["id"]
    project = uid("proj")
    db = uid("db")
    workflows = []
    try:
        _make_b04_task(client, admin_headers, space_id, project, "task_single", "wf_single")
        _make_b03_items(client, admin_headers, space_id, [(db, "single_t")])
        workflows.append(_make_lineage(client, admin_headers, space_id, project,
                                       "task_single", [f"{db}.single_t"]))
        # 导入 single_t=通过 → 增量刷新仅覆盖导入时已存在的 task_single
        _import(client, admin_headers, space_id, DEF_HEADERS,
                [[db, "single_t", "1", "1", "通过"]], _today(), "default")
        results = _task_check_results(client, admin_headers, space_id, project)
        assert results["task_single"] == "通过"

        # 导入之后才建立的任务+血缘（输出表同为 single_t）→ 增量刷新未触发
        _make_b04_task(client, admin_headers, space_id, project, "task_late", "wf_late")
        workflows.append(_make_lineage(client, admin_headers, space_id, project,
                                       "task_late", [f"{db}.single_t"]))
        results = _task_check_results(client, admin_headers, space_id, project)
        assert results["task_late"] in (None, "无校验结果")

        # 全空间刷新 → task_late 重新判定为通过（演示覆盖增量刷新盲区）
        resp = client.post(f"{API}/b05/checks/refresh", headers=admin_headers,
                           params={"space_id": space_id})
        body = assert_ok(resp)
        assert body["data"]["refreshed_tasks"] >= 1

        results = _task_check_results(client, admin_headers, space_id, project)
        assert results["task_single"] == "通过"
        assert results["task_late"] == "通过"
    finally:
        _drop_lineage(client, admin_headers, space_id, workflows)


def _task_check_results(client, headers, space_id, project):
    """读取空间内指定项目的任务数据校验结果 {task_name: check_result}。"""
    resp = client.get(f"{API}/b04/scenarios", headers=headers, params={"space_id": space_id})
    out = {}
    for sc in assert_ok(resp)["data"]:
        resp = client.get(f"{API}/b04/scenarios/{sc['id']}/tasks", headers=headers,
                          params={"space_id": space_id, "project_name": project, "page_size": 200})
        for t in assert_ok(resp)["data"]["list"]:
            out[t["task_name"]] = t["check_result"]
    return out


def test_checks_by_tables(client, admin_headers, test_space):
    """GET /b05/checks/by-tables：按表批量取最近 N 天校验结果（供血缘节点□）。"""
    space_id = test_space["id"]
    db, tbl = uid("db"), uid("tbl")
    _make_b03_items(client, admin_headers, space_id, [(db, tbl)])
    _import(client, admin_headers, space_id, DEF_HEADERS,
            [[db, tbl, "1", "1", "通过"]], _yesterday(), "default")

    # 命中表返回 1 条当日校验结果
    resp = client.get(f"{API}/b05/checks/by-tables", headers=admin_headers,
                      params={"space_id": space_id, "tables": f"{db}.{tbl}"})
    body = assert_ok(resp)
    assert f"{db}.{tbl}" in body["data"]["tables"]
    recs = body["data"]["tables"][f"{db}.{tbl}"]
    assert len(recs) == 1
    assert recs[0]["result"] == "通过"
    assert recs[0]["src_volume"] == 1

    # 未命中表返回空列表（而非报错）
    resp = client.get(f"{API}/b05/checks/by-tables", headers=admin_headers,
                      params={"space_id": space_id, "tables": f"{db}.nope"})
    body = assert_ok(resp)
    assert body["data"]["tables"].get(f"{db}.nope") == []


def test_import_validation(client, admin_headers, test_space):
    """非法文件类型 / 非法模板 / 未来日期 / 空文件均被拒绝。"""
    space_id = test_space["id"]
    # 非法文件类型
    resp = client.post(
        f"{API}/b05/checks/import", headers=admin_headers,
        params={"space_id": space_id, "data_date": _today().isoformat(), "template": "default"},
        files={"file": ("bad.txt", b"x", "text/plain")},
    )
    assert_biz_error(resp, CODE_BIZ, "仅支持")
    # 非法模板
    resp = client.post(
        f"{API}/b05/checks/import", headers=admin_headers,
        params={"space_id": space_id, "data_date": _today().isoformat(), "template": "bad"},
        files=xlsx_upload(DEF_HEADERS, [[uid("db"), "t", "1", "1", "通过"]]),
    )
    assert_biz_error(resp, CODE_BIZ, "非法的导入模板")
    # 未来日期
    future = (_today() + timedelta(days=1)).isoformat()
    resp = client.post(
        f"{API}/b05/checks/import", headers=admin_headers,
        params={"space_id": space_id, "data_date": future, "template": "default"},
        files=xlsx_upload(DEF_HEADERS, [[uid("db"), "t", "1", "1", "通过"]]),
    )
    assert_biz_error(resp, CODE_BIZ, "日期")
    # 空文件（仅表头）
    resp = _import(client, admin_headers, space_id, DEF_HEADERS, [], _today(), "default")
    assert_biz_error(resp, CODE_BIZ, "无数据行")
    # 非法校验结果取值 → 行级错误
    resp = _import(client, admin_headers, space_id, DEF_HEADERS,
                   [[uid("db"), "t", "1", "1", "可能通过"]], _today(), "default")
    body = assert_ok(resp)
    assert body["data"]["inserted"] == 0 and len(body["data"]["errors"]) == 1


def test_import_template_download(client, admin_headers, test_space):
    """两种模板均可下载，表头符合各自格式。"""
    space_id = test_space["id"]
    resp = client.get(f"{API}/b05/checks/import-template", headers=admin_headers,
                      params={"space_id": space_id, "template": "default"})
    assert resp.status_code == 200
    from tests.conftest import read_xlsx

    assert read_xlsx(resp.content)[0] == DEF_HEADERS
    resp = client.get(f"{API}/b05/checks/import-template", headers=admin_headers,
                      params={"space_id": space_id, "template": "tencent"})
    assert read_xlsx(resp.content)[0] == TENCENT_HEADERS


def test_list_checks_scenario_filter_and_not_in_list(client, admin_headers, test_space):
    """列表按 b03 场景过滤；清单外库表正常入库并计入 not_in_list（D2/D6）。"""
    space_id = test_space["id"]
    db = uid("db")
    # 两个场景各建一张清单库表
    sc_a = _make_b03_items(client, admin_headers, space_id, [(db, "t1")])
    sc_b = _make_b03_items(client, admin_headers, space_id, [(db, "t2")])

    # 导入：t1（清单内，通过）+ t3（清单外，不通过）
    resp = _import(
        client, admin_headers, space_id, DEF_HEADERS,
        [[db, "t1", "1", "1", "通过"], [db, "t3", "2", "2", "不通过"]],
        _today(), "default", ext="csv",
    )
    body = assert_ok(resp)
    assert body["data"]["inserted"] == 2
    assert body["data"]["not_in_list"] == 1

    # 按场景 A 过滤：仅见 t1，且最新结果为通过
    resp = client.get(f"{API}/b05/checks", headers=admin_headers,
                      params={"space_id": space_id, "scenario_id": sc_a})
    rows = assert_ok(resp)["data"]["list"]
    assert [r["table_name"] for r in rows] == ["t1"]
    assert rows[0]["latest_result"] == "通过"

    # 按场景 B 过滤：仅见 t2，无校验记录
    resp = client.get(f"{API}/b05/checks", headers=admin_headers,
                      params={"space_id": space_id, "scenario_id": sc_b})
    rows = assert_ok(resp)["data"]["list"]
    assert [r["table_name"] for r in rows] == ["t2"]
    assert rows[0]["latest_result"] is None

    # 空间级（不传场景）：仅展示清单内库表，不含清单外的 t3
    resp = client.get(f"{API}/b05/checks", headers=admin_headers,
                      params={"space_id": space_id, "keyword": db})
    names = {r["table_name"] for r in assert_ok(resp)["data"]["list"]}
    assert names == {"t1", "t2"}


def test_import_row_limit_50000(client, admin_headers, test_space):
    """数据校验结果导入单文件上限 50000 行（b05 专用；超过即拒绝，且不写库）。"""
    space_id = test_space["id"]
    db = uid("db")
    # 50001 行 → 拒绝（校验发生在入库前）
    rows = [[db, f"t{i}", "1", "1", "通过"] for i in range(50001)]
    resp = _import(client, admin_headers, space_id, DEF_HEADERS, rows, _today(), "default")
    assert_biz_error(resp, CODE_BIZ, "50000")
    # 拒绝后库中无任何写入
    resp = client.get(f"{API}/b05/checks", headers=admin_headers,
                      params={"space_id": space_id, "keyword": db})
    assert assert_ok(resp)["data"]["total"] == 0


def test_member_read_and_outsider_forbidden(client, admin_headers, member_headers, outsider_headers, test_space):
    """空间成员可读；非成员越权访问被拒绝。"""
    space_id = test_space["id"]
    resp = client.get(f"{API}/b05/checks", headers=member_headers, params={"space_id": space_id})
    assert_ok(resp)
    resp = client.get(f"{API}/b05/checks", headers=outsider_headers, params={"space_id": space_id})
    assert_biz_error(resp, CODE_FORBIDDEN, "无权访问")
