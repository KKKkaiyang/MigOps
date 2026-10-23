"""b02 项目资料管理功能测试：分类、三类资料 CRUD、筛选、Markdown 查看密码流程、越权边界。"""

from tests.conftest import (
    API,
    CODE_BIZ,
    CODE_FORBIDDEN,
    CODE_NOT_FOUND,
    CODE_PARAM,
    VIEW_PASSWORD,
    assert_biz_error,
    assert_ok,
    uid,
)


def test_preset_categories_present(client, admin_headers, test_space):
    resp = client.get(f"{API}/b02/categories", headers=admin_headers, params={"space_id": test_space["id"]})
    body = assert_ok(resp)
    names = {c["name"]: c for c in body["data"]}
    for preset in ("项目管理类", "调研资料类", "代码与迁移类"):
        assert preset in names, "预置分类缺失"
        assert names[preset]["is_preset"] == 1
        assert names[preset]["material_count"] == 0


def test_category_crud(client, admin_headers, test_space):
    space_id = test_space["id"]
    # 创建自定义分类
    resp = client.post(
        f"{API}/b02/categories", headers=admin_headers,
        params={"space_id": space_id}, json={"name": uid("自定义分类"), "sort_no": 10},
    )
    body = assert_ok(resp, 201)
    cat_id = body["data"]["id"]
    # 重名 → 业务错误
    resp = client.post(
        f"{API}/b02/categories", headers=admin_headers,
        params={"space_id": space_id}, json={"name": body["data"]["name"]},
    )
    assert_biz_error(resp, CODE_BIZ, "分类名称已存在")
    # 更新
    resp = client.put(
        f"{API}/b02/categories/{cat_id}", headers=admin_headers,
        params={"space_id": space_id}, json={"name": uid("重命名分类"), "sort_no": 20},
    )
    assert_ok(resp)
    # 预置分类不可删除
    resp = client.get(f"{API}/b02/categories", headers=admin_headers, params={"space_id": space_id})
    preset_cat = next(c for c in resp.json()["data"] if c["is_preset"] == 1)
    resp = client.delete(f"{API}/b02/categories/{preset_cat['id']}", headers=admin_headers, params={"space_id": space_id})
    assert_biz_error(resp, CODE_BIZ, "预置分类不可删除")
    # 删除自定义分类
    resp = client.delete(f"{API}/b02/categories/{cat_id}", headers=admin_headers, params={"space_id": space_id})
    assert_ok(resp)


def test_create_material_type_validation(client, admin_headers, test_space):
    space_id = test_space["id"]
    base = {"name": uid("类型校验资料")}
    # 外部链接缺 url
    resp = client.post(f"{API}/b02/materials", headers=admin_headers, params={"space_id": space_id},
                       json={**base, "type": "external_link"})
    assert_biz_error(resp, CODE_BIZ, "外部链接类型必须填写链接地址")
    # markdown 缺 content
    resp = client.post(f"{API}/b02/materials", headers=admin_headers, params={"space_id": space_id},
                       json={**base, "type": "markdown"})
    assert_biz_error(resp, CODE_BIZ, "Markdown 类型必须填写资料内容")
    # 平台台账缺 target_module
    resp = client.post(f"{API}/b02/materials", headers=admin_headers, params={"space_id": space_id},
                       json={**base, "type": "platform_ledger"})
    assert_biz_error(resp, CODE_BIZ, "平台台账类型必须选择跳转目标")
    # 非法类型 → 参数校验
    resp = client.post(f"{API}/b02/materials", headers=admin_headers, params={"space_id": space_id},
                       json={**base, "type": "unknown"})
    assert_biz_error(resp, CODE_PARAM)
    # 非法 target_module → 参数校验
    resp = client.post(f"{API}/b02/materials", headers=admin_headers, params={"space_id": space_id},
                       json={**base, "type": "platform_ledger", "target_module": "zzz"})
    assert_biz_error(resp, CODE_PARAM)


def test_material_crud_and_list_hides_content(client, admin_headers, test_space):
    space_id = test_space["id"]
    # 创建 markdown（无密码）
    resp = client.post(
        f"{API}/b02/materials", headers=admin_headers, params={"space_id": space_id},
        json={"name": uid("无密码MD"), "type": "markdown", "content": "# 正文内容"},
    )
    body = assert_ok(resp, 201)
    mat_id = body["data"]["id"]
    # 列表不返回 content
    resp = client.get(f"{API}/b02/materials", headers=admin_headers, params={"space_id": space_id})
    row = next(m for m in assert_ok(resp)["data"]["list"] if m["id"] == mat_id)
    assert row["content"] is None
    assert row["has_password"] is False
    # 详情返回 content
    resp = client.get(f"{API}/b02/materials/{mat_id}", headers=admin_headers, params={"space_id": space_id})
    body = assert_ok(resp)
    assert body["data"]["content"] == "# 正文内容"
    # 更新
    resp = client.put(
        f"{API}/b02/materials/{mat_id}", headers=admin_headers, params={"space_id": space_id},
        json={"name": uid("无密码MD改"), "content": "## 新内容"},
    )
    body = assert_ok(resp)
    assert body["data"]["name"] != row["name"]
    # 删除
    resp = client.delete(f"{API}/b02/materials/{mat_id}", headers=admin_headers, params={"space_id": space_id})
    assert_ok(resp)
    resp = client.get(f"{API}/b02/materials/{mat_id}", headers=admin_headers, params={"space_id": space_id})
    assert_biz_error(resp, CODE_NOT_FOUND, "资料不存在")


def test_material_filters(client, admin_headers, test_space):
    space_id = test_space["id"]
    name_a = uid("筛选A")
    name_b = uid("筛选B")
    client.post(f"{API}/b02/materials", headers=admin_headers, params={"space_id": space_id},
                json={"name": name_a, "type": "external_link", "url": "https://a.com"})
    client.post(f"{API}/b02/materials", headers=admin_headers, params={"space_id": space_id},
                json={"name": name_b, "type": "markdown", "content": "x"})
    # keyword
    resp = client.get(f"{API}/b02/materials", headers=admin_headers, params={"space_id": space_id, "keyword": name_a})
    body = assert_ok(resp)
    assert body["data"]["total"] == 1 and body["data"]["list"][0]["name"] == name_a
    # type 筛选
    resp = client.get(f"{API}/b02/materials", headers=admin_headers, params={"space_id": space_id, "type": "markdown"})
    body = assert_ok(resp)
    assert all(m["type"] == "markdown" for m in body["data"]["list"])


def test_platform_ledger_material(client, admin_headers, test_space):
    resp = client.post(
        f"{API}/b02/materials", headers=admin_headers, params={"space_id": test_space["id"]},
        json={"name": uid("平台台账资料"), "type": "platform_ledger", "target_module": "b03"},
    )
    body = assert_ok(resp, 201)
    assert body["data"]["target_module"] == "b03"


def test_markdown_password_flow(client, admin_headers, member_headers, outsider_headers, test_space):
    space_id = test_space["id"]
    # 创建带密码 markdown
    resp = client.post(
        f"{API}/b02/materials", headers=admin_headers, params={"space_id": space_id},
        json={"name": uid("加密MD"), "type": "markdown", "content": "机密内容", "view_password": VIEW_PASSWORD},
    )
    mat_id = assert_ok(resp, 201)["data"]["id"]
    # 列表 has_password=True，content 不返回
    resp = client.get(f"{API}/b02/materials", headers=admin_headers, params={"space_id": space_id})
    row = next(m for m in assert_ok(resp)["data"]["list"] if m["id"] == mat_id)
    assert row["has_password"] is True and row["content"] is None
    # 无 token 查看详情 → 403
    resp = client.get(f"{API}/b02/materials/{mat_id}", headers=admin_headers, params={"space_id": space_id})
    assert_biz_error(resp, CODE_FORBIDDEN, "查看密码")
    # 无 token 下载 → 403
    resp = client.get(f"{API}/b02/materials/{mat_id}/download", headers=admin_headers, params={"space_id": space_id})
    assert_biz_error(resp, CODE_FORBIDDEN, "查看密码")
    # 非成员越权访问（空间权限先于密码校验） → 403 无权访问
    resp = client.get(f"{API}/b02/materials/{mat_id}", headers=outsider_headers, params={"space_id": space_id})
    assert_biz_error(resp, CODE_FORBIDDEN, "无权访问")

    # 错误密码 4 次：提示剩余次数
    for remain in (4, 3, 2, 1):
        resp = client.post(
            f"{API}/b02/materials/{mat_id}/verify-password", headers=admin_headers,
            params={"space_id": space_id}, json={"password": "Wrong@1234"},
        )
        assert_biz_error(resp, CODE_BIZ, f"还可尝试 {remain} 次")
    # 第 5 次错误 → 锁定
    resp = client.post(
        f"{API}/b02/materials/{mat_id}/verify-password", headers=admin_headers,
        params={"space_id": space_id}, json={"password": "Wrong@1234"},
    )
    assert_biz_error(resp, CODE_BIZ, "已锁定")
    # 锁定期间正确密码也被拒
    resp = client.post(
        f"{API}/b02/materials/{mat_id}/verify-password", headers=admin_headers,
        params={"space_id": space_id}, json={"password": VIEW_PASSWORD},
    )
    assert_biz_error(resp, CODE_BIZ, "已锁定")
    # 编辑免密：通过改密重置锁定（改为新密码）
    resp = client.put(
        f"{API}/b02/materials/{mat_id}", headers=admin_headers, params={"space_id": space_id},
        json={"view_password": "NewView@1234"},
    )
    assert_ok(resp)
    # 用新密码验证 → 签发 view_token
    resp = client.post(
        f"{API}/b02/materials/{mat_id}/verify-password", headers=admin_headers,
        params={"space_id": space_id}, json={"password": "NewView@1234"},
    )
    body = assert_ok(resp)
    token = body["data"]["view_token"]
    assert body["data"]["expires_in"] == 1800
    # 带 token 查看详情 → content 返回（header 方式）
    resp = client.get(f"{API}/b02/materials/{mat_id}", headers={**admin_headers, "X-View-Token": token},
                      params={"space_id": space_id})
    assert assert_ok(resp)["data"]["content"] == "机密内容"
    # 带 token 下载 → 200 + markdown 内容 + .md 文件名
    resp = client.get(f"{API}/b02/materials/{mat_id}/download", headers=admin_headers,
                      params={"space_id": space_id, "view_token": token})
    assert resp.status_code == 200
    assert resp.text == "机密内容"
    assert resp.headers["Content-Disposition"].endswith(".md")
    # 编辑免密：不带 token 也能更新资料（编辑不走密码）
    resp = client.put(
        f"{API}/b02/materials/{mat_id}", headers=admin_headers, params={"space_id": space_id},
        json={"content": "编辑后内容"},
    )
    assert_ok(resp)
    # 无密码的资料验证 → 业务错误（用全新无密码资料验证该分支）
    resp = client.post(
        f"{API}/b02/materials", headers=admin_headers, params={"space_id": space_id},
        json={"name": uid("无密码MD2"), "type": "markdown", "content": "公开内容"},
    )
    no_pwd_id = assert_ok(resp, 201)["data"]["id"]
    resp = client.post(
        f"{API}/b02/materials/{no_pwd_id}/verify-password", headers=admin_headers,
        params={"space_id": space_id}, json={"password": "x"},
    )
    assert_biz_error(resp, CODE_BIZ, "未设置查看密码")

    # 成员（L2）可正常验证并查看
    resp = client.post(
        f"{API}/b02/materials/{mat_id}/verify-password", headers=member_headers,
        params={"space_id": space_id}, json={"password": "NewView@1234"},
    )
    body = assert_ok(resp)
    member_token = body["data"]["view_token"]
    resp = client.get(f"{API}/b02/materials/{mat_id}", headers={**member_headers, "X-View-Token": member_token},
                      params={"space_id": space_id})
    assert assert_ok(resp)["data"]["content"] == "编辑后内容"


def test_download_non_markdown_rejected(client, admin_headers, test_space):
    space_id = test_space["id"]
    resp = client.post(
        f"{API}/b02/materials", headers=admin_headers, params={"space_id": space_id},
        json={"name": uid("外链资料"), "type": "external_link", "url": "https://x.com"},
    )
    mat_id = assert_ok(resp, 201)["data"]["id"]
    resp = client.get(f"{API}/b02/materials/{mat_id}/download", headers=admin_headers, params={"space_id": space_id})
    assert_biz_error(resp, CODE_BIZ, "仅 Markdown 资料支持下载")


def test_category_delete_clears_material_category(client, admin_headers, test_space):
    space_id = test_space["id"]
    resp = client.post(
        f"{API}/b02/categories", headers=admin_headers, params={"space_id": space_id},
        json={"name": uid("待删分类")},
    )
    cat_id = assert_ok(resp, 201)["data"]["id"]
    resp = client.post(
        f"{API}/b02/materials", headers=admin_headers, params={"space_id": space_id},
        json={"name": uid("归类资料"), "type": "markdown", "content": "x", "category_id": cat_id},
    )
    mat_id = assert_ok(resp, 201)["data"]["id"]
    resp = client.delete(f"{API}/b02/categories/{cat_id}", headers=admin_headers, params={"space_id": space_id})
    assert_ok(resp)
    resp = client.get(f"{API}/b02/materials/{mat_id}", headers=admin_headers, params={"space_id": space_id})
    assert assert_ok(resp)["data"]["category_id"] is None
