"""空间真实统计服务：跨模块聚合空间库各业务表计数（供空间概览页展示）。

统计口径（与《迁移管家平台-界面交互与排版评审》I8 / 原型 P3 对齐）：
- b02：资料总数、分类总数；
- b03：场景数、库表总数、元数据/全量/增量三类状态分布、迁移过程记录数；
- b04：场景数、任务总数、迁移状态分布、排查备注数、自定义台账数（含固化合计数）；
- b06：标签总数、管理/技术分类数；
- b07：血缘边数、工作流数（去重）。

本服务只读空间库（sdb），不做跨库 JOIN；权限由路由层 require_space_member 校验。
"""

import logging
from typing import Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.b02_material import B02Category, B02Material
from app.models.b03_data_migration import (
    B03MigrationRecord,
    B03Scenario,
    B03TableItem,
)
from app.models.b04_task_migration import (
    B04SavedView,
    B04Scenario,
    B04Task,
    B04TaskNote,
)
from app.models.b06_tag import B06Tag
from app.models.b07_lineage import B07Lineage

logger = logging.getLogger("migops")


def _count_by(sdb: Session, model, column, space_id: int) -> Dict[str, int]:
    """按枚举列分组计数（已逻辑删除行不计）。"""
    rows = (
        sdb.query(column, func.count())
        .filter(model.space_id == space_id, model.deleted_at.is_(None))
        .group_by(column)
        .all()
    )
    return {str(k): int(v) for k, v in rows if k is not None}


def space_stats(sdb: Session, space_id: int) -> dict:
    """聚合当前空间的真实业务统计。"""
    stats: dict = {}

    # ── b02 项目资料索引 ──
    stats["b02_material_count"] = (
        sdb.query(func.count(B02Material.id))
        .filter(B02Material.space_id == space_id, B02Material.deleted_at.is_(None))
        .scalar()
        or 0
    )
    stats["b02_category_count"] = (
        sdb.query(func.count(B02Category.id))
        .filter(B02Category.space_id == space_id, B02Category.deleted_at.is_(None))
        .scalar()
        or 0
    )

    # ── b03 数据迁移 ──
    stats["b03_scenario_count"] = (
        sdb.query(func.count(B03Scenario.id))
        .filter(B03Scenario.space_id == space_id, B03Scenario.deleted_at.is_(None))
        .scalar()
        or 0
    )
    stats["b03_table_total"] = (
        sdb.query(func.count(B03TableItem.id))
        .filter(B03TableItem.space_id == space_id, B03TableItem.deleted_at.is_(None))
        .scalar()
        or 0
    )
    stats["b03_metadata_stats"] = _count_by(
        sdb, B03TableItem, B03TableItem.metadata_status, space_id
    )
    stats["b03_full_sync_stats"] = _count_by(
        sdb, B03TableItem, B03TableItem.full_sync_status, space_id
    )
    stats["b03_incr_sync_stats"] = _count_by(
        sdb, B03TableItem, B03TableItem.incr_sync_status, space_id
    )
    stats["b03_record_count"] = (
        sdb.query(func.count(B03MigrationRecord.id))
        .filter(B03MigrationRecord.space_id == space_id, B03MigrationRecord.deleted_at.is_(None))
        .scalar()
        or 0
    )

    # ── b04 任务迁移 ──
    stats["b04_scenario_count"] = (
        sdb.query(func.count(B04Scenario.id))
        .filter(B04Scenario.space_id == space_id, B04Scenario.deleted_at.is_(None))
        .scalar()
        or 0
    )
    stats["b04_task_total"] = (
        sdb.query(func.count(B04Task.id))
        .filter(B04Task.space_id == space_id, B04Task.deleted_at.is_(None))
        .scalar()
        or 0
    )
    stats["b04_migration_stats"] = _count_by(sdb, B04Task, B04Task.migration_status, space_id)
    stats["b04_note_count"] = (
        sdb.query(func.count(B04TaskNote.id))
        .filter(B04TaskNote.space_id == space_id, B04TaskNote.deleted_at.is_(None))
        .scalar()
        or 0
    )
    stats["b04_view_count"] = (
        sdb.query(func.count(B04SavedView.id))
        .filter(B04SavedView.space_id == space_id, B04SavedView.deleted_at.is_(None))
        .scalar()
        or 0
    )
    stats["b04_fixed_view_count"] = (
        sdb.query(func.count(B04SavedView.id))
        .filter(
            B04SavedView.space_id == space_id,
            B04SavedView.deleted_at.is_(None),
            B04SavedView.view_mode == "fixed",
        )
        .scalar()
        or 0
    )

    # ── b06 标签管理 ──
    stats["b06_tag_count"] = (
        sdb.query(func.count(B06Tag.id))
        .filter(B06Tag.space_id == space_id, B06Tag.deleted_at.is_(None))
        .scalar()
        or 0
    )
    stats["b06_manage_tag_count"] = (
        sdb.query(func.count(B06Tag.id))
        .filter(
            B06Tag.space_id == space_id,
            B06Tag.deleted_at.is_(None),
            B06Tag.tag_category == "管理标签",
        )
        .scalar()
        or 0
    )
    stats["b06_tech_tag_count"] = (
        sdb.query(func.count(B06Tag.id))
        .filter(
            B06Tag.space_id == space_id,
            B06Tag.deleted_at.is_(None),
            B06Tag.tag_category == "技术标签",
        )
        .scalar()
        or 0
    )

    # ── b07 血缘管理 ──
    stats["b07_edge_count"] = (
        sdb.query(func.count(B07Lineage.id))
        .filter(B07Lineage.space_id == space_id, B07Lineage.deleted_at.is_(None))
        .scalar()
        or 0
    )
    stats["b07_workflow_count"] = (
        sdb.query(func.count(func.distinct(B07Lineage.workflow_name)))
        .filter(B07Lineage.space_id == space_id, B07Lineage.deleted_at.is_(None))
        .scalar()
        or 0
    )

    return stats
