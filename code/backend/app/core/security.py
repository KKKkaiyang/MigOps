"""安全基座：密码哈希、JWT、密码复杂度、图形验证码。

密码方案（公共业务需求 §3.2 / §7.1）：
- 采用 bcrypt 自适应成本哈希，仅存密文，不存明文；
- 复杂度：长度 ≥ 8，且包含大写字母、小写字母、数字、特殊字符中的三类；
- 验证码：4 位字符（数字 + 字母，排除易混字符 1/I/0/O），内存存储，TTL 内单次消费。
"""

import random
import re
import string
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

import bcrypt
import jwt

from app.config import settings
from app.core.exceptions import BizError, CaptchaError

# ── 密码复杂度 ──
PASSWORD_MIN_LENGTH = 8
PASSWORD_CATEGORIES = 3

# 验证码字符集：数字 + 大小写字母，排除易混淆字符 1 I 0 O
_CAPTCHA_POOL = "".join(
    c
    for c in string.digits + string.ascii_uppercase + string.ascii_lowercase
    if c not in "1I0O"
)
CAPTCHA_LENGTH = 4


# ── 密码哈希 ──
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def validate_password_complexity(password: str) -> None:
    """校验密码复杂度，不满足则抛出 BizError。"""
    if not password or len(password) < PASSWORD_MIN_LENGTH:
        raise BizError(f"密码长度至少 {PASSWORD_MIN_LENGTH} 位")
    categories = 0
    if re.search(r"[A-Z]", password):
        categories += 1
    if re.search(r"[a-z]", password):
        categories += 1
    if re.search(r"\d", password):
        categories += 1
    if re.search(r"[^A-Za-z0-9]", password):
        categories += 1
    if categories < PASSWORD_CATEGORIES:
        raise BizError("密码需包含大写字母、小写字母、数字、特殊字符中的三类")


def gen_temp_password() -> str:
    """生成满足复杂度策略的临时密码。"""
    upper = random.choice(string.ascii_uppercase)
    lower = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    special = random.choice("!@#$%^&*")
    rest = "".join(
        random.choices(string.ascii_letters + string.digits + "!@#$%^&*", k=6)
    )
    return upper + lower + digit + special + rest


# ── JWT ──
def create_access_token(user_id: int, username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict:
    """解析并校验 JWT，失败抛出 UnauthorizedError。"""
    from app.core.exceptions import UnauthorizedError

    try:
        return jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("登录已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise UnauthorizedError("无效的登录凭证")


# ── markdown 资料查看令牌（项目空间业务需求 D16） ──
VIEW_TOKEN_TYPE = "material_view"


def create_view_token(material_id: int, user_id: int, space_id: int) -> str:
    """签发资料查看令牌：密码验证通过后会话内复用，TTL 内有效。"""
    now = datetime.now(timezone.utc)
    payload = {
        "type": VIEW_TOKEN_TYPE,
        "mid": material_id,
        "uid": user_id,
        "sid": space_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.VIEW_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_view_token(token: str, material_id: int, user_id: int, space_id: int) -> bool:
    """校验查看令牌是否匹配当前资料/用户/空间；无效或过期返回 False。"""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.InvalidTokenError:
        return False
    return (
        payload.get("type") == VIEW_TOKEN_TYPE
        and payload.get("mid") == material_id
        and payload.get("uid") == user_id
        and payload.get("sid") == space_id
    )


# ── 验证码（内存存储，TTL + 单次消费） ──
# captcha_id -> {"code": str, "expire_at": float}
_captcha_store: Dict[str, Dict] = {}


def _gc_captcha() -> None:
    now = time.time()
    expired = [cid for cid, item in _captcha_store.items() if item["expire_at"] <= now]
    for cid in expired:
        _captcha_store.pop(cid, None)


def gen_captcha_code() -> str:
    return "".join(random.choices(_CAPTCHA_POOL, k=CAPTCHA_LENGTH))


def create_captcha() -> Tuple[str, str, str]:
    """创建验证码，返回 (captcha_id, code, svg)。"""
    _gc_captcha()
    captcha_id = uuid.uuid4().hex
    code = gen_captcha_code()
    _captcha_store[captcha_id] = {
        "code": code,
        "expire_at": time.time() + settings.CAPTCHA_TTL_SECONDS,
    }
    return captcha_id, code, render_captcha_svg(code)


def verify_captcha(captcha_id: Optional[str], code: Optional[str]) -> bool:
    """校验验证码：单次消费，过期或不存在均视为失败。"""
    if not captcha_id or not code:
        return False
    item = _captcha_store.pop(captcha_id, None)
    if not item:
        return False
    if item["expire_at"] <= time.time():
        return False
    return item["code"].lower() == code.strip().lower()


def assert_captcha(captcha_id: Optional[str], code: Optional[str]) -> None:
    if not verify_captcha(captcha_id, code):
        raise CaptchaError()


def render_captcha_svg(code: str) -> str:
    """渲染 4 位字符验证码 SVG（带干扰线与随机偏移）。"""
    width, height = 120, 44
    chars = list(code)
    text_nodes = []
    for i, ch in enumerate(chars):
        x = 16 + i * 27 + random.randint(-3, 3)
        y = 30 + random.randint(-4, 4)
        rotate = random.randint(-18, 18)
        color = random.choice(["#1a73e8", "#37475a", "#188038", "#b06a00"])
        text_nodes.append(
            f'<text x="{x}" y="{y}" font-size="24" font-family="Menlo, Consolas, monospace" '
            f'fill="{color}" transform="rotate({rotate} {x} {y})">{ch}</text>'
        )
    lines = []
    for _ in range(3):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        lines.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#c7d2e0" stroke-width="1"/>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<rect width="{width}" height="{height}" fill="#f3f6fb" rx="6"/>'
        f'{"".join(lines)}{"".join(text_nodes)}</svg>'
    )
