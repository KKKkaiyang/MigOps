from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.response import ok
from app.core.security import create_captcha
from app.database import get_db
from app.models.user import CommonUser
from app.schemas.auth import CaptchaOut, ChangePasswordIn, LoginIn, LoginOut
from app.services import auth as svc

router = APIRouter(prefix="/common/auth", tags=["common-用户认证"])


@router.get("/captcha")
def captcha():
    """获取图形验证码（4 位字符，排除易混字符 1/I/0/O）。"""
    captcha_id, _code, svg = create_captcha()
    return ok(data=CaptchaOut(captcha_id=captcha_id, svg=svg))


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    """用户名 + 密码登录；连续失败达阈值需验证码，累计达上限锁定账号。"""
    result = svc.login(db, payload)
    return ok(data=result, message="登录成功")


@router.get("/me")
def me(user: CommonUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """当前登录用户信息与角色。"""
    return ok(data=svc.build_current_user(db, user))


@router.post("/change-password")
def change_password(
    payload: ChangePasswordIn,
    user: CommonUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码（临时密码登录后被强制走此流程）。"""
    svc.change_password(db, user, payload)
    return ok(message="密码修改成功")


@router.post("/logout")
def logout(user: CommonUser = Depends(get_current_user)):
    """登出（JWT 无状态，客户端丢弃令牌即可）。"""
    return ok(message="已退出登录")
