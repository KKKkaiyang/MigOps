"""API 密钥服务（b08 / 个人中心）：生成、列表、吊销、切换，以及 ak/sk 签名校验。"""

import hashlib
import hmac
import time
from typing import Dict, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.core.crypto import fernet_decrypt, fernet_encrypt, gen_access_key, gen_secret_key
from app.core.exceptions import BizError, UnauthorizedError
from app.models.common_user_api_key import (
    API_KEY_STATUS_DISABLED,
    API_KEY_STATUS_ENABLED,
    CommonUserApiKey,
)
from app.models.user import USER_STATUS_ENABLED, CommonUser

# nonce 防重放缓存：nonce -> 过期时间戳（秒）
_nonce_cache: Dict[str, float] = {}


def _purge_nonce_cache(now: float) -> None:
    expired = [n for n, exp in _nonce_cache.items() if exp <= now]
    for n in expired:
        _nonce_cache.pop(n, None)


def create_key(db: Session, user_id: int, operator: str) -> Tuple[CommonUserApiKey, str]:
    """生成密钥对；返回 (记录, 明文 secret_key)。secret 仅此一次明文。"""
    access_key = gen_access_key()
    secret_key = gen_secret_key()
    secret_enc = fernet_encrypt(secret_key)
    obj = CommonUserApiKey(
        user_id=user_id,
        access_key=access_key,
        secret_key_enc=secret_enc,
        status=API_KEY_STATUS_ENABLED,
        created_by=operator,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj, secret_key


def list_keys(db: Session, user_id: int) -> list[CommonUserApiKey]:
    return (
        db.query(CommonUserApiKey)
        .filter(
            CommonUserApiKey.user_id == user_id,
            CommonUserApiKey.deleted_at.is_(None),
        )
        .order_by(CommonUserApiKey.id.desc())
        .all()
    )


def revoke_key(db: Session, user_id: int, key_id: int, operator: str) -> None:
    obj = (
        db.query(CommonUserApiKey)
        .filter(
            CommonUserApiKey.id == key_id,
            CommonUserApiKey.user_id == user_id,
            CommonUserApiKey.deleted_at.is_(None),
        )
        .first()
    )
    if not obj:
        raise BizError("密钥不存在")
    obj.deleted_at = _now_dt()
    obj.updated_by = operator
    db.commit()


def toggle_key(db: Session, user_id: int, key_id: int, operator: str) -> CommonUserApiKey:
    obj = (
        db.query(CommonUserApiKey)
        .filter(
            CommonUserApiKey.id == key_id,
            CommonUserApiKey.user_id == user_id,
            CommonUserApiKey.deleted_at.is_(None),
        )
        .first()
    )
    if not obj:
        raise BizError("密钥不存在")
    obj.status = (
        API_KEY_STATUS_DISABLED
        if obj.status == API_KEY_STATUS_ENABLED
        else API_KEY_STATUS_ENABLED
    )
    obj.updated_by = operator
    db.commit()
    db.refresh(obj)
    return obj


def verify_signature(
    db: Session,
    access_key: str | None,
    method: str,
    path: str,
    timestamp: str | None,
    nonce: str | None,
    signature: str | None,
) -> CommonUser:
    """校验 ak/sk HMAC 签名，成功返回对应用户，失败抛 UnauthorizedError。"""
    if not (access_key and timestamp and nonce and signature):
        raise UnauthorizedError("缺少 ak/sk 签名头")

    try:
        ts = int(timestamp)  # 毫秒
    except (TypeError, ValueError):
        raise UnauthorizedError("时间戳非法")

    now_ms = int(time.time() * 1000)
    skew_ms = settings.API_SIGN_TIME_SKEW_SECONDS * 1000
    if abs(now_ms - ts) > skew_ms:
        raise UnauthorizedError("签名时间戳超出允许偏差")

    now = time.time()
    _purge_nonce_cache(now)
    nonce_ttl = settings.API_SIGN_NONCE_TTL_SECONDS
    if nonce in _nonce_cache:
        raise UnauthorizedError("签名 nonce 已使用（防重放）")
    _nonce_cache[nonce] = now + nonce_ttl

    key = (
        db.query(CommonUserApiKey)
        .filter(
            CommonUserApiKey.access_key == access_key,
            CommonUserApiKey.deleted_at.is_(None),
        )
        .first()
    )
    if not key or key.status != API_KEY_STATUS_ENABLED:
        raise UnauthorizedError("access_key 无效或已停用")

    secret = fernet_decrypt(key.secret_key_enc)
    message = f"{method}\n{path}\n{timestamp}\n{nonce}"
    expected = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise UnauthorizedError("签名校验失败")

    user = (
        db.query(CommonUser)
        .filter(CommonUser.id == key.user_id, CommonUser.deleted_at.is_(None))
        .first()
    )
    if not user or user.status != USER_STATUS_ENABLED:
        raise UnauthorizedError("用户不可用")

    try:
        key.last_used_at = _now_dt()
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()

    return user


def _now_dt():
    from datetime import datetime

    return datetime.now()
