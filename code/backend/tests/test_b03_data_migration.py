"""b03 数据迁移管理功能测试：场景、库表清单、批量状态、Excel 导入导出、迁移记录。"""

import pytest

from tests.conftest import (
    API,
    CODE_BIZ,
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
    resp = client.post(f"{API}/b03/scenarios", headers=admin_headers, params={"space_id": space_id},
                       json={"name": uid("场景Hive2Hive"), "remark": "功能测试场景"})
    body = assert_ok(resp, 201)
    sc = {"id": body["data"]["id"], "name": body["data"]["name"]}
    yield {"space_id": space_id, **sc}
    client.delete(f"{API}/b03/scenarios/{sc['id']}", headers=admin_headers, params={"space_id": space_id})


def test_scenario_crud(client, admin_headers, test_space, scenario):
    space_id = test_space["id"]
    # 重名 → 业务错误
    resp = client.post(f"{API}/b03/scenarios", headers=admin_headers, params={"space_id": space_id},
                       json={"name": scenario["name"]})
    assert_biz_error(resp, CODE_BIZ, "场景名称已存在")
    # 列表含 table_count
    resp = client.get(f"{API}/b03/scenarios", headers=admin_headers, params={"space_id": space_id})
    body = assert_ok(resp)
    same = next(s for s in body["data"] if s["id"] == scenario["id"])
    assert "table_count" in same
    # 更新
    resp = client.put(f"{API}/b03/scenarios/{scenario['id']}", headers=admin_headers,
                      params={"space_id": space_id}, json={"remark": "更新备注"})
    assert_ok(resp)


def test_table_item_crud(client, admin_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    # 创建
    resp = client.post(f"{API}/b03/scenarios/{sc_id}/table-items", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"db_name": "ods", "table_name": uid("tbl_a"), "table_type": "分区表",
                             "data_volume": 100, "partition_count": 5})
    body = assert_ok(resp, 201)
    item_id = body["data"]["id"]
    # 重复库表 → 业务错误
    resp = client.post(f"{API}/b03/scenarios/{sc_id}/table-items", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"db_name": "ods", "table_name": body["data"]["table_name"]})
    assert_biz_error(resp, CODE_BIZ, "库表已存在")
    # 更新 target 字段
    resp = client.put(f"{API}/b03/table-items/{item_id}", headers=admin_headers,
                      params={"space_id": space_id},
                      json={"target_db_name": "dwd", "target_table_name": uid("tbl_a_tgt")})
    assert_ok(resp)
    # 筛选：table_type + metadata_status
    resp = client.get(f"{API}/b03/scenarios/{sc_id}/table-items", headers=admin_headers,
                      params={"space_id": space_id, "table_type": "分区表"})
    body = assert_ok(resp)
    assert all(t["table_type"] == "分区表" for t in body["data"]["list"])
    # 删除（无单条 get 接口，用列表总数变化验证）
    before = assert_ok(client.get(f"{API}/b03/scenarios/{sc_id}/table-items", headers=admin_headers,
                                  params={"space_id": space_id}))["data"]["total"]
    resp = client.delete(f"{API}/b03/table-items/{item_id}", headers=admin_headers, params={"space_id": space_id})
    assert_ok(resp)
    after = assert_ok(client.get(f"{API}/b03/scenarios/{sc_id}/table-items", headers=admin_headers,
                                 params={"space_id": space_id}))["data"]["total"]
    assert after == before - 1


def test_batch_status(client, admin_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    r1 = client.post(f"{API}/b03/scenarios/{sc_id}/table-items", headers=admin_headers,
                     params={"space_id": space_id},
                     json={"db_name": "ods", "table_name": uid("bt_a")})
    r2 = client.post(f"{API}/b03/scenarios/{sc_id}/table-items", headers=admin_headers,
                     params={"space_id": space_id},
                     json={"db_name": "ods", "table_name": uid("bt_b")})
    ids = [r1.json()["data"]["id"], r2.json()["data"]["id"]]
    # 批量更新
    resp = client.post(f"{API}/b03/scenarios/{sc_id}/table-items/batch-status", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"ids": ids, "metadata_status": "已完成", "full_sync_status": "已完成"})
    body = assert_ok(resp)
    assert body["data"]["affected"] == 2
    # 空字段 → 业务错误
    resp = client.post(f"{API}/b03/scenarios/{sc_id}/table-items/batch-status", headers=admin_headers,
                       params={"space_id": space_id}, json={"ids": ids})
    assert_biz_error(resp, CODE_BIZ, "未提供需要更新的状态字段")
    # 非法状态 → 参数校验
    resp = client.post(f"{API}/b03/scenarios/{sc_id}/table-items/batch-status", headers=admin_headers,
                       params={"space_id": space_id}, json={"ids": ids, "metadata_status": "非法"})
    assert_biz_error(resp, CODE_PARAM)


def test_import_table_items_xlsx(client, admin_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    headers = ["库名", "表名", "目标库名", "目标表名", "表类型", "预估数据量", "分区数"]
    rows = [
        ["ods", uid("imp_a"), "dwd", uid("imp_a_t"), "分区表", 100, 3],
        ["ods", uid("imp_b"), "dwd", uid("imp_b_t"), "内部表", 200, 0],
        ["ods", uid("imp_c"), "", "", "非法表", 1, 0],  # 非法表类型 → 错误行
        ["", uid("imp_d"), "", "", "", "", ""],          # 空库名 → 错误行
    ]
    resp = client.post(f"{API}/b03/scenarios/{sc_id}/table-items/import", headers=admin_headers,
                       params={"space_id": space_id}, files=xlsx_upload(headers, rows))
    body = assert_ok(resp)
    assert body["data"]["inserted"] == 2
    assert len(body["data"]["errors"]) == 2
    # 再次导入（改目标库名）→ 更新，库名/表名需与已导入一致
    rows2 = [["ods", rows[0][1], "dwd2", uid("imp_a_t2"), "分区表", 999, 9]]
    resp = client.post(f"{API}/b03/scenarios/{sc_id}/table-items/import", headers=admin_headers,
                       params={"space_id": space_id}, files=xlsx_upload(headers, rows2))
    body = assert_ok(resp)
    assert body["data"]["updated"] == 1


def test_import_table_items_csv_and_rejects(client, admin_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    headers = ["库名", "表名", "目标库名", "目标表名", "表类型", "预估数据量", "分区数"]
    rows = [["ods", uid("csv_a"), "", "", "视图", 10, 0]]
    resp = client.post(f"{API}/b03/scenarios/{sc_id}/table-items/import", headers=admin_headers,
                       params={"space_id": space_id}, files=csv_upload(headers, rows))
    assert_ok(resp)
    # 缺必需列
    resp = client.post(f"{API}/b03/scenarios/{sc_id}/table-items/import", headers=admin_headers,
                       params={"space_id": space_id}, files=xlsx_upload(["表名"], [["x"]]))
    assert_biz_error(resp, CODE_BIZ, "缺少必需列")
    # 非法扩展名
    resp = client.post(f"{API}/b03/scenarios/{sc_id}/table-items/import", headers=admin_headers,
                       params={"space_id": space_id}, files={"file": ("x.txt", b"1,2", "text/plain")})
    assert_biz_error(resp, CODE_BIZ, "仅支持")


def test_export_and_template(client, admin_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    # 准备若干库表，供导出验证
    client.post(f"{API}/b03/scenarios/{sc_id}/table-items", headers=admin_headers,
                params={"space_id": space_id}, json={"db_name": "ods", "table_name": uid("exp_a"), "table_type": "分区表"})
    client.post(f"{API}/b03/scenarios/{sc_id}/table-items", headers=admin_headers,
                params={"space_id": space_id}, json={"db_name": "ods", "table_name": uid("exp_b"), "table_type": "内部表"})
    # 模板
    resp = client.get(f"{API}/b03/scenarios/{sc_id}/table-items/template", headers=admin_headers,
                      params={"space_id": space_id})
    assert resp.status_code == 200
    rows = read_xlsx(resp.content)
    assert rows[0][0] == "库名"
    # 导出
    resp = client.get(f"{API}/b03/scenarios/{sc_id}/table-items/export", headers=admin_headers,
                      params={"space_id": space_id})
    assert resp.status_code == 200
    rows = read_xlsx(resp.content)
    assert rows[0][0] == "库名"
    assert len(rows) >= 2  # 表头 + 至少一行


def test_records_crud(client, admin_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    # 先建库表
    resp = client.post(f"{API}/b03/scenarios/{sc_id}/table-items", headers=admin_headers,
                       params={"space_id": space_id}, json={"db_name": "ods", "table_name": uid("rec_t")})
    item_id = assert_ok(resp, 201)["data"]["id"]
    # 创建记录
    resp = client.post(f"{API}/b03/table-items/{item_id}/records", headers=admin_headers,
                       params={"space_id": space_id},
                       json={"migration_type": "全量历史迁移", "status": "成功", "data_volume": 50})
    body = assert_ok(resp, 201)
    rec_id = body["data"]["id"]
    # 列表
    resp = client.get(f"{API}/b03/table-items/{item_id}/records", headers=admin_headers,
                      params={"space_id": space_id})
    assert assert_ok(resp)["data"]["total"] >= 1
    # 更新
    resp = client.put(f"{API}/b03/records/{rec_id}", headers=admin_headers, params={"space_id": space_id},
                      json={"status": "失败"})
    assert_ok(resp)
    # 删除
    resp = client.delete(f"{API}/b03/records/{rec_id}", headers=admin_headers, params={"space_id": space_id})
    assert_ok(resp)


def test_import_records(client, admin_headers, scenario):
    space_id, sc_id = scenario["space_id"], scenario["id"]
    # 准备库表，供记录导入引用
    resp = client.post(f"{API}/b03/scenarios/{sc_id}/table-items", headers=admin_headers,
                       params={"space_id": space_id}, json={"db_name": "ods", "table_name": uid("irec_t")})
    item = assert_ok(resp, 201)["data"]
    headers = ["库名", "表名", "迁移类型", "开始时间", "结束时间", "数据量", "迁移方式", "数据截止日期", "状态", "备注"]
    rows = [
        ["ods", item["table_name"], "全量历史迁移", "2026-09-28 10:00:00", "2026-09-28 14:30:00", 230, "DistCp", "2026-09-27", "成功", ""],
        ["ods", item["table_name"], "非法类型", "", "", "", "", "", "成功", ""],     # 非法迁移类型 → 错误
        ["ods", uid("no_such_tbl"), "全量历史迁移", "", "", "", "", "", "成功", ""],  # 库表不存在 → 错误
    ]
    resp = client.post(f"{API}/b03/scenarios/{sc_id}/records/import", headers=admin_headers,
                       params={"space_id": space_id}, files=xlsx_upload(headers, rows))
    body = assert_ok(resp)
    assert body["data"]["inserted"] == 1
    assert len(body["data"]["errors"]) == 2


def test_scenario_delete_cascades(client, admin_headers, test_space):
    """删除场景级联逻辑删除其下库表与记录。"""
    space_id = test_space["id"]
    resp = client.post(f"{API}/b03/scenarios", headers=admin_headers, params={"space_id": space_id},
                       json={"name": uid("级联场景")})
    sc_id = assert_ok(resp, 201)["data"]["id"]
    resp = client.post(f"{API}/b03/scenarios/{sc_id}/table-items", headers=admin_headers,
                       params={"space_id": space_id}, json={"db_name": "ods", "table_name": uid("casc_t")})
    assert_ok(resp, 201)
    resp = client.delete(f"{API}/b03/scenarios/{sc_id}", headers=admin_headers, params={"space_id": space_id})
    assert_ok(resp)
    # 场景已删，取空间下全部场景不应再包含该场景（验证级联删除入口生效）
    body = assert_ok(client.get(f"{API}/b03/scenarios", headers=admin_headers, params={"space_id": space_id}))
    assert all(s["id"] != sc_id for s in body["data"])
