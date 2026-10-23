"""认证模块功能测试：登录、令牌、验证码阈值与账号锁定。"""

from tests.conftest import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    API,
    CODE_BIZ,
    CODE_CAPTCHA,
    CODE_FORBIDDEN,
    CODE_UNAUTHORIZED,
    MEMBER_PASSWORD,
    assert_biz_error,
    assert_ok,
    uid,
)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_login_success(client):
    resp = client.post(
        f"{API}/common/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    body = assert_ok(resp)
    data = body["data"]
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] > 0
    assert data["must_change_password"] is False
    assert data["user"]["username"] == ADMIN_USERNAME


def test_login_wrong_password(client):
    resp = client.post(
        f"{API}/common/auth/login",
        json={"username": ADMIN_USERNAME, "password": "Wrong@1234"},
    )
    assert_biz_error(resp, CODE_BIZ, "用户名或密码错误")


def test_login_unknown_user(client):
    resp = client.post(
        f"{API}/common/auth/login",
        json={"username": uid("nosuchuser"), "password": "Whatever@123"},
    )
    assert_biz_error(resp, CODE_BIZ, "用户名或密码错误")


def test_me_requires_token(client):
    resp = client.get(f"{API}/common/auth/me")
    assert_biz_error(resp, CODE_UNAUTHORIZED)


def test_me_with_token(client, admin_headers):
    resp = client.get(f"{API}/common/auth/me", headers=admin_headers)
    body = assert_ok(resp)
    assert body["data"]["username"] == ADMIN_USERNAME
    assert body["data"]["is_l0"] is True


def test_me_with_invalid_token(client):
    resp = client.get(f"{API}/common/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert_biz_error(resp, CODE_UNAUTHORIZED)


def test_captcha_required_after_threshold(client, throwaway_user, captcha_helper):
    """连续失败 3 次后第 4 次必须验证码；带正确验证码+正确密码可登录成功。"""
    user = throwaway_user("functest_captcha")
    # 前 3 次失败：无需验证码，每次提示剩余次数
    for remain in (9, 8, 7):
        resp = client.post(
            f"{API}/common/auth/login",
            json={"username": user["username"], "password": "Wrong@1234"},
        )
        assert_biz_error(resp, CODE_BIZ, f"还可尝试 {remain} 次")
    # 第 4 次不带验证码 → 验证码缺失
    resp = client.post(
        f"{API}/common/auth/login",
        json={"username": user["username"], "password": MEMBER_PASSWORD},
    )
    assert_biz_error(resp, CODE_CAPTCHA)
    # 带正确验证码 + 错误密码 → 仍失败（计数 +1）
    captcha_id, code = captcha_helper()
    resp = client.post(
        f"{API}/common/auth/login",
        json={
            "username": user["username"],
            "password": "Wrong@1234",
            "captcha_id": captcha_id,
            "captcha_code": code,
        },
    )
    assert_biz_error(resp, CODE_BIZ, "还可尝试 6 次")
    # 带正确验证码 + 正确密码 → 登录成功，计数复位
    captcha_id, code = captcha_helper()
    resp = client.post(
        f"{API}/common/auth/login",
        json={
            "username": user["username"],
            "password": MEMBER_PASSWORD,
            "captcha_id": captcha_id,
            "captcha_code": code,
        },
    )
    body = assert_ok(resp)
    assert body["data"]["user"]["username"] == user["username"]


def test_account_lockout_after_threshold(client, throwaway_user, captcha_helper):
    """失败计数达到上限（10）立即触发账号锁定，且锁定后正确密码也拒绝。"""
    user = throwaway_user("functest_lock")
    user_id = user["user_id"]
    # 将失败计数直接置为 9（模拟已接近阈值），规避反复验证码时序
    from app.database import SessionLocal
    from app.models.user import CommonUser

    db = SessionLocal()
    try:
        db.query(CommonUser).filter(CommonUser.id == user_id).update({"login_fail_count": 9})
        db.commit()
    finally:
        db.close()
    # 第 1 次失败（需验证码）：count 9→10 立即触发锁定，响应应为锁定提示
    captcha_id, code = captcha_helper()
    resp = client.post(
        f"{API}/common/auth/login",
        json={
            "username": user["username"],
            "password": "Wrong@1234",
            "captcha_id": captcha_id,
            "captcha_code": code,
        },
    )
    assert_biz_error(resp, CODE_FORBIDDEN, "账号已锁定")
    # 锁定期间即便密码正确也被拒绝（账号已锁定优先于密码校验）
    resp = client.post(
        f"{API}/common/auth/login",
        json={"username": user["username"], "password": MEMBER_PASSWORD},
    )
    assert_biz_error(resp, CODE_FORBIDDEN, "账号已锁定")


def test_login_lockout_full_sequence(client, throwaway_user, captcha_helper):
    """完整链路：连续失败 1→3 无需验证码（剩余 9/8/7），
    4 起需验证码，直到第 10 次失败触发锁定（ForbiddenError）。"""
    user = throwaway_user("functest_seq")
    # 前 3 次失败：无需验证码，提示剩余次数
    for remain in (9, 8, 7):
        resp = client.post(
            f"{API}/common/auth/login",
            json={"username": user["username"], "password": "Wrong@1234"},
        )
        assert_biz_error(resp, CODE_BIZ, f"还可尝试 {remain} 次")
    # 第 4~9 次失败：需要验证码，剩余 6/5/4/3/2/1
    for remain in (6, 5, 4, 3, 2, 1):
        captcha_id, code = captcha_helper()
        resp = client.post(
            f"{API}/common/auth/login",
            json={
                "username": user["username"],
                "password": "Wrong@1234",
                "captcha_id": captcha_id,
                "captcha_code": code,
            },
        )
        assert_biz_error(resp, CODE_BIZ, f"还可尝试 {remain} 次")
    # 第 10 次失败：触发锁定，立即返回锁定提示
    captcha_id, code = captcha_helper()
    resp = client.post(
        f"{API}/common/auth/login",
        json={
            "username": user["username"],
            "password": "Wrong@1234",
            "captcha_id": captcha_id,
            "captcha_code": code,
        },
    )
    assert_biz_error(resp, CODE_FORBIDDEN, "账号已锁定")


def test_logout(client, admin_headers):
    resp = client.post(f"{API}/common/auth/logout", headers=admin_headers)
    assert_ok(resp)
