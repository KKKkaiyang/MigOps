"""双鉴权（Bearer / ak/sk）冒烟测试：覆盖 b03 / b04 / b07（AK-02 / BRD §4.5 / §9.10 D2）。

验证：
- 空间成员持 ak/sk 可签名调用 b03/b04/b07 接口（须为空间成员，D2）；
- 非空间成员持 ak/sk 调用被拒（40300）；
- 错误签名被拒（40100）；
- 既有 Bearer 登录态调用不受影响。

需本地 MySQL 且已创建 mig_common_db（bootstrap 会建表并种子 admin）。
"""

import hashlib
import hmac
import time

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models.common_user_api_key import CommonUserApiKey

from tests.conftest import (
    API,
    CODE_FORBIDDEN,
    CODE_UNAUTHORIZED,
    assert_biz_error,
    assert_ok,
    uid,
)


@pytest.fixture(autouse=True)
def _clean_api_keys():
    """真实 MySQL 无事务回滚，用例前清空 API 密钥表，保证幂等。"""
    db = SessionLocal()
    try:
        db.query(CommonUserApiKey).delete()
        db.commit()
    finally:
        db.close()
    yield


def _sign(access_key, secret, method, path, ts, nonce):
    msg = f"{method}\n{path}\n{ts}\n{nonce}"
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()


def _create_api_key(client, user_headers) -> tuple[str, str]:
    """为某登录用户生成密钥对，返回 (access_key, secret_key 明文)。"""
    resp = client.post(f"{API}/common/users/me/api-keys", headers=user_headers)
    body = assert_ok(resp, 201)
    return body["data"]["access_key"], body["data"]["secret_key"]


def _signed_headers(access_key, secret, method, path) -> dict:
    ts = str(int(time.time() * 1000))
    nonce = f"nonce-{access_key}-{int(ts)}"
    sig = _sign(access_key, secret, method, path, ts, nonce)
    return {
        "X-Access-Key": access_key,
        "X-Timestamp": ts,
        "X-Nonce": nonce,
        "X-Signature": sig,
    }


def test_b03_aksk_member_ok(client, member_headers, test_space):
    """空间成员持 ak/sk 可签名调用 b03（D2：成员校验通过）。"""
    ak, sk = _create_api_key(client, member_headers)
    space_id = test_space["id"]
    path = f"{API}/b03/scenarios"
    # 列表
    resp = client.get(
        f"{path}",
        params={"space_id": space_id},
        headers=_signed_headers(ak, sk, "GET", path),
    )
    assert_ok(resp)
    # 创建场景（写操作）
    resp = client.post(
        f"{path}",
        params={"space_id": space_id},
        json={"name": uid("aksk_b03"), "remark": "双鉴权测试"},
        headers=_signed_headers(ak, sk, "POST", path),
    )
    body = assert_ok(resp, 201)
    sc_id = body["data"]["id"]
    # 清理
    client.delete(
        f"{path}/{sc_id}",
        params={"space_id": space_id},
        headers=_signed_headers(ak, sk, "DELETE", f"{path}/{sc_id}"),
    )


def test_b04_aksk_member_ok(client, member_headers, test_space):
    """空间成员持 ak/sk 可签名调用 b04（含 b06 标签、台账，均走 b04 路由）。"""
    ak, sk = _create_api_key(client, member_headers)
    space_id = test_space["id"]
    path = f"{API}/b04/scenarios"
    resp = client.post(
        f"{path}",
        params={"space_id": space_id},
        json={"name": uid("aksk_b04"), "remark": "双鉴权测试"},
        headers=_signed_headers(ak, sk, "POST", path),
    )
    body = assert_ok(resp, 201)
    sc_id = body["data"]["id"]
    # 列表
    resp = client.get(
        f"{path}",
        params={"space_id": space_id},
        headers=_signed_headers(ak, sk, "GET", path),
    )
    assert_ok(resp)
    client.delete(
        f"{path}/{sc_id}",
        params={"space_id": space_id},
        headers=_signed_headers(ak, sk, "DELETE", f"{path}/{sc_id}"),
    )


def test_b07_aksk_member_ok(client, member_headers, test_space):
    """空间成员持 ak/sk 可签名调用 b07 血缘接口。"""
    ak, sk = _create_api_key(client, member_headers)
    space_id = test_space["id"]
    path = f"{API}/b07/lineages"
    resp = client.get(
        f"{path}",
        params={"space_id": space_id},
        headers=_signed_headers(ak, sk, "GET", path),
    )
    assert_ok(resp)


def test_aksk_non_member_forbidden(client, outsider_headers, test_space):
    """非空间成员持 ak/sk 调用 b03 → 40300（D2：空间成员校验）。"""
    ak, sk = _create_api_key(client, outsider_headers)
    space_id = test_space["id"]
    path = f"{API}/b03/scenarios"
    resp = client.get(
        f"{path}",
        params={"space_id": space_id},
        headers=_signed_headers(ak, sk, "GET", path),
    )
    assert_biz_error(resp, CODE_FORBIDDEN, "无权访问该项目空间")


def test_aksk_bad_signature_rejected(client, member_headers, test_space):
    """错误签名 → 40100（ak/sk 校验失败）。"""
    ak, sk = _create_api_key(client, member_headers)
    space_id = test_space["id"]
    path = f"{API}/b03/scenarios"
    headers = _signed_headers(ak, sk, "GET", path)
    headers["X-Signature"] = "deadbeef"
    resp = client.get(f"{path}", params={"space_id": space_id}, headers=headers)
    assert_biz_error(resp, CODE_UNAUTHORIZED)


def test_bearer_still_works(client, admin_headers, test_space):
    """既有 Bearer 登录态调用 b03 不受影响（双鉴权向后兼容）。"""
    space_id = test_space["id"]
    resp = client.get(
        f"{API}/b03/scenarios",
        params={"space_id": space_id},
        headers=admin_headers,
    )
    assert_ok(resp)
