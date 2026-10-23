"""b07 血缘管理功能测试：脚本解析、导入新增、重建、列表、工作流选项、删除。"""

from tests.conftest import API, assert_biz_error, assert_ok


SQL_SAMPLE = """
INSERT INTO TABLE dwd.user_profile
SELECT * FROM ods.user_raw JOIN ods.user_ext ON ods.user_raw.id = ods.user_ext.uid
"""

PYSPARK_SAMPLE = """
df = spark.sql("INSERT INTO TABLE dwd.order_agg SELECT * FROM ods.order_raw")
df.write.saveAsTable("dwd.order_agg")
"""


def _import(client, headers, space_id, workflow, **payload):
    return client.post(
        f"{API}/b07/lineages/import",
        headers=headers,
        params={"space_id": space_id},
        json={"workflow": workflow, **payload},
    )


def test_parse_script(client, admin_headers, test_space):
    space_id = test_space["id"]
    # SQL 解析
    resp = client.post(
        f"{API}/b07/lineages/parse", headers=admin_headers,
        params={"space_id": space_id}, json={"code": SQL_SAMPLE, "lang": "sql"},
    )
    edges = assert_ok(resp)["data"]
    sources = {e["source"] for e in edges}
    targets = {e["target"] for e in edges}
    assert "ods.user_raw" in sources and "ods.user_ext" in sources
    assert "dwd.user_profile" in targets
    # 空脚本返回空
    resp = client.post(
        f"{API}/b07/lineages/parse", headers=admin_headers,
        params={"space_id": space_id}, json={"code": "   "},
    )
    assert assert_ok(resp)["data"] == []

    # PySpark 解析（自动识别）
    resp = client.post(
        f"{API}/b07/lineages/parse", headers=admin_headers,
        params={"space_id": space_id}, json={"code": PYSPARK_SAMPLE},
    )
    edges = assert_ok(resp)["data"]
    assert any(e["target"] == "dwd.order_agg" for e in edges)


def test_import_add_and_rebuild(client, admin_headers, test_space):
    space_id = test_space["id"]
    # add：脚本解析入库
    resp = _import(client, admin_headers, space_id, "wf_hr", code=SQL_SAMPLE, lang="sql")
    body = assert_ok(resp)
    assert body["data"]["inserted"] == 2 and body["data"]["mode"] == "add"

    resp = client.get(f"{API}/b07/lineages", headers=admin_headers, params={"space_id": space_id})
    assert assert_ok(resp)["data"].__len__() == 2

    # add：再补充一条边 → 总数 3
    resp = _import(
        client, admin_headers, space_id, "wf_hr",
        edges=[{"source": "ods.extra", "target": "dwd.user_profile", "source_type": "正式表", "target_type": "正式表"}],
    )
    assert_ok(resp)
    resp = client.get(f"{API}/b07/lineages", headers=admin_headers, params={"space_id": space_id})
    assert assert_ok(resp)["data"].__len__() == 3

    # rebuild：覆盖为 1 条 → 旧 3 条逻辑删除，剩 1 条
    resp = _import(
        client, admin_headers, space_id, "wf_hr", mode="rebuild",
        edges=[{"source": "ods.new_src", "target": "dwd.new_tgt"}],
    )
    assert assert_ok(resp)["data"]["mode"] == "rebuild"
    resp = client.get(f"{API}/b07/lineages", headers=admin_headers, params={"space_id": space_id})
    rows = assert_ok(resp)["data"]
    assert len(rows) == 1
    assert rows[0]["input_table"] == "ods.new_src"

    # 重建后该工作流仍可被选项接口识别
    resp = client.get(
        f"{API}/b07/lineages/workflows/{ 'wf_hr' }/options", headers=admin_headers,
        params={"space_id": space_id},
    )
    assert assert_ok(resp)["data"]["workflow"] == "wf_hr"


def test_list_filters_and_workflows(client, admin_headers, test_space):
    space_id = test_space["id"]
    _import(client, admin_headers, space_id, "wf_filter", code=SQL_SAMPLE, lang="sql")
    # 按表名关键字筛选
    resp = client.get(
        f"{API}/b07/lineages", headers=admin_headers,
        params={"space_id": space_id, "keyword": "user_raw"},
    )
    rows = assert_ok(resp)["data"]
    assert all("user_raw" in (r["input_table"] + r["output_table"]) for r in rows)
    # 工作流聚合
    resp = client.get(f"{API}/b07/lineages/workflows", headers=admin_headers, params={"space_id": space_id})
    names = {w["name"] for w in assert_ok(resp)["data"]}
    assert "wf_filter" in names


def test_delete_lineage(client, admin_headers, test_space):
    space_id = test_space["id"]
    _import(client, admin_headers, space_id, "wf_del", code=SQL_SAMPLE, lang="sql")
    resp = client.get(f"{API}/b07/lineages", headers=admin_headers, params={"space_id": space_id})
    rows = assert_ok(resp)["data"]
    first_id = rows[0]["id"]
    resp = client.delete(
        f"{API}/b07/lineages/{first_id}", headers=admin_headers, params={"space_id": space_id}
    )
    assert_ok(resp)
    resp = client.get(f"{API}/b07/lineages", headers=admin_headers, params={"space_id": space_id})
    assert all(r["id"] != first_id for r in assert_ok(resp)["data"])
