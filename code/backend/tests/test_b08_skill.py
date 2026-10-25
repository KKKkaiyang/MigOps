"""b08 skill 管理冒烟测试：登录 → API 密钥 → ak/sk 上传 → 市场列表 → 下载（token / ak/sk）→ 错误签名拒绝。

运行：.venv/bin/python -m pytest tests/test_b08_skill.py -q
需本地 MySQL 且已创建 mig_common_db（bootstrap 会建表并种子 admin）。
"""

import hashlib
import hmac
import time

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models.b08_skill import B08Skill
from app.models.common_user_api_key import CommonUserApiKey

from main import app

BASE = "/api/v1"
client = TestClient(app)  # 触发 startup：建表 + 种子 admin


@pytest.fixture(autouse=True)
def _clean_b08_tables():
    """真实 MySQL 无事务回滚，测试前清空 b08 两张表，保证用例幂等。"""
    db = SessionLocal()
    try:
        db.query(CommonUserApiKey).delete()
        db.query(B08Skill).delete()
        db.commit()
    finally:
        db.close()
    yield


def _token():
    r = client.post(
        f"{BASE}/common/auth/login",
        json={"username": "admin", "password": "Admin@1234"},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["token"]


def _sign(access_key, secret, method, path, ts, nonce):
    msg = f"{method}\n{path}\n{ts}\n{nonce}"
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()


def test_market_empty():
    tok = _token()
    r = client.get(f"{BASE}/b08/skills/market", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json()["data"]["total"] == 0


def test_full_flow():
    tok = _token()

    # 1) 生成 API 密钥（secret 仅一次明文）
    r = client.post(f"{BASE}/common/users/me/api-keys", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 201, r.text
    body = r.json()["data"]
    ak, sk = body["access_key"], body["secret_key"]
    assert sk

    # 2) 用 ak/sk 签名上传 skill
    path_up = f"{BASE}/b08/skills"
    ts = str(int(time.time() * 1000))
    nonce = "nonce-upload-1"
    sig = _sign(ak, sk, "POST", path_up, ts, nonce)
    content = b"PK\x03\x04 fake-zip-bytes"
    r = client.post(
        path_up,
        files={"file": ("demo.zip", content, "application/zip")},
        data={"name": "smoke-skill", "intro": "冒烟测试", "is_public": "1"},
        headers={"X-Access-Key": ak, "X-Timestamp": ts, "X-Nonce": nonce, "X-Signature": sig},
    )
    assert r.status_code == 201, r.text
    code = r.json()["data"]["skill_code"]

    # 3) 市场列表（token）应可见该公开 skill
    r = client.get(f"{BASE}/b08/skills/market", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json()["data"]["total"] == 1

    # 4) 下载（ak/sk）
    path_dl = f"{BASE}/b08/skills/{code}/download"
    ts = str(int(time.time() * 1000))
    nonce = "nonce-dl-1"
    sig = _sign(ak, sk, "GET", path_dl, ts, nonce)
    r = client.get(
        path_dl,
        headers={"X-Access-Key": ak, "X-Timestamp": ts, "X-Nonce": nonce, "X-Signature": sig},
    )
    assert r.status_code == 200, r.text
    assert r.content == content

    # 5) 下载（token）同样可行
    r = client.get(path_dl, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200

    # 6) 错误签名应被拒绝（40100）
    ts = str(int(time.time() * 1000))
    nonce = "nonce-bad-1"
    r = client.get(
        path_dl,
        headers={"X-Access-Key": ak, "X-Timestamp": ts, "X-Nonce": nonce, "X-Signature": "deadbeef"},
    )
    assert r.json()["code"] == 40100, r.text

    # 7) 缺失鉴权头应被拒绝（40100）
    r = client.post(
        path_up,
        files={"file": ("a.zip", b"x", "application/zip")},
        data={"name": "x"},
    )
    assert r.json()["code"] == 40100

    # 8) 吊销密钥后签名失效
    r = client.delete(f"{BASE}/common/users/me/api-keys/{{kid}}".format(kid=body["id"]),
                      headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    ts = str(int(time.time() * 1000))
    nonce = "nonce-revoked-1"
    sig = _sign(ak, sk, "GET", path_dl, ts, nonce)
    r = client.get(
        path_dl,
        headers={"X-Access-Key": ak, "X-Timestamp": ts, "X-Nonce": nonce, "X-Signature": sig},
    )
    assert r.json()["code"] == 40100
