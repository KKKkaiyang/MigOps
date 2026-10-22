"""认证服务：登录（验证码 + 锁定）、改密、当前用户信息。"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import ROLE_L0, list_user_roles
from app.core.exceptions import BizError, CaptchaError, ForbiddenError
from app.core.security import (
    assert_captcha,
    create_access_token,
    hash_password,
    validate_password_complexity,
    verify_password,
)
from app.models.role import ROLE_LEVEL_NAMES
from app.models.user import USER_STATUS_DISABLED, USER_STATUS_ENABLED, CommonUser
from app.schemas.auth import ChangePasswordIn, CurrentUserOut, LoginIn, LoginOut


def _get_active_user(db: Session, username: str) -> Optional[CommonUser]:
    return (
        db.query(CommonUser)
        .filter(CommonUser.username == username, CommonUser.deleted_at.is_(None))
        .first()
    )


def _lock_remaining_minutes(user: CommonUser) -> int:
    remain = (user.locked_until - datetime.now()).total_seconds() / 60
    return max(1, int(remain) + 1)


def _register_failure(db: Session, user: CommonUser) -> None:
    """登记一次登录失败：计数 +1；达到阈值则锁定账号。"""
    user.login_fail_count = (user.login_fail_count or 0) + 1
    user.last_fail_at = datetime.now()
    if user.login_fail_count >= settings.LOGIN_LOCK_THRESHOLD:
        user.locked_until = datetime.now() + timedelta(
            minutes=settings.LOGIN_LOCK_MINUTES
        )
        user.login_fail_count = 0
    db.commit()


def login(db: Session, payload: LoginIn) -> LoginOut:
    user = _get_active_user(db, payload.username)

    # 用户不存在时也走一次哈希比对，避免时间侧信道泄露用户名
    if not user:
        verify_password(payload.password, hash_password("dummy-password"))
        raise BizError("用户名或密码错误")

    if user.status != USER_STATUS_ENABLED:
        raise ForbiddenError("账号已停用，请联系管理员")

    if user.locked_until and user.locked_until > datetime.now():
        raise ForbiddenError(
            f"密码错误次数过多，账号已锁定，请 {_lock_remaining_minutes(user)} 分钟后重试"
        )

    # 连续失败达到阈值后必须输入验证码
    if (user.login_fail_count or 0) >= settings.CAPTCHA_FAIL_THRESHOLD:
        if not payload.captcha_id or not payload.captcha_code:
            raise CaptchaError("请输入验证码")
        assert_captcha(payload.captcha_id, payload.captcha_code)

    if not verify_password(payload.password, user.password):
        _register_failure(db, user)
        remain = settings.LOGIN_LOCK_THRESHOLD - (user.login_fail_count or 0)
        if remain > 0:
            raise BizError(f"用户名或密码错误，还可尝试 {remain} 次")
        raise ForbiddenError(
            f"密码错误次数过多，账号已锁定 {settings.LOGIN_LOCK_MINUTES} 分钟"
        )

    # 登录成功：重置失败计数与锁定状态
    user.login_fail_count = 0
    user.locked_until = None
    user.last_fail_at = None
    user.last_login_at = datetime.now()
    db.commit()
    db.refresh(user)

    return LoginOut(
        token=create_access_token(user.id, user.username),
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
        user={
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "org_type": user.org_type,
        },
        must_change_password=bool(user.must_change_password),
    )


def change_password(db: Session, user: CommonUser, payload: ChangePasswordIn) -> None:
    if not verify_password(payload.old_password, user.password):
        raise BizError("原密码错误")
    if payload.old_password == payload.new_password:
        raise BizError("新密码不能与原密码相同")
    validate_password_complexity(payload.new_password)

    user.password = hash_password(payload.new_password)
    user.must_change_password = 0
    user.updated_by = user.username
    user.updated_at = datetime.now()
    db.commit()


def build_current_user(db: Session, user: CommonUser) -> CurrentUserOut:
    roles = list_user_roles(db, user.id)
    role_payload = []
    is_l0 = False
    for r in roles:
        space_name = None
        if r.space_id:
            from app.models.space import MigSpace

            space = (
                db.query(MigSpace)
                .filter(MigSpace.id == r.space_id, MigSpace.deleted_at.is_(None))
                .first()
            )
            space_name = space.space_name if space else None
        else:
            is_l0 = True
        role_payload.append(
            {
                "role_level": r.role_level,
                "role_name": ROLE_LEVEL_NAMES.get(r.role_level, r.role_level),
                "space_id": r.space_id,
                "space_name": space_name,
            }
        )
    return CurrentUserOut(
        id=user.id,
        username=user.username,
        name=user.name,
        email=user.email,
        phone=user.phone,
        org_type=user.org_type,
        status=user.status,
        is_l0=is_l0,
        roles=role_payload,
        last_login_at=user.last_login_at,
    )
