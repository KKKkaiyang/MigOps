"""加解密与密钥生成工具（b08 skill 管理 / 个人中心 API 密钥）。

- secret_key 以 Fernet（AES-128-CBC + HMAC-SHA256）加密后落库，仅生成时明文展示一次；
- access_key / secret_key 随机生成，均使用密码学安全随机数。
"""

import base64
import hashlib
import secrets
import string

from cryptography.fernet import Fernet

from app.config import settings

_ALPHABET = string.ascii_letters + string.digits


def _derive_fernet_key() -> bytes:
    """Fernet 要求 32 字节 URL-safe base64 密钥；缺省由 JWT_SECRET 派生。"""
    raw = settings.API_KEY_FERNET_KEY.strip()
    if raw:
        # 用户直接提供 Fernet 密钥（须为 32 字节 URL-safe base64）
        return raw.encode("utf-8")
    digest = hashlib.sha256(settings.JWT_SECRET.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_derive_fernet_key())
    return _fernet


def fernet_encrypt(plain: str) -> str:
    """加密明文，返回可安全存储的密文令牌。"""
    return _get_fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def fernet_decrypt(token: str) -> str:
    """解密密文令牌，返回原始明文。"""
    return _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")


def gen_access_key() -> str:
    """生成 access_key：AK 前缀 + 20 位随机字符，便于辨识。"""
    return "AK" + "".join(secrets.choice(_ALPHABET) for _ in range(20))


def gen_secret_key() -> str:
    """生成 secret_key：32 位随机字符（仅生成时向用户展示一次）。"""
    return "".join(secrets.choice(_ALPHABET) for _ in range(32))
