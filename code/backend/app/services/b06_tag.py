"""b06 标签管理服务：标签维护、标签查看、任务标签关联（跨模块关联 b04 任务）。

任务标签关联以 (task_id, tag_id) 唯一约束，关联表以「逻辑删除 + 行复用」方式避免唯一约束冲突。
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import BizError, NotFoundError
from app.models.b04_task_migration import B04Task
from app.models.b06_tag import B06Tag, B06TaskTag
from app.schemas.b06_tag import TagCreate, TagUpdate, TaskBatchTagIn, TaskTagIn


# ── 标签维护 ──
def list_tags(sdb: Session, space_id: int) -> List[dict]:
    rows = (
        sdb.query(B06Tag)
        .filter(B06Tag.space_id == space_id, B06Tag.deleted_at.is_(None))
        .order_by(B06Tag.id.desc())
        .all()
    )
    counts = dict(
        sdb.query(B06TaskTag.tag_id, func.count(B06TaskTag.id))
        .filter(B06TaskTag.space_id == space_id, B06TaskTag.deleted_at.is_(None))
        .group_by(B06TaskTag.tag_id)
        .all()
    )
    return [
        {
            "id": r.id,
            "tag_name": r.tag_name,
            "tag_description": r.tag_description,
            "tag_category": r.tag_category,
            "color": r.color,
            "task_count": counts.get(r.id, 0),
            "created_by": r.created_by,
            "created_at": r.created_at,
        }
        for r in rows
    ]


def get_tag(sdb: Session, space_id: int, tag_id: int) -> B06Tag:
    obj = (
        sdb.query(B06Tag)
        .filter(B06Tag.id == tag_id, B06Tag.space_id == space_id, B06Tag.deleted_at.is_(None))
        .first()
    )
    if not obj:
        raise NotFoundError(f"标签不存在: {tag_id}")
    return obj


def create_tag(sdb: Session, space_id: int, payload: TagCreate, operator: str) -> B06Tag:
    if (
        sdb.query(B06Tag)
        .filter(
            B06Tag.space_id == space_id,
            B06Tag.tag_name == payload.tag_name,
            B06Tag.deleted_at.is_(None),
        )
        .first()
    ):
        raise BizError(f"标签名称已存在: {payload.tag_name}")
    obj = B06Tag(
        space_id=space_id,
        tag_name=payload.tag_name,
        tag_description=payload.tag_description,
        tag_category=payload.tag_category or "技术标签",
        color=payload.color or "#1a73e8",
        created_by=operator,
    )
    sdb.add(obj)
    sdb.commit()
    sdb.refresh(obj)
    return obj


def update_tag(
    sdb: Session, space_id: int, tag_id: int, payload: TagUpdate, operator: str
) -> B06Tag:
    obj = get_tag(sdb, space_id, tag_id)
    data = payload.model_dump(exclude_unset=True)
    if "tag_name" in data and data["tag_name"] != obj.tag_name:
        if (
            sdb.query(B06Tag)
            .filter(
                B06Tag.space_id == space_id,
                B06Tag.tag_name == data["tag_name"],
                B06Tag.id != tag_id,
                B06Tag.deleted_at.is_(None),
            )
            .first()
        ):
            raise BizError(f"标签名称已存在: {data['tag_name']}")
    for field, value in data.items():
        setattr(obj, field, value)
    obj.updated_by = operator
    obj.updated_at = datetime.now()
    sdb.commit()
    sdb.refresh(obj)
    return obj


def delete_tag(sdb: Session, space_id: int, tag_id: int) -> None:
    """删除标签：级联解除任务关联（不删任务本身）。"""
    obj = get_tag(sdb, space_id, tag_id)
    now = datetime.now()
    sdb.query(B06TaskTag).filter(
        B06TaskTag.space_id == space_id,
        B06TaskTag.tag_id == tag_id,
        B06TaskTag.deleted_at.is_(None),
    ).update({B06TaskTag.deleted_at: now})
    obj.deleted_at = now
    sdb.commit()


# ── 任务标签（跨模块：标签 b06，任务 b04） ──
def _require_task(sdb: Session, space_id: int, task_id: int) -> None:
    exists = (
        sdb.query(B04Task.id)
        .filter(
            B04Task.id == task_id,
            B04Task.space_id == space_id,
            B04Task.deleted_at.is_(None),
        )
        .first()
    )
    if not exists:
        raise NotFoundError(f"任务不存在: {task_id}")


def _task_tags(sdb: Session, space_id: int, task_id: int) -> List[dict]:
    rows = (
        sdb.query(B06Tag.id, B06Tag.tag_name, B06Tag.color)
        .join(B06TaskTag, B06TaskTag.tag_id == B06Tag.id)
        .filter(
            B06TaskTag.space_id == space_id,
            B06TaskTag.task_id == task_id,
            B06TaskTag.deleted_at.is_(None),
            B06Tag.deleted_at.is_(None),
        )
        .all()
    )
    return [{"id": r[0], "name": r[1], "color": r[2]} for r in rows]


def get_task_tags(sdb: Session, space_id: int, task_id: int) -> List[dict]:
    _require_task(sdb, space_id, task_id)
    return _task_tags(sdb, space_id, task_id)


def get_task_tags_map(sdb: Session, space_id: int, task_ids: List[int]) -> dict:
    """批量获取任务→标签列表（id/name/color）映射，供列表渲染。"""
    if not task_ids:
        return {}
    rows = (
        sdb.query(B06TaskTag.task_id, B06Tag.id, B06Tag.tag_name, B06Tag.color)
        .join(B06Tag, B06Tag.id == B06TaskTag.tag_id)
        .filter(
            B06TaskTag.space_id == space_id,
            B06TaskTag.task_id.in_(task_ids),
            B06TaskTag.deleted_at.is_(None),
            B06Tag.deleted_at.is_(None),
        )
        .all()
    )
    result: dict = {}
    for task_id, tag_id, name, color in rows:
        result.setdefault(task_id, []).append({"id": tag_id, "name": name, "color": color})
    return result


def set_task_tags(
    sdb: Session, space_id: int, task_id: int, payload: TaskTagIn, operator: str
) -> List[dict]:
    """整体替换任务标签（set）。

    关联表以 (task_id, tag_id) 唯一约束，故对逻辑删除的行做「复用/复活」而非物理新增，
    避免与已逻辑删除的旧行冲突。
    """
    _require_task(sdb, space_id, task_id)
    now = datetime.now()
    valid_tags = set(
        tid
        for (tid,) in sdb.query(B06Tag.id)
        .filter(B06Tag.space_id == space_id, B06Tag.id.in_(payload.tag_ids), B06Tag.deleted_at.is_(None))
        .all()
    )
    want = set(payload.tag_ids) & valid_tags
    # 取该任务全部关联行（含已逻辑删除，用于复用）
    rows = (
        sdb.query(B06TaskTag)
        .filter(B06TaskTag.space_id == space_id, B06TaskTag.task_id == task_id)
        .all()
    )
    by_tag = {r.tag_id: r for r in rows}
    for tid in want:
        if tid in by_tag:
            by_tag[tid].deleted_at = None
            by_tag[tid].updated_by = operator
            by_tag[tid].updated_at = now
        else:
            sdb.add(
                B06TaskTag(
                    space_id=space_id, task_id=task_id, tag_id=tid, created_by=operator
                )
            )
    for tid, r in by_tag.items():
        if tid not in want and r.deleted_at is None:
            r.deleted_at = now
    sdb.commit()
    return _task_tags(sdb, space_id, task_id)


def batch_task_tags(
    sdb: Session,
    space_id: int,
    ids: List[int],
    tag_ids: List[int],
    action: str,
    operator: str,
) -> int:
    """批量打标签 / 去标签。返回受影响的任务数。"""
    if action not in ("add", "remove"):
        raise BizError("非法的批量操作")
    # 仅本空间内存在且未删除的任务
    valid_tasks = set(
        tid
        for (tid,) in sdb.query(B04Task.id)
        .filter(B04Task.space_id == space_id, B04Task.id.in_(ids), B04Task.deleted_at.is_(None))
        .all()
    )
    if not valid_tasks:
        raise NotFoundError("未找到可操作任务")
    valid_tags = set(
        tid
        for (tid,) in sdb.query(B06Tag.id)
        .filter(B06Tag.space_id == space_id, B06Tag.id.in_(tag_ids), B06Tag.deleted_at.is_(None))
        .all()
    )
    now = datetime.now()
    if action == "add":
        # 复用/复活已逻辑删除的关联，避免唯一约束冲突
        for task_id in valid_tasks:
            for tag_id in valid_tags:
                row = (
                    sdb.query(B06TaskTag)
                    .filter(
                        B06TaskTag.space_id == space_id,
                        B06TaskTag.task_id == task_id,
                        B06TaskTag.tag_id == tag_id,
                    )
                    .first()
                )
                if row is None:
                    sdb.add(
                        B06TaskTag(
                            space_id=space_id,
                            task_id=task_id,
                            tag_id=tag_id,
                            created_by=operator,
                        )
                    )
                elif row.deleted_at is not None:
                    row.deleted_at = None
                    row.updated_by = operator
                    row.updated_at = now
    else:  # remove
        sdb.query(B06TaskTag).filter(
            B06TaskTag.space_id == space_id,
            B06TaskTag.task_id.in_(valid_tasks),
            B06TaskTag.tag_id.in_(valid_tags),
            B06TaskTag.deleted_at.is_(None),
        ).update({B06TaskTag.deleted_at: now})
    sdb.commit()
    return len(valid_tasks)
