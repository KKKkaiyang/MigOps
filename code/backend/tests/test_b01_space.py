"""b01 项目空间管理功能测试：空间 CRUD、状态机、成员管理、权限边界。"""

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from tests.conftest import (
    API,
    CODE_BIZ,
    CODE_FORBIDDEN,
    CODE_NOT_FOUND,
    CODE_PARAM,
    CODE_UNAUTHORIZED,
    assert_biz_error,
    assert_ok,
    uid,
)


def test_create_space_defaults(client, admin_headers, test_space):
    """创建空间：初始状态=初始化，L0 创建人角色恒为 L0，空间库已绑定。"""
    assert test_space["status"] == "初始化"
    assert test_space["overall_progress"] == 10
    assert test_space["my_role"] == "L0"
    assert test_space["member_count"] >= 1
    assert test_space["db_name"].startswith("mig_functest")


def test_creator_becomes_l1(client, l1_headers, admin_headers):
    """L1 项目管理员创建空间后，自动成为该空间的 L1 项目管理员。"""
    code = uid("functest_creator")
    resp = client.post(
        f"{API}/b01/spaces", headers=l1_headers,
        json={"space_code": code, "space_name": uid("成员创建空间")},
    )
    body = assert_ok(resp, 201)
    new_space = body["data"]
    try:
        assert new_space["my_role"] == "L1"
        assert new_space["member_count"] == 1
    finally:
        from app.database import SessionLocal, _server_engine
        from app.models.role import CommonUserRole
        from app.models.space import MigSpace
        from sqlalchemy import text

        db = SessionLocal()
        try:
            db.query(CommonUserRole).filter(CommonUserRole.space_id == new_space["id"]).delete()
            db.query(MigSpace).filter(MigSpace.id == new_space["id"]).delete()
            db.commit()
        finally:
            db.close()
        eng = _server_engine()
        try:
            with eng.connect() as conn:
                conn.execute(text(f"DROP DATABASE IF EXISTS `{new_space['db_name']}`"))
        finally:
            eng.dispose()


def test_l2_cannot_create_space(client, member_headers):
    """L2 项目成员无权创建空间（BRD §4.4：创建仅 L0/L1）。"""
    resp = client.post(
        f"{API}/b01/spaces", headers=member_headers,
        json={"space_code": uid("functest_l2create"), "space_name": uid("L2越权创建")},
    )
    assert_biz_error(resp, CODE_FORBIDDEN, "创建空间")


def test_space_db_and_preset_categories_initialized(test_space):
    """空间库已建表并种子预置资料分类。"""
    from app.database import get_space_engine
    from app.models.b02_material import B02Category

    engine = get_space_engine(test_space["db_name"])
    with engine.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT TABLE_NAME FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = :db"
                ),
                {"db": test_space["db_name"]},
            )
        }
    assert {"b02_category", "b02_material", "b03_scenario", "b04_task"} <= tables

    session_cls = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_cls() as sdb:
        names = {
            c.name
            for c in sdb.query(B02Category).filter(B02Category.space_id == test_space["id"]).all()
        }
    assert {"项目管理类", "调研资料类", "代码与迁移类"} <= names


def test_create_space_duplicate_code(client, admin_headers, test_space):
    resp = client.post(
        f"{API}/b01/spaces",
        headers=admin_headers,
        json={"space_code": test_space["space_code"], "space_name": uid("重复简称空间")},
    )
    assert_biz_error(resp, CODE_BIZ, "项目简称已存在")


def test_create_space_duplicate_name(client, admin_headers, test_space):
    resp = client.post(
        f"{API}/b01/spaces",
        headers=admin_headers,
        json={"space_code": uid("functest_dup"), "space_name": test_space["space_name"]},
    )
    assert_biz_error(resp, CODE_BIZ, "项目名称已存在")


def test_create_space_invalid_code(client, admin_headers):
    # 仅包含无法通过字段校验（正则/长度）的非法简称，避免误建空间。
    # 注意：后端会对 space_code 做 strip().lower()，故 "Abc" 会归一为 "abc"
    # （合法格式），不参与此处格式校验断言。
    for bad in ("1abc", "a", "a-1", "中文项目"):
        resp = client.post(
            f"{API}/b01/spaces",
            headers=admin_headers,
            json={"space_code": bad, "space_name": uid("非法简称空间")},
        )
        assert_biz_error(resp, CODE_PARAM)


def test_create_space_progress_out_of_range(client, admin_headers):
    resp = client.post(
        f"{API}/b01/spaces",
        headers=admin_headers,
        json={
            "space_code": uid("functest_prog"),
            "space_name": uid("越界进展空间"),
            "overall_progress": 101,
        },
    )
    assert_biz_error(resp, CODE_PARAM)


def test_list_spaces_keyword_and_pagination(client, admin_headers, test_space):
    resp = client.get(
        f"{API}/b01/spaces",
        headers=admin_headers,
        params={"keyword": test_space["space_code"], "page": 1, "page_size": 5},
    )
    body = assert_ok(resp)
    data = body["data"]
    assert data["total"] >= 1
    assert any(s["id"] == test_space["id"] for s in data["list"])

    # 状态筛选：返回值必须全部匹配该状态
    resp = client.get(f"{API}/b01/spaces", headers=admin_headers, params={"status": "初始化"})
    body = assert_ok(resp)
    assert all(s["status"] == "初始化" for s in body["data"]["list"])

    # 分页结构
    resp = client.get(f"{API}/b01/spaces", headers=admin_headers, params={"page": 1, "page_size": 1})
    body = assert_ok(resp)
    assert len(body["data"]["list"]) == 1
    assert body["data"]["page"] == 1 and body["data"]["page_size"] == 1


def test_get_space_permission(client, admin_headers, member_headers, outsider_headers, test_space):
    # L0 可见，角色恒 L0
    body = assert_ok(client.get(f"{API}/b01/spaces/{test_space['id']}", headers=admin_headers))
    assert body["data"]["my_role"] == "L0"
    # L2 成员可见，角色 L2
    body = assert_ok(client.get(f"{API}/b01/spaces/{test_space['id']}", headers=member_headers))
    assert body["data"]["my_role"] == "L2"
    # 非成员越权 → 403
    resp = client.get(f"{API}/b01/spaces/{test_space['id']}", headers=outsider_headers)
    assert_biz_error(resp, CODE_FORBIDDEN, "无权访问")
    # 未登录 → 401
    resp = client.get(f"{API}/b01/spaces/{test_space['id']}")
    assert_biz_error(resp, CODE_UNAUTHORIZED)


def test_update_space_permission(client, admin_headers, member_headers, test_space):
    # L2 成员不能修改空间信息（仅 L0/L1）
    resp = client.put(
        f"{API}/b01/spaces/{test_space['id']}",
        headers=member_headers,
        json={"remark": "成员试图修改"},
    )
    assert_biz_error(resp, CODE_FORBIDDEN)
    # L0 可修改
    resp = client.put(
        f"{API}/b01/spaces/{test_space['id']}",
        headers=admin_headers,
        json={"overall_progress": 55, "remark": "功能测试更新"},
    )
    body = assert_ok(resp)
    assert body["data"]["overall_progress"] == 55
    assert body["data"]["remark"] == "功能测试更新"


def test_space_status_machine(client, admin_headers, member_headers, test_space):
    space_id = test_space["id"]
    # 初始化 → 交付中 → 已验收
    resp = client.post(f"{API}/b01/spaces/{space_id}/status", headers=admin_headers, json={"status": "交付中"})
    assert_ok(resp)
    resp = client.post(f"{API}/b01/spaces/{space_id}/status", headers=admin_headers, json={"status": "已验收"})
    assert_ok(resp)
    # 已验收为终态，不能回退
    resp = client.post(f"{API}/b01/spaces/{space_id}/status", headers=admin_headers, json={"status": "初始化"})
    assert_biz_error(resp, CODE_BIZ, "不能从")
    # 非法状态值
    resp = client.post(f"{API}/b01/spaces/{space_id}/status", headers=admin_headers, json={"status": "不存在态"})
    assert_biz_error(resp, CODE_BIZ, "非法的空间状态")
    # L2 成员不能改状态
    resp = client.post(f"{API}/b01/spaces/{space_id}/status", headers=member_headers, json={"status": "交付中"})
    assert_biz_error(resp, CODE_FORBIDDEN)


def test_member_management(client, admin_headers, test_space, throwaway_user):
    space_id = test_space["id"]
    user = throwaway_user("functest_membermgmt")
    user_id = user["user_id"]

    # 添加 L2 成员
    resp = client.post(
        f"{API}/b01/spaces/{space_id}/members",
        headers=admin_headers,
        json={"user_id": user_id, "role_level": "L2"},
    )
    assert_ok(resp, 201)
    # 重复添加 → 业务错误
    resp = client.post(
        f"{API}/b01/spaces/{space_id}/members",
        headers=admin_headers,
        json={"user_id": user_id, "role_level": "L2"},
    )
    assert_biz_error(resp, CODE_BIZ, "已是空间成员")
    # 添加不存在的用户 → 404
    resp = client.post(
        f"{API}/b01/spaces/{space_id}/members",
        headers=admin_headers,
        json={"user_id": 999999999, "role_level": "L2"},
    )
    assert_biz_error(resp, CODE_NOT_FOUND)
    # 角色变更：L2 → L1 → L2
    resp = client.put(
        f"{API}/b01/spaces/{space_id}/members/{user_id}",
        headers=admin_headers,
        json={"role_level": "L1"},
    )
    assert assert_ok(resp)["data"]["role_level"] == "L1"
    resp = client.put(
        f"{API}/b01/spaces/{space_id}/members/{user_id}",
        headers=admin_headers,
        json={"role_level": "L2"},
    )
    assert_ok(resp)
    # 移除 → 再移除报 404
    resp = client.delete(f"{API}/b01/spaces/{space_id}/members/{user_id}", headers=admin_headers)
    assert_ok(resp)
    resp = client.delete(f"{API}/b01/spaces/{space_id}/members/{user_id}", headers=admin_headers)
    assert_biz_error(resp, CODE_NOT_FOUND, "不是空间成员")


def test_l0_physical_delete_space(client, admin_headers, member_headers):
    """L0 物理删除空间：空间库被 DROP，公共库元数据逻辑保留并写审计；L2 被拒。"""
    from app.database import SessionLocal, _server_engine
    from app.models.role import CommonUserRole
    from app.models.space import MigSpace, SpaceDeleteLog

    code = uid("functest_del")
    resp = client.post(
        f"{API}/b01/spaces", headers=admin_headers,
        json={"space_code": code, "space_name": uid("待删空间")},
    )
    space = assert_ok(resp, 201)["data"]
    db_name = space["db_name"]

    def _db_exists(name: str) -> bool:
        eng = _server_engine()
        try:
            with eng.connect() as conn:
                return conn.execute(
                    text("SELECT 1 FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = :n"),
                    {"n": name},
                ).scalar() is not None
        finally:
            eng.dispose()

    assert _db_exists(db_name), "删除前空间库应存在"

    # L2 无权删除
    resp = client.delete(f"{API}/b01/spaces/{space['id']}", headers=member_headers)
    assert_biz_error(resp, CODE_FORBIDDEN)

    # L0 删除
    resp = client.delete(f"{API}/b01/spaces/{space['id']}", headers=admin_headers)
    assert_ok(resp)
    assert resp.json()["message"] == "空间已删除"

    assert not _db_exists(db_name), "删除后空间库应已被 DROP"

    # 元数据逻辑保留 + 审计留存
    db = SessionLocal()
    try:
        rec = db.query(MigSpace).filter(MigSpace.id == space["id"]).first()
        assert rec is not None and rec.deleted_at is not None and rec.status == "已删除"
        log = db.query(SpaceDeleteLog).filter(SpaceDeleteLog.space_id == space["id"]).first()
        assert log is not None and log.db_name == db_name
        # 清理：审计、成员角色、空间主记录
        db.query(SpaceDeleteLog).filter(SpaceDeleteLog.space_id == space["id"]).delete()
        db.query(CommonUserRole).filter(CommonUserRole.space_id == space["id"]).delete()
        db.query(MigSpace).filter(MigSpace.id == space["id"]).delete()
        db.commit()
    finally:
        db.close()
